import os
import pandas as pd
import json
from core_logic import extract_json_content, compare_structures_for_eval
from utils import get_model_folder, flatten_json, flatten_excluding_alerted, tx_key, flatten_tx, is_transaction_field

def create_model_outputs(file_path, output_base_folder):
    """Step 1: Process a single model file and generate global/transaction outputs."""
    folder, model_name = get_model_folder(file_path, output_base_folder)
    print(f"Processing {file_path} into folder {folder}")

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"❌ Error reading {file_path}: {e}")
        return None

    gt_col = "Ground Truth"
    # Look for job_ column first, then fallback to -Instruct column
    job_cols = [c for c in df.columns if c.startswith("job_")]
    if not job_cols:
        job_cols = [c for c in df.columns if c.endswith("-Instruct")]
    if not job_cols:
        print(f"⚠️ No LLM response column found in {file_path}. Expected column starting with 'job_' or ending with '-Instruct'. Available columns: {list(df.columns)}")
        return None
    job_col = job_cols[0]

    global_rows = []
    tx_rows = []

    for idx, row in df.iterrows():
        gt_raw = str(row[gt_col])
        llm_raw = str(row[job_col])

        # Extract JSONs
        try:
            gt_json = extract_json_content(gt_raw)
        except Exception:
            gt_json = None
        try:
            llm_json = extract_json_content(llm_raw)
        except Exception:
            llm_json = None

        # --- GLOBAL FIELDS ---
        gt_flat = flatten_excluding_alerted(gt_json)
        llm_flat = flatten_excluding_alerted(llm_json)
        
        # FILTER OUT any transaction-related fields that might have leaked through
        gt_flat_filtered = {k: v for k, v in gt_flat.items() if not is_transaction_field(k)}
        llm_flat_filtered = {k: v for k, v in llm_flat.items() if not is_transaction_field(k)}
        
        combined_flat = {}
        for k in set(gt_flat_filtered.keys()).union(llm_flat_filtered.keys()):
            combined_flat[f"gt_{k}"] = gt_flat_filtered.get(k, None)
            combined_flat[f"llm_{k}"] = llm_flat_filtered.get(k, None)

        global_row = dict(row)
        global_row["extracted_gt_json"] = json.dumps(gt_json, indent=2, ensure_ascii=False) if gt_json else ""
        global_row["extracted_llm_json"] = json.dumps(llm_json, indent=2, ensure_ascii=False) if llm_json else ""
        global_row.update(combined_flat)
        global_rows.append(global_row)

        # --- TRANSACTION FIELDS ---
        gt_txs = gt_json.get("alerted_transactions", []) if isinstance(gt_json, dict) else []
        llm_txs = llm_json.get("alerted_transactions", []) if isinstance(llm_json, dict) else []

        gt_map = {tx_key(tx): tx for tx in gt_txs if tx_key(tx)}
        llm_map = {tx_key(tx): tx for tx in llm_txs if tx_key(tx)}

        # Special handling for ALL types when GT has no alerted_transactions
        if not gt_txs:
            # If LLM has alerted_transactions, add all as mismatches
            if llm_txs:
                for llm_tx in llm_txs:
                    key = tx_key(llm_tx)
                    tx_row = dict(row)
                    tx_row['transaction_references'] = key
                    tx_row['extracted_gt_json'] = ''  # No GT transaction
                    tx_row['extracted_llm_json'] = json.dumps(llm_tx, indent=2, ensure_ascii=False)
                    llm_tx_flat = flatten_tx(llm_tx)
                    for k, v in llm_tx_flat.items():
                        tx_row[f'llm_{k}'] = v
                        tx_row[f'gt_{k}'] = None
                    tx_row['mismatches'] = 'Extra in LLM output'
                    tx_rows.append(tx_row)
            else:
                # No GT and no LLM transactions, add one correct entry with empty transaction_references
                tx_row = dict(row)
                tx_row['transaction_references'] = ''
                tx_row['extracted_gt_json'] = ''
                tx_row['extracted_llm_json'] = ''
                tx_row['mismatches'] = True  # Changed from 'N/A' to True
                tx_rows.append(tx_row)
            # Skip normal processing for this row since we handled the no-GT case
            continue

        # Special handling for when LLM has no transactions but GT has transactions
        if not llm_txs and gt_txs:
            for gt_tx in gt_txs:
                key = tx_key(gt_tx)
                tx_row = dict(row)
                tx_row['transaction_references'] = key
                tx_row['extracted_gt_json'] = json.dumps(gt_tx, indent=2, ensure_ascii=False)
                tx_row['extracted_llm_json'] = ''  # No LLM transaction
                gt_tx_flat = flatten_tx(gt_tx)
                for k, v in gt_tx_flat.items():
                    tx_row[f'gt_{k}'] = v
                    tx_row[f'llm_{k}'] = None
                tx_row['mismatches'] = 'Missing in LLM output'
                tx_rows.append(tx_row)
            # Skip normal processing since we handled the no-LLM case
            continue

        # Normal processing when both GT and LLM have transactions
        all_keys = set(gt_map) | set(llm_map)
        for key in all_keys:
            gt_tx = gt_map.get(key)
            llm_tx = llm_map.get(key)
            tx_row = dict(row)
            tx_row["transaction_references"] = key
            tx_row["extracted_gt_json"] = json.dumps(gt_tx, indent=2, ensure_ascii=False) if gt_tx else ""
            tx_row["extracted_llm_json"] = json.dumps(llm_tx, indent=2, ensure_ascii=False) if llm_tx else ""
            
            gt_tx_flat = flatten_tx(gt_tx)
            llm_tx_flat = flatten_tx(llm_tx)
            
            # Side-by-side fields
            for k in set(gt_tx_flat.keys()).union(llm_tx_flat.keys()):
                tx_row[f"gt_{k}"] = gt_tx_flat.get(k, None)
                tx_row[f"llm_{k}"] = llm_tx_flat.get(k, None)
            
            # Add mismatch info using enhanced comparison
            if gt_tx and llm_tx:
                mismatches = compare_structures_for_eval(llm_tx, gt_tx)
                tx_row["mismatches"] = "\n".join(mismatches) if mismatches else True  # True if no mismatches
            elif gt_tx and not llm_tx:
                tx_row["mismatches"] = "Missing in LLM output"
            elif llm_tx and not gt_tx:
                tx_row["mismatches"] = "Extra in LLM output"
            else:
                tx_row["mismatches"] = True  # Changed from "N/A" to True
            tx_rows.append(tx_row)

    # Save main output files
    global_df = pd.DataFrame(global_rows)
    tx_df = pd.DataFrame(tx_rows)
    
    global_out = os.path.join(folder, "global_fields_evaluation.csv")
    tx_out = os.path.join(folder, "transaction_fields_evaluation.csv")
    
    global_df.to_csv(global_out, index=False, encoding="utf-8-sig")
    tx_df.to_csv(tx_out, index=False, encoding="utf-8-sig")
    
    print(f"✅ Saved outputs for {model_name}")
    
    return {
        'model_name': model_name,
        'folder': folder,
        'global_df': global_df,
        'tx_df': tx_df
    }

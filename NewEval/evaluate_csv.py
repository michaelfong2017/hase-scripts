import pandas as pd
import json
from collections import defaultdict
from core_logic import extract_json_content, compare_structures_for_eval

INPUT_PATH = "../Cycle3 Results Raw/cycle2_final8B_full60_test_set_v5_test_set_model_responses.csv"
OUTPUT_GLOBAL = "global_fields_evaluation.csv"
OUTPUT_TX = "transaction_fields_evaluation.csv"

def flatten_json(y, parent_key='', sep='.'):
    """Flatten a nested JSON dict."""
    items = []
    if isinstance(y, dict):
        for k, v in y.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(flatten_json(v, new_key, sep=sep).items())
    elif isinstance(y, list):
        for i, v in enumerate(y):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.extend(flatten_json(v, new_key, sep=sep).items())
    else:
        items.append((parent_key, y))
    return dict(items)

def flatten_excluding_alerted(json_obj):
    """Flatten JSON excluding alerted_transactions."""
    if not isinstance(json_obj, dict):
        return {}
    return {k: v for k, v in flatten_json(json_obj).items() if not k.startswith('alerted_transactions')}

def tx_key(tx):
    """Generate key from transaction_references."""
    refs = tx.get("transaction_references", [])
    if not isinstance(refs, list):
        refs = [str(refs)]
    return ",".join(sorted(map(str, refs)))

def flatten_tx(tx):
    """Flatten transaction dict."""
    return flatten_json(tx) if isinstance(tx, dict) else {}

def aggregate_by_type(df):
    """Aggregate results by Type - requires ALL fields to be correct for accuracy."""
    from core_logic import are_exact_match_for_eval
    
    if 'Type' not in df.columns:
        return pd.DataFrame()
    
    agg = defaultdict(lambda: {"total": 0, "all_fields_correct": 0})
    
    # Find all gt_ columns and their corresponding llm_ columns
    gt_cols = [col for col in df.columns if col.startswith('gt_')]
    
    # Group by Type and check if ALL fields are correct for each row
    for _, row in df.iterrows():
        type_val = row.get("Type", "Unknown")
        agg[type_val]["total"] += 1
        
        # Check if this row is correct - either by mismatches column or field comparison
        is_correct = False
        
        # First check the mismatches column if it exists
        if 'mismatches' in df.columns:
            mismatch_val = row.get('mismatches')
            # If mismatches is True (boolean), it's correct
            if mismatch_val is True:
                is_correct = True
            # If mismatches is empty string or evaluates to False, it's correct
            elif not mismatch_val or str(mismatch_val).strip() == '':
                is_correct = True
            # Otherwise it contains error messages, so it's incorrect
            else:
                is_correct = False
        else:
            # Fallback: Check if ALL fields are correct for this row
            all_correct = True
            null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
            
            for gt_col in gt_cols:
                field_name = gt_col[3:]  # Remove 'gt_' prefix
                llm_col = f"llm_{field_name}"
                
                if llm_col in df.columns:
                    gt_val = row.get(gt_col)
                    llm_val = row.get(llm_col)
                    
                    # Skip null comparisons
                    try:
                        gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                    except TypeError:
                        gt_is_null = pd.isna(gt_val)
                    try:
                        llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                    except TypeError:
                        llm_is_null = pd.isna(llm_val)
                    
                    if gt_is_null and llm_is_null:
                        continue  # Both null, consider correct
                    
                    # Use enhanced comparison - if ANY field is wrong, mark as incorrect
                    if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                        all_correct = False
                        break  # No need to check further fields
            
            is_correct = all_correct
        
        if is_correct:
            agg[type_val]["all_fields_correct"] += 1
    
    rows = []
    for k, v in agg.items():
        row = {
            "Type": k, 
            "total": v["total"], 
            "all_fields_correct": v["all_fields_correct"],
            "mismatch_count": v["total"] - v["all_fields_correct"]
        }
        row["accuracy_rate"] = f"{(v['all_fields_correct'] / v['total'] * 100):.2f}%" if v["total"] > 0 else "0.00%"
        rows.append(row)
    
    return pd.DataFrame(rows)

def aggregate_by_field(df):
    """Aggregate results by individual fields using enhanced comparison logic."""
    from core_logic import are_exact_match_for_eval
    
    agg = defaultdict(lambda: {"total": 0, "mismatch_count": 0})
    
    # Find all gt_ columns and their corresponding llm_ columns
    gt_cols = [col for col in df.columns if col.startswith('gt_')]
    
    for gt_col in gt_cols:
        field_name = gt_col[3:]  # Remove 'gt_' prefix
        llm_col = f"llm_{field_name}"
        
        if llm_col in df.columns:
            for _, row in df.iterrows():
                # FIRST: Check if this row is already marked as correct via mismatches column
                if 'mismatches' in df.columns:
                    mismatch_val = row.get('mismatches')
                    if mismatch_val is True:
                        # This entire row is correct, so this field is correct
                        agg[field_name]["total"] += 1
                        # Don't increment mismatch_count (it's correct)
                        continue
                    elif isinstance(mismatch_val, str) and mismatch_val.strip():
                        # This row has errors, but we still need to check if THIS specific field contributes
                        pass  # Continue to field-level checking below
                
                gt_val = row.get(gt_col)
                llm_val = row.get(llm_col)
                
                # Skip if both are null/empty using the same null logic as main comparison
                null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
                
                try:
                    gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                except TypeError:
                    gt_is_null = pd.isna(gt_val)
                try:
                    llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                except TypeError:
                    llm_is_null = pd.isna(llm_val)
                
                if gt_is_null and llm_is_null:
                    continue  # Skip null vs null comparisons
                
                agg[field_name]["total"] += 1
                
                # Use the same enhanced comparison logic as the main evaluation
                if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                    agg[field_name]["mismatch_count"] += 1
    
    rows = []
    for k, v in agg.items():
        row = {"Field": k, "total": v["total"], "mismatch_count": v["mismatch_count"]}
        row["accuracy_rate"] = f"{((v['total'] - v['mismatch_count']) / v['total'] * 100):.2f}%" if v["total"] > 0 else "0.00%"
        rows.append(row)
    return pd.DataFrame(rows)

def aggregate_by_type_and_field(df):
    """Aggregate results by both Type and Field together (composite)."""
    from core_logic import are_exact_match_for_eval
    
    agg = defaultdict(lambda: {"total": 0, "mismatch_count": 0})
    
    # Find all gt_ columns and their corresponding llm_ columns
    gt_cols = [col for col in df.columns if col.startswith('gt_')]
    
    for gt_col in gt_cols:
        field_name = gt_col[3:]  # Remove 'gt_' prefix
        llm_col = f"llm_{field_name}"
        
        if llm_col in df.columns:
            for _, row in df.iterrows():
                type_val = row.get("Type", "Unknown")
                
                # FIRST: Check if this row is already marked as correct via mismatches column
                if 'mismatches' in df.columns:
                    mismatch_val = row.get('mismatches')
                    if mismatch_val is True:
                        # This entire row is correct, so this field is correct
                        composite_key = f"{type_val}|{field_name}"
                        agg[composite_key]["total"] += 1
                        # Don't increment mismatch_count (it's correct)
                        continue
                    elif isinstance(mismatch_val, str) and mismatch_val.strip():
                        # This row has errors, but we still need to check if THIS specific field contributes
                        pass  # Continue to field-level checking below
                
                gt_val = row.get(gt_col)
                llm_val = row.get(llm_col)
                
                # Create composite key: Type + Field
                composite_key = f"{type_val}|{field_name}"
                
                # Skip if both are null/empty using the same null logic as main comparison
                null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
                
                try:
                    gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                except TypeError:
                    gt_is_null = pd.isna(gt_val)
                try:
                    llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                except TypeError:
                    llm_is_null = pd.isna(llm_val)
                
                if gt_is_null and llm_is_null:
                    continue  # Skip null vs null comparisons
                
                agg[composite_key]["total"] += 1
                
                # Use the same enhanced comparison logic as the main evaluation
                if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                    agg[composite_key]["mismatch_count"] += 1
    
    rows = []
    for k, v in agg.items():
        type_name, field_name = k.split("|", 1)
        row = {
            "Type": type_name, 
            "Field": field_name, 
            "total": v["total"], 
            "mismatch_count": v["mismatch_count"]
        }
        row["accuracy_rate"] = f"{((v['total'] - v['mismatch_count']) / v['total'] * 100):.2f}%" if v["total"] > 0 else "0.00%"
        rows.append(row)
    
    # Sort by Type then Field for better readability
    return pd.DataFrame(rows).sort_values(['Type', 'Field'])

def main():
    df = pd.read_csv(INPUT_PATH)
    gt_col = "Ground Truth"
    job_col = next(c for c in df.columns if c.startswith("job_"))

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
        combined_flat = {}
        for k in set(gt_flat.keys()).union(llm_flat.keys()):
            combined_flat[f"gt_{k}"] = gt_flat.get(k, None)
            combined_flat[f"llm_{k}"] = llm_flat.get(k, None)

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
    
    global_df.to_csv(OUTPUT_GLOBAL, index=False, encoding="utf-8-sig")
    tx_df.to_csv(OUTPUT_TX, index=False, encoding="utf-8-sig")
    
    # Generate aggregation files
    agg_type_global = aggregate_by_type(global_df)
    agg_field_global = aggregate_by_field(global_df)
    agg_composite_global = aggregate_by_type_and_field(global_df)  # NEW
    
    agg_type_tx = aggregate_by_type(tx_df)
    agg_field_tx = aggregate_by_field(tx_df)
    agg_composite_tx = aggregate_by_type_and_field(tx_df)  # NEW
    
    # Save all aggregation files
    agg_type_global.to_csv("agg_by_type_global.csv", index=False, encoding="utf-8-sig")
    agg_field_global.to_csv("agg_by_field_global.csv", index=False, encoding="utf-8-sig")
    agg_composite_global.to_csv("agg_by_type_and_field_global.csv", index=False, encoding="utf-8-sig")  # NEW
    
    agg_type_tx.to_csv("agg_by_type_transaction.csv", index=False, encoding="utf-8-sig")
    agg_field_tx.to_csv("agg_by_field_transaction.csv", index=False, encoding="utf-8-sig")
    agg_composite_tx.to_csv("agg_by_type_and_field_transaction.csv", index=False, encoding="utf-8-sig")  # NEW
    
    print(f"✅ Saved main files: {OUTPUT_GLOBAL}, {OUTPUT_TX}")
    print(f"✅ Saved aggregation files:")
    print(f"   - agg_by_type_global.csv, agg_by_field_global.csv, agg_by_type_and_field_global.csv")
    print(f"   - agg_by_type_transaction.csv, agg_by_field_transaction.csv, agg_by_type_and_field_transaction.csv")

if __name__ == "__main__":
    main()

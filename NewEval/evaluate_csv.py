import pandas as pd
import json
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
    # Defensive: ensure refs is always a list of strings
    if not isinstance(refs, list):
        refs = [str(refs)]
    return ",".join(sorted(map(str, refs)))

def flatten_tx(tx):
    """Flatten transaction dict."""
    return flatten_json(tx) if isinstance(tx, dict) else {}

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
            
            # Optional: add mismatch info
            if gt_tx and llm_tx:
                mismatches = compare_structures_for_eval(llm_tx, gt_tx)
                tx_row["mismatches"] = "\n".join(mismatches)
            elif gt_tx and not llm_tx:
                tx_row["mismatches"] = "Missing in LLM output"
            elif llm_tx and not gt_tx:
                tx_row["mismatches"] = "Extra in LLM output"
            else:
                tx_row["mismatches"] = "N/A"
            tx_rows.append(tx_row)

    # Save output files
    pd.DataFrame(global_rows).to_csv(OUTPUT_GLOBAL, index=False, encoding="utf-8-sig")
    pd.DataFrame(tx_rows).to_csv(OUTPUT_TX, index=False, encoding="utf-8-sig")
    print(f"✅ Saved {OUTPUT_GLOBAL} and {OUTPUT_TX}")

if __name__ == "__main__":
    main()

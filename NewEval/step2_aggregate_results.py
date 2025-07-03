import os
import pandas as pd
from collections import defaultdict
from core_logic import are_exact_match_for_eval
from utils import is_transaction_field

def aggregate_by_field(df, is_global_analysis=True):
    """Aggregate results by individual fields - count nulls as valid answers."""
    agg = defaultdict(lambda: {"total": 0, "mismatch_count": 0})
    
    # Define null representations
    null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
    
    # Find all gt_ columns and their corresponding llm_ columns
    gt_cols = []
    for col in df.columns:
        if col.startswith('gt_'):
            field_name = col[3:]  # Remove 'gt_' prefix
            # Only filter transaction fields for global analysis
            if is_global_analysis and is_transaction_field(field_name):
                continue
            gt_cols.append(col)
    
    for gt_col in gt_cols:
        field_name = gt_col[3:]  # Remove 'gt_' prefix
        llm_col = f"llm_{field_name}"
        
        if llm_col in df.columns:
            for _, row in df.iterrows():
                gt_val = row.get(gt_col)
                llm_val = row.get(llm_col)
                
                # **ALWAYS COUNT AS TOTAL** - including nulls as valid question-answer pairs
                agg[field_name]["total"] += 1
                
                # Check if values match (including null-null matches)
                try:
                    gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                except TypeError:
                    gt_is_null = pd.isna(gt_val)
                try:
                    llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                except TypeError:
                    llm_is_null = pd.isna(llm_val)
                
                # Both null = match (correct answer)
                if gt_is_null and llm_is_null:
                    continue  # No mismatch
                
                # One null, one not = mismatch
                if gt_is_null != llm_is_null:
                    agg[field_name]["mismatch_count"] += 1
                    continue
                
                # Both have values - use enhanced comparison
                if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                    agg[field_name]["mismatch_count"] += 1
    
    rows = []
    for k, v in agg.items():
        row = {"Field": k, "total": v["total"], "mismatch_count": v["mismatch_count"]}
        row["accuracy_rate"] = f"{((v['total'] - v['mismatch_count']) / v['total'] * 100):.2f}%" if v["total"] > 0 else "0.00%"
        rows.append(row)
    return pd.DataFrame(rows)

def aggregate_by_type_and_field(df, is_global_analysis=True):
    """Aggregate results by both Type and Field - count nulls as valid answers."""
    agg = defaultdict(lambda: {"total": 0, "mismatch_count": 0})
    
    # Define null representations
    null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
    
    # Find all gt_ columns and their corresponding llm_ columns
    gt_cols = []
    for col in df.columns:
        if col.startswith('gt_'):
            field_name = col[3:]  # Remove 'gt_' prefix
            # Only filter transaction fields for global analysis
            if is_global_analysis and is_transaction_field(field_name):
                continue
            gt_cols.append(col)
    
    for gt_col in gt_cols:
        field_name = gt_col[3:]  # Remove 'gt_' prefix
        llm_col = f"llm_{field_name}"
        
        if llm_col in df.columns:
            for _, row in df.iterrows():
                type_val = row.get("Type", "Unknown")
                composite_key = f"{type_val}|{field_name}"
                
                gt_val = row.get(gt_col)
                llm_val = row.get(llm_col)
                
                # **ALWAYS COUNT AS TOTAL** - including nulls as valid question-answer pairs
                agg[composite_key]["total"] += 1
                
                # Check if values match (including null-null matches)
                try:
                    gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                except TypeError:
                    gt_is_null = pd.isna(gt_val)
                try:
                    llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                except TypeError:
                    llm_is_null = pd.isna(llm_val)
                
                # Both null = match (correct answer)
                if gt_is_null and llm_is_null:
                    continue  # No mismatch
                
                # One null, one not = mismatch
                if gt_is_null != llm_is_null:
                    agg[composite_key]["mismatch_count"] += 1
                    continue
                
                # Both have values - use enhanced comparison
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
    
    # SAFE SORTING: Check if we have rows and if 'Type' column exists
    if rows:
        df_result = pd.DataFrame(rows)
        # Only sort by Type if it exists in the DataFrame
        if 'Type' in df_result.columns and 'Field' in df_result.columns:
            return df_result.sort_values(['Type', 'Field'])
        elif 'Field' in df_result.columns:
            return df_result.sort_values(['Field'])
        else:
            return df_result
    else:
        # Return empty DataFrame with correct columns
        return pd.DataFrame(columns=['Type', 'Field', 'total', 'mismatch_count', 'accuracy_rate'])

def aggregate_by_type(df):
    """Aggregate results by Type - requires ALL fields to be correct for accuracy."""
    if 'Type' not in df.columns:
        return pd.DataFrame()
    
    agg = defaultdict(lambda: {"total": 0, "all_fields_correct": 0})
    
    # Find all gt_ columns and their corresponding llm_ columns
    # For GLOBAL aggregation, exclude transaction fields more aggressively
    gt_cols = [col for col in df.columns if col.startswith('gt_') and not is_transaction_field(col[3:])]
    
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
                    
                    # Check for null matches
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

def aggregate_model_results(result, output_base_folder):
    """Step 2: Generate aggregation files for a single model."""
    folder = result['folder']
    model_name = result['model_name']
    global_df = result['global_df']
    tx_df = result['tx_df']
    
    print(f"Aggregating results for {model_name}...")
    
    # Generate aggregation files
    agg_type_global = aggregate_by_type(global_df)
    agg_field_global = aggregate_by_field(global_df, is_global_analysis=True)  # Filter transaction fields
    agg_composite_global = aggregate_by_type_and_field(global_df, is_global_analysis=True)  # Filter transaction fields

    agg_type_tx = aggregate_by_type(tx_df)
    agg_field_tx = aggregate_by_field(tx_df, is_global_analysis=False)  # DON'T filter transaction fields
    agg_composite_tx = aggregate_by_type_and_field(tx_df, is_global_analysis=False)  # DON'T filter transaction fields
    
    # Save aggregation files
    agg_type_global.to_csv(os.path.join(folder, "agg_by_type_global.csv"), index=False, encoding="utf-8-sig")
    agg_field_global.to_csv(os.path.join(folder, "agg_by_field_global.csv"), index=False, encoding="utf-8-sig")
    agg_composite_global.to_csv(os.path.join(folder, "agg_by_type_and_field_global.csv"), index=False, encoding="utf-8-sig")
    
    agg_type_tx.to_csv(os.path.join(folder, "agg_by_type_transaction.csv"), index=False, encoding="utf-8-sig")
    agg_field_tx.to_csv(os.path.join(folder, "agg_by_field_transaction.csv"), index=False, encoding="utf-8-sig")
    agg_composite_tx.to_csv(os.path.join(folder, "agg_by_type_and_field_transaction.csv"), index=False, encoding="utf-8-sig")
    
    # Update result with aggregation data
    result.update({
        'agg_type_global': agg_type_global,
        'agg_field_global': agg_field_global,
        'agg_composite_global': agg_composite_global,
        'agg_type_tx': agg_type_tx,
        'agg_field_tx': agg_field_tx,
        'agg_composite_tx': agg_composite_tx
    })
    
    print(f"✅ Aggregated results for {model_name}")

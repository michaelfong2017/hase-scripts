import os
import pandas as pd
from collections import defaultdict
from core_logic import are_exact_match_for_eval
from utils import is_transaction_field


def aggregate_custom_results(all_results, output_base_folder):
    """Step 4: Complete custom aggregation - detailed files, half analysis, and type analysis."""
    
    # Create output folder for custom aggregation
    custom_folder = os.path.join(output_base_folder, "step4_custom_aggregation")
    os.makedirs(custom_folder, exist_ok=True)
    
    print("🔄 Step 4a: Generating detailed pass files per model...")
    generate_detailed_pass_files_per_model(all_results, custom_folder)
    
    print("🔄 Step 4b: Creating first half / second half analysis...")
    create_half_analysis(all_results, custom_folder)
    
    print("🔄 Step 4c: Creating by-type analysis...")
    create_type_analysis(all_results, custom_folder)
    
    print(f"✅ All custom aggregation completed in {custom_folder}")


def generate_detailed_pass_files_per_model(all_results, custom_folder):
    """Generate detailed CSV files for each model with each row as [Case Number, Intelligence Number] and boolean pass columns."""
    
    for result in all_results:
        model_name = result['model_name']
        global_df = result['global_df']
        tx_df = result['tx_df']

        # Identify case number and intelligence number columns
        case_identifier_cols = [col for col in global_df.columns if not col.startswith(('gt_', 'llm_', 'extracted_', 'mismatches'))]

        # Define helper functions for pass checks
        def check_global_field_pass(global_row):
            if 'mismatches' in global_df.columns:
                global_mismatch_val = global_row.get('mismatches')
                return global_mismatch_val is True or not str(global_mismatch_val).strip()
            else:
                gt_cols = [col for col in global_df.columns if col.startswith('gt_') and not is_transaction_field(col[3:])]
                null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
                for gt_col in gt_cols:
                    field_name = gt_col[3:]
                    llm_col = f"llm_{field_name}"
                    if llm_col in global_df.columns:
                        gt_val = global_row.get(gt_col)
                        llm_val = global_row.get(llm_col)
                        try:
                            gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                            llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                        except TypeError:
                            gt_is_null = pd.isna(gt_val)
                            llm_is_null = pd.isna(llm_val)
                        if gt_is_null and llm_is_null:
                            continue
                        if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                            return False
                return True

        def check_alerted_transactions_pass(global_row):
            intelligence_tx_rows = tx_df
            for col in case_identifier_cols:
                if col in tx_df.columns:
                    intelligence_tx_rows = intelligence_tx_rows[intelligence_tx_rows[col] == global_row[col]]
            if len(intelligence_tx_rows) == 0:
                return True
            for _, tx_row in intelligence_tx_rows.iterrows():
                if 'mismatches' in tx_df.columns:
                    tx_mismatch_val = tx_row.get('mismatches')
                    if not (tx_mismatch_val is True or not str(tx_mismatch_val).strip()):
                        return False
                else:
                    gt_cols = [col for col in tx_df.columns if col.startswith('gt_')]
                    null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
                    for gt_col in gt_cols:
                        field_name = gt_col[3:]
                        llm_col = f"llm_{field_name}"
                        if llm_col in tx_df.columns:
                            gt_val = tx_row.get(gt_col)
                            llm_val = tx_row.get(llm_col)
                            try:
                                gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                                llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                            except TypeError:
                                gt_is_null = pd.isna(gt_val)
                                llm_is_null = pd.isna(llm_val)
                            if gt_is_null and llm_is_null:
                                continue
                            if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                                return False
            return True

        def check_overall_pass(global_row):
            return check_global_field_pass(global_row) and check_alerted_transactions_pass(global_row)

        detailed_rows = []

        # For each row in global_df, create a detailed row with pass booleans
        for _, global_row in global_df.iterrows():
            row_data = {col: global_row[col] for col in case_identifier_cols}
            row_data['Overall_Pass'] = check_overall_pass(global_row)
            row_data['Global_Field_Pass'] = check_global_field_pass(global_row)
            row_data['Alerted_Transactions_Pass'] = check_alerted_transactions_pass(global_row)
            detailed_rows.append(row_data)

        detailed_df = pd.DataFrame(detailed_rows)

        # Save detailed CSV per model
        detailed_file = os.path.join(custom_folder, f"detailed_pass_by_case_intelligence_{model_name}.csv")
        detailed_df.to_csv(detailed_file, index=False, encoding="utf-8-sig")

        print(f"✅ Detailed pass file saved for model {model_name}")


def create_half_analysis(all_results, custom_folder):
    """Create first half / second half analysis."""
    
    summary = {}
    
    for result in all_results:
        model_name = result['model_name']
        global_df = result['global_df']
        tx_df = result['tx_df']
        
        # Split data into first half and second half
        total_rows = len(global_df)
        half_point = total_rows // 2
        
        first_half_global = global_df.iloc[:half_point]
        second_half_global = global_df.iloc[half_point:]
        
        # Identify case identifier columns
        case_identifier_cols = [col for col in global_df.columns 
                              if not col.startswith(('gt_', 'llm_', 'extracted_', 'mismatches'))]
        
        # Helper functions (same as before)
        def check_global_field_pass(global_row):
            if 'mismatches' in global_df.columns:
                global_mismatch_val = global_row.get('mismatches')
                return global_mismatch_val is True or not str(global_mismatch_val).strip()
            else:
                gt_cols = [col for col in global_df.columns if col.startswith('gt_') and not is_transaction_field(col[3:])]
                null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
                for gt_col in gt_cols:
                    field_name = gt_col[3:]
                    llm_col = f"llm_{field_name}"
                    if llm_col in global_df.columns:
                        gt_val = global_row.get(gt_col)
                        llm_val = global_row.get(llm_col)
                        try:
                            gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                            llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                        except TypeError:
                            gt_is_null = pd.isna(gt_val)
                            llm_is_null = pd.isna(llm_val)
                        if gt_is_null and llm_is_null:
                            continue
                        if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                            return False
                return True

        def check_alerted_transactions_pass(global_row):
            intelligence_tx_rows = tx_df
            for col in case_identifier_cols:
                if col in tx_df.columns:
                    intelligence_tx_rows = intelligence_tx_rows[intelligence_tx_rows[col] == global_row[col]]
            if len(intelligence_tx_rows) == 0:
                return True
            for _, tx_row in intelligence_tx_rows.iterrows():
                if 'mismatches' in tx_df.columns:
                    tx_mismatch_val = tx_row.get('mismatches')
                    if not (tx_mismatch_val is True or not str(tx_mismatch_val).strip()):
                        return False
                else:
                    gt_cols = [col for col in tx_df.columns if col.startswith('gt_')]
                    null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
                    for gt_col in gt_cols:
                        field_name = gt_col[3:]
                        llm_col = f"llm_{field_name}"
                        if llm_col in tx_df.columns:
                            gt_val = tx_row.get(gt_col)
                            llm_val = tx_row.get(llm_col)
                            try:
                                gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                                llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                            except TypeError:
                                gt_is_null = pd.isna(gt_val)
                                llm_is_null = pd.isna(llm_val)
                            if gt_is_null and llm_is_null:
                                continue
                            if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                                return False
            return True

        def check_overall_pass(global_row):
            return check_global_field_pass(global_row) and check_alerted_transactions_pass(global_row)
        
        # Aggregate counts for each half
        def aggregate_half(global_half):
            total = len(global_half)
            overall_pass_count = 0
            global_field_pass_count = 0
            alerted_tx_pass_count = 0
            
            for idx, global_row in global_half.iterrows():
                if check_overall_pass(global_row):
                    overall_pass_count += 1
                if check_global_field_pass(global_row):
                    global_field_pass_count += 1
                if check_alerted_transactions_pass(global_row):
                    alerted_tx_pass_count += 1
            
            return {
                'total': total,
                'overall_pass': overall_pass_count,
                'global_field_pass': global_field_pass_count,
                'alerted_tx_pass': alerted_tx_pass_count
            }
        
        # Calculate results for both halves
        first_half_results = aggregate_half(first_half_global)
        second_half_results = aggregate_half(second_half_global)
        
        # Store results
        summary[model_name] = {
            'first_half': first_half_results,
            'second_half': second_half_results
        }
    
    # Generate formatted output
    output_lines = []
    for model_name, results in summary.items():
        first = results['first_half']
        second = results['second_half']
        
        output_lines.append(f"Model: {model_name}")
        
        # Overall Pass
        output_lines.append("- Overall Pass (pass all global fields and all transactions)")
        output_lines.append(f"  First half ({first['total']}): {first['overall_pass']} out of {first['total']} ({first['overall_pass']/first['total']*100:.2f}%)")
        output_lines.append(f"  Second half ({second['total']}): {second['overall_pass']} out of {second['total']} ({second['overall_pass']/second['total']*100:.2f}%)")
        
        # Global Field Pass
        output_lines.append("- Global Field Pass (pass all global fields)")
        output_lines.append(f"  First half ({first['total']}): {first['global_field_pass']} out of {first['total']} ({first['global_field_pass']/first['total']*100:.2f}%)")
        output_lines.append(f"  Second half ({second['total']}): {second['global_field_pass']} out of {second['total']} ({second['global_field_pass']/second['total']*100:.2f}%)")
        
        # Alerted Transactions Pass
        output_lines.append("- Alerted Transactions Pass (must pass all transactions together)")
        output_lines.append(f"  First half ({first['total']}): {first['alerted_tx_pass']} out of {first['total']} ({first['alerted_tx_pass']/first['total']*100:.2f}%)")
        output_lines.append(f"  Second half ({second['total']}): {second['alerted_tx_pass']} out of {second['total']*100:.2f}%)")
        
        output_lines.append("")  # Empty line between models
    
    # Save to file
    output_file = os.path.join(custom_folder, "half_analysis_summary.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    # Also save as CSV for further analysis
    csv_rows = []
    for model_name, results in summary.items():
        first = results['first_half']
        second = results['second_half']
        
        csv_rows.append({
            'Model': model_name,
            'Metric': 'Overall Pass',
            'First_Half_Pass': first['overall_pass'],
            'First_Half_Total': first['total'],
            'First_Half_Percentage': f"{first['overall_pass']/first['total']*100:.2f}%",
            'Second_Half_Pass': second['overall_pass'],
            'Second_Half_Total': second['total'],
            'Second_Half_Percentage': f"{second['overall_pass']/second['total']*100:.2f}%"
        })
        
        csv_rows.append({
            'Model': model_name,
            'Metric': 'Global Field Pass',
            'First_Half_Pass': first['global_field_pass'],
            'First_Half_Total': first['total'],
            'First_Half_Percentage': f"{first['global_field_pass']/first['total']*100:.2f}%",
            'Second_Half_Pass': second['global_field_pass'],
            'Second_Half_Total': second['total'],
            'Second_Half_Percentage': f"{second['global_field_pass']/second['total']*100:.2f}%"
        })
        
        csv_rows.append({
            'Model': model_name,
            'Metric': 'Alerted Transactions Pass',
            'First_Half_Pass': first['alerted_tx_pass'],
            'First_Half_Total': first['total'],
            'First_Half_Percentage': f"{first['alerted_tx_pass']/first['total']*100:.2f}%",
            'Second_Half_Pass': second['alerted_tx_pass'],
            'Second_Half_Total': second['total'],
            'Second_Half_Percentage': f"{second['alerted_tx_pass']/second['total']*100:.2f}%"
        })
    
    csv_df = pd.DataFrame(csv_rows)
    csv_file = os.path.join(custom_folder, "half_analysis_summary.csv")
    csv_df.to_csv(csv_file, index=False, encoding="utf-8-sig")
    
    print(f"✅ Half analysis saved")


def create_type_analysis(all_results, custom_folder):
    """Create by-type analysis across all models."""
    
    # Aggregate by type across all models
    type_summary = defaultdict(lambda: {
        'total': 0, 
        'overall_pass': 0, 
        'global_field_pass': 0, 
        'alerted_tx_pass': 0,
        'models': set()
    })
    
    # Also create per-model type analysis
    model_type_data = []
    
    for result in all_results:
        model_name = result['model_name']
        global_df = result['global_df']
        tx_df = result['tx_df']
        
        # Check if Type column exists
        if 'Type' not in global_df.columns:
            print(f"Warning: No 'Type' column found in {model_name}")
            continue
        
        # Identify case identifier columns
        case_identifier_cols = [col for col in global_df.columns 
                              if not col.startswith(('gt_', 'llm_', 'extracted_', 'mismatches'))]
        
        # Helper functions (same as before)
        def check_global_field_pass(global_row):
            if 'mismatches' in global_df.columns:
                global_mismatch_val = global_row.get('mismatches')
                return global_mismatch_val is True or not str(global_mismatch_val).strip()
            else:
                gt_cols = [col for col in global_df.columns if col.startswith('gt_') and not is_transaction_field(col[3:])]
                null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
                for gt_col in gt_cols:
                    field_name = gt_col[3:]
                    llm_col = f"llm_{field_name}"
                    if llm_col in global_df.columns:
                        gt_val = global_row.get(gt_col)
                        llm_val = global_row.get(llm_col)
                        try:
                            gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                            llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                        except TypeError:
                            gt_is_null = pd.isna(gt_val)
                            llm_is_null = pd.isna(llm_val)
                        if gt_is_null and llm_is_null:
                            continue
                        if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                            return False
                return True

        def check_alerted_transactions_pass(global_row):
            intelligence_tx_rows = tx_df
            for col in case_identifier_cols:
                if col in tx_df.columns:
                    intelligence_tx_rows = intelligence_tx_rows[intelligence_tx_rows[col] == global_row[col]]
            if len(intelligence_tx_rows) == 0:
                return True
            for _, tx_row in intelligence_tx_rows.iterrows():
                if 'mismatches' in tx_df.columns:
                    tx_mismatch_val = tx_row.get('mismatches')
                    if not (tx_mismatch_val is True or not str(tx_mismatch_val).strip()):
                        return False
                else:
                    gt_cols = [col for col in tx_df.columns if col.startswith('gt_')]
                    null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
                    for gt_col in gt_cols:
                        field_name = gt_col[3:]
                        llm_col = f"llm_{field_name}"
                        if llm_col in tx_df.columns:
                            gt_val = tx_row.get(gt_col)
                            llm_val = tx_row.get(llm_col)
                            try:
                                gt_is_null = pd.isna(gt_val) or gt_val in null_representations
                                llm_is_null = pd.isna(llm_val) or llm_val in null_representations
                            except TypeError:
                                gt_is_null = pd.isna(gt_val)
                                llm_is_null = pd.isna(llm_val)
                            if gt_is_null and llm_is_null:
                                continue
                            if not are_exact_match_for_eval(llm_val, gt_val, field_name):
                                return False
            return True

        def check_overall_pass(global_row):
            return check_global_field_pass(global_row) and check_alerted_transactions_pass(global_row)
        
        # Process each row by type
        model_type_counts = defaultdict(lambda: {
            'total': 0, 
            'overall_pass': 0, 
            'global_field_pass': 0, 
            'alerted_tx_pass': 0
        })
        
        for _, global_row in global_df.iterrows():
            type_val = global_row.get('Type', 'Unknown')
            
            # Update counts
            type_summary[type_val]['total'] += 1
            type_summary[type_val]['models'].add(model_name)
            model_type_counts[type_val]['total'] += 1
            
            # Check passes
            overall_pass = check_overall_pass(global_row)
            global_pass = check_global_field_pass(global_row)
            tx_pass = check_alerted_transactions_pass(global_row)
            
            if overall_pass:
                type_summary[type_val]['overall_pass'] += 1
                model_type_counts[type_val]['overall_pass'] += 1
            if global_pass:
                type_summary[type_val]['global_field_pass'] += 1
                model_type_counts[type_val]['global_field_pass'] += 1
            if tx_pass:
                type_summary[type_val]['alerted_tx_pass'] += 1
                model_type_counts[type_val]['alerted_tx_pass'] += 1
        
        # Add to model-specific data
        for type_val, counts in model_type_counts.items():
            model_type_data.append({
                'Model': model_name,
                'Type': type_val,
                'Total': counts['total'],
                'Overall_Pass': counts['overall_pass'],
                'Overall_Pass_Rate': f"{counts['overall_pass']/counts['total']*100:.2f}%" if counts['total'] > 0 else "0.00%",
                'Global_Field_Pass': counts['global_field_pass'],
                'Global_Field_Pass_Rate': f"{counts['global_field_pass']/counts['total']*100:.2f}%" if counts['total'] > 0 else "0.00%",
                'Alerted_Transactions_Pass': counts['alerted_tx_pass'],
                'Alerted_Transactions_Pass_Rate': f"{counts['alerted_tx_pass']/counts['total']*100:.2f}%" if counts['total'] > 0 else "0.00%"
            })
    
    # Create overall type summary
    overall_type_rows = []
    for type_val, data in type_summary.items():
        overall_type_rows.append({
            'Type': type_val,
            'Total_Cases': data['total'],
            'Overall_Pass': data['overall_pass'],
            'Overall_Pass_Rate': f"{data['overall_pass']/data['total']*100:.2f}%" if data['total'] > 0 else "0.00%",
            'Global_Field_Pass': data['global_field_pass'],
            'Global_Field_Pass_Rate': f"{data['global_field_pass']/data['total']*100:.2f}%" if data['total'] > 0 else "0.00%",
            'Alerted_Transactions_Pass': data['alerted_tx_pass'],
            'Alerted_Transactions_Pass_Rate': f"{data['alerted_tx_pass']/data['total']*100:.2f}%" if data['total'] > 0 else "0.00%",
            'Models_Included': ', '.join(sorted(data['models']))
        })
    
    # Save overall type analysis
    overall_type_df = pd.DataFrame(overall_type_rows)
    overall_type_file = os.path.join(custom_folder, "type_analysis_overall.csv")
    overall_type_df.to_csv(overall_type_file, index=False, encoding="utf-8-sig")
    
    # Save per-model type analysis
    model_type_df = pd.DataFrame(model_type_data)
    model_type_file = os.path.join(custom_folder, "type_analysis_by_model.csv")
    model_type_df.to_csv(model_type_file, index=False, encoding="utf-8-sig")
    
    print(f"✅ Type analysis saved")
    print(f"   - Overall: {overall_type_file}")
    print(f"   - By Model: {model_type_file}")

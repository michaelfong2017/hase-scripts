import pandas as pd
import json
import random
from data_processor import (
    random_generation_functions, strict_normalization_functions,
    replace_in_dataframe, NORMALIZED_NAMES, save_json_utf8, load_json_utf8,
    randomize_masked_value
)
from io import StringIO

def create_randomized_rows(df, num_new_rows=10):
    """Create randomized rows by replacing values while maintaining referential integrity"""
    new_rows = []
    
    for i in range(num_new_rows):
        template_idx = random.randint(0, len(df) - 1)
        template_row = df.iloc[template_idx].copy()
        
        value_mappings = generate_value_mappings()
        new_row = apply_mappings_to_row(template_row, value_mappings)
        new_rows.append(new_row)
    
    new_df = pd.concat([df] + [pd.DataFrame([row]) for row in new_rows], ignore_index=True)
    return new_df

def generate_value_mappings():
    """Generate random mappings for all field types"""
    mappings = {}
    
    for field_type, generator in random_generation_functions.items():
        random_values = [generator() for _ in range(5)]
        mappings[field_type] = random_values
    
    return mappings

def apply_mappings_to_row(row, value_mappings):
    """Apply value mappings to a single row across all columns"""
    new_row = row.copy()
    
    row_mappings = {}
    current_values = extract_values_from_row(row)
    
    for field_type, current_vals in current_values.items():
        if field_type in value_mappings:
            available_randoms = value_mappings[field_type]
            for i, val in enumerate(current_vals):
                if val not in row_mappings:
                    random_val = available_randoms[i % len(available_randoms)]
                    # Apply ■ randomization during this step
                    random_val = randomize_masked_value(random_val)
                    row_mappings[val] = random_val
    
    new_row['Input'] = apply_mappings_to_text(row['Input'], row_mappings)
    new_row['Transactions'] = apply_mappings_to_transactions(row['Transactions'], row_mappings)
    new_row['Ground Truth'] = apply_mappings_to_ground_truth(row['Ground Truth'], row_mappings)
    
    # Add the two new columns
    original_values = []
    replaced_values = []
    
    for original, replacement in row_mappings.items():
        if str(original).strip() and str(replacement).strip():  # Only non-empty values
            original_values.append(str(original))
            replaced_values.append(str(replacement))
    
    new_row['Values_To_Be_Replaced'] = '\n'.join(original_values)
    new_row['Values_After_Replacement'] = '\n'.join(replaced_values)
    
    return new_row

def extract_values_from_row(row):
    """Extract all values of target fields from a row"""
    values = {field: [] for field in random_generation_functions.keys()}
    
    try:
        ground_truth_str = row['Ground Truth']
        ground_truth = json.loads(ground_truth_str) if pd.notna(ground_truth_str) else {}
        
        for transaction in ground_truth.get('alerted_transactions', []):
            if 'date' in transaction:
                values['date'].append(transaction['date'])
            if 'amount' in transaction:
                values['amount'].append(str(transaction['amount']))
            if 'from' in transaction and 'name' in transaction['from']:
                values['name'].append(transaction['from']['name'])
            if 'to' in transaction and 'name' in transaction['to']:
                values['name'].append(transaction['to']['name'])
            if 'from' in transaction and 'account_number' in transaction['from']:
                values['account_number'].append(transaction['from']['account_number'])
            if 'to' in transaction and 'account_number' in transaction['to']:
                values['account_number'].append(transaction['to']['account_number'])
            if 'from' in transaction and 'bank' in transaction['from']:
                values['bank'].append(transaction['from']['bank'])
            if 'to' in transaction and 'bank' in transaction['to']:
                values['bank'].append(transaction['to']['bank'])
            if 'cancel_amount_requested' in transaction:
                values['cancel_amount_requested'].append(str(transaction['cancel_amount_requested']))
        
        if 'police_reference' in ground_truth:
            values['police_reference'].append(ground_truth['police_reference'])
        if 'writ_no' in ground_truth:
            values['writ_no'].append(ground_truth['writ_no'])
        if 'contact_person' in ground_truth:
            values['contact_person'].append(ground_truth['contact_person'])
            
    except (json.JSONDecodeError, TypeError):
        pass
    
    for field in values:
        values[field] = list(set(values[field]))
    
    return values

def apply_mappings_to_text(text, mappings):
    """Apply value mappings to unstructured text"""
    if not text or pd.isna(text):
        return text
    
    result = str(text)
    for original, replacement in mappings.items():
        # Apply ■ randomization to replacement
        replacement = randomize_masked_value(replacement)
        result = result.replace(str(original), str(replacement))
    
    return result

def apply_mappings_to_transactions(transactions_csv, mappings):
    """Apply value mappings to transactions CSV string"""
    if not transactions_csv or pd.isna(transactions_csv):
        return transactions_csv
    
    try:
        trans_df = pd.read_csv(StringIO(transactions_csv))
        
        for col in trans_df.columns:
            trans_df[col] = trans_df[col].apply(
                lambda x: apply_single_mapping(x, mappings) if pd.notna(x) else x
            )
        
        return trans_df.to_csv(index=False)
    except Exception as e:
        print(f"Error processing transactions: {e}")
        return transactions_csv

def apply_mappings_to_ground_truth(json_str, mappings):
    """Apply value mappings to ground truth JSON string"""
    if not json_str or pd.isna(json_str):
        return json_str
    
    try:
        ground_truth = json.loads(json_str)
        ground_truth = apply_mappings_recursive(ground_truth, mappings)
        return json.dumps(ground_truth, ensure_ascii=False)
    except Exception as e:
        print(f"Error processing ground truth: {e}")
        return json_str

def apply_single_mapping(value, mappings):
    """Apply mappings to a single value"""
    str_value = str(value)
    for original, replacement in mappings.items():
        if str(original) == str_value:
            # Apply ■ randomization to replacement
            replacement = randomize_masked_value(replacement)
            return replacement
        # Apply ■ randomization to replacement
        replacement = randomize_masked_value(replacement)
        str_value = str_value.replace(str(original), str(replacement))
    return str_value

def apply_mappings_recursive(obj, mappings):
    """Apply mappings recursively to nested objects"""
    if isinstance(obj, dict):
        return {k: apply_mappings_recursive(v, mappings) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [apply_mappings_recursive(item, mappings) for item in obj]
    elif isinstance(obj, str):
        return apply_single_mapping(obj, mappings)
    else:
        return obj

def save_csv_with_indented_json(df, output_file, json_columns=['Ground Truth']):
    """Save CSV with properly indented JSON in specified columns"""
    df_copy = df.copy()
    
    def indent_json_str(json_str):
        try:
            if pd.isna(json_str) or json_str == '':
                return json_str
            obj = json.loads(json_str)
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except Exception:
            return json_str
    
    for col in json_columns:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(indent_json_str)
    
    # Ensure the new columns are at the end
    cols = df_copy.columns.tolist()
    if 'Values_To_Be_Replaced' in cols and 'Values_After_Replacement' in cols:
        # Move the new columns to the end
        cols.remove('Values_To_Be_Replaced')
        cols.remove('Values_After_Replacement')
        cols.extend(['Values_To_Be_Replaced', 'Values_After_Replacement'])
        df_copy = df_copy[cols]
    
    df_copy.to_csv(output_file, index=False, encoding='utf-8-sig')
    return df_copy

def main():
    """Main function to create randomized dataset"""
    input_file = "Dataset_Source_v5_updated_with_groundtruth.csv"
    output_file = "Dataset_Source_v5_randomized.csv"
    
    try:
        print(f"Loading dataset from {input_file}...")
        df = pd.read_csv(input_file, encoding='utf-8-sig')
        print(f"Original dataset has {len(df)} rows")
        
        print("Creating randomized rows...")
        randomized_df = create_randomized_rows(df, num_new_rows=50)
        print(f"Randomized dataset has {len(randomized_df)} rows")
        
        # Save with properly indented JSON - REPLACE THIS PART
        randomized_df = save_csv_with_indented_json(randomized_df, output_file, ['Ground Truth'])
        print(f"Randomized dataset saved to {output_file} with properly indented JSON")
        
        print("\nSample of randomized rows:")
        new_rows = randomized_df.iloc[len(df):len(df)+3]
        for idx, row in new_rows.iterrows():
            print(f"\nRow {idx}:")
            print(f"  Type: {row.get('Type', 'N/A')}")
            print(f"  Input (first 100 chars): {str(row['Input'])[:100]}...")
            
        mapping_info = {
            'original_rows': len(df),
            'randomized_rows': len(randomized_df),
            'new_rows_added': len(randomized_df) - len(df),
            'timestamp': pd.Timestamp.now().isoformat(),
            'encoding_used': 'utf-8-sig'
        }
        save_json_utf8(mapping_info, 'randomization_info.json')
        print(f"\nRandomization info saved to 'randomization_info.json'")
            
    except FileNotFoundError:
        print(f"Input file {input_file} not found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

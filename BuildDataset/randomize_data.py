import pandas as pd
import json
import random
import re
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
    
    # Track all transformations
    transformation_records = []
    
    for field_type, current_vals in current_values.items():
        if field_type in value_mappings:
            available_randoms = value_mappings[field_type]
            for i, val in enumerate(current_vals):
                if val not in row_mappings:
                    random_val = available_randoms[i % len(available_randoms)]
                    
                    # Record the transformation
                    if field_type in strict_normalization_functions:
                        normalizer = strict_normalization_functions[field_type]
                        normalized_original = normalizer(val)
                        normalized_random = normalizer(random_val)
                    else:
                        normalized_original = val
                        normalized_random = random_val
                    
                    # Apply ■ randomization during this step
                    random_val_final = randomize_masked_value(random_val)
                    normalized_random_final = randomize_masked_value(normalized_random)
                    
                    row_mappings[val] = random_val_final
                    
                    # Record all four values
                    transformation_records.append({
                        'normalized_original': str(normalized_original),
                        'original_value': str(val),
                        'randomized_normalized': str(normalized_random_final),
                        'randomized_value': str(random_val_final)
                    })
    
    new_row['Input'] = apply_mappings_to_text(row['Input'], row_mappings)
    new_row['Transactions'] = apply_mappings_to_transactions(row['Transactions'], row_mappings)
    new_row['Ground Truth'] = apply_mappings_to_ground_truth(row['Ground Truth'], row_mappings)
    
    # Create the four columns with newline-separated values
    normalized_original_values = []
    original_values = []
    randomized_normalized_values = []
    randomized_values = []
    
    for record in transformation_records:
        if record['original_value'].strip():  # Only non-empty values
            normalized_original_values.append(record['normalized_original'])
            original_values.append(record['original_value'])
            randomized_normalized_values.append(record['randomized_normalized'])
            randomized_values.append(record['randomized_value'])
    
    new_row['Normalized_Original'] = '\n'.join(normalized_original_values)
    new_row['Original_Values'] = '\n'.join(original_values)
    new_row['Randomized_Normalized'] = '\n'.join(randomized_normalized_values)
    new_row['Randomized_Values'] = '\n'.join(randomized_values)
    
    return new_row

def extract_values_from_row(row):
    """Extract all values of target fields from a row with better amount handling - exclude nulls"""
    values = {field: [] for field in random_generation_functions.keys()}
    
    try:
        ground_truth_str = row['Ground Truth']
        ground_truth = json.loads(ground_truth_str) if pd.notna(ground_truth_str) else {}
        
        for transaction in ground_truth.get('alerted_transactions', []):
            # Date - exclude null/None
            if 'date' in transaction and transaction['date'] is not None and str(transaction['date']).strip():
                values['date'].append(transaction['date'])
                
            # Amount - exclude null/None
            if 'amount' in transaction and transaction['amount'] is not None:
                amount_val = str(transaction['amount'])
                if amount_val.strip():  # Exclude empty strings
                    values['amount'].append(amount_val)
                    # Use the function from data_processor
                    from data_processor import strict_normalization_functions
                    normalized_amount = strict_normalization_functions['amount'](amount_val)
                    if normalized_amount != amount_val and normalized_amount.strip():
                        values['amount'].append(normalized_amount)
            
            # Names - exclude null/None/empty
            if 'from' in transaction and 'name' in transaction['from'] and transaction['from']['name'] is not None:
                name_val = str(transaction['from']['name']).strip()
                if name_val:
                    values['name'].append(name_val)
            if 'to' in transaction and 'name' in transaction['to'] and transaction['to']['name'] is not None:
                name_val = str(transaction['to']['name']).strip()
                if name_val:
                    values['name'].append(name_val)
            
            # Account numbers - exclude null/None/empty
            if 'from' in transaction and 'account_number' in transaction['from'] and transaction['from']['account_number'] is not None:
                account_val = str(transaction['from']['account_number']).strip()
                if account_val:
                    values['account_number'].append(account_val)
            if 'to' in transaction and 'account_number' in transaction['to'] and transaction['to']['account_number'] is not None:
                account_val = str(transaction['to']['account_number']).strip()
                if account_val:
                    values['account_number'].append(account_val)
            
            # Banks - exclude null/None/empty
            if 'from' in transaction and 'bank' in transaction['from'] and transaction['from']['bank'] is not None:
                bank_val = str(transaction['from']['bank']).strip()
                if bank_val:
                    values['bank'].append(bank_val)
            if 'to' in transaction and 'bank' in transaction['to'] and transaction['to']['bank'] is not None:
                bank_val = str(transaction['to']['bank']).strip()
                if bank_val:
                    values['bank'].append(bank_val)
            
            # Cancel amount - exclude null/None/empty
            if 'cancel_amount_requested' in transaction and transaction['cancel_amount_requested'] is not None:
                cancel_amount_val = str(transaction['cancel_amount_requested']).strip()
                if cancel_amount_val:
                    values['cancel_amount_requested'].append(cancel_amount_val)
                    normalized_cancel = strict_normalization_functions['cancel_amount_requested'](cancel_amount_val)
                    if normalized_cancel != cancel_amount_val and normalized_cancel.strip():
                        values['cancel_amount_requested'].append(normalized_cancel)
        
        # Other fields - exclude null/None/empty
        if 'police_reference' in ground_truth and ground_truth['police_reference'] is not None:
            police_val = str(ground_truth['police_reference']).strip()
            if police_val:
                values['police_reference'].append(police_val)
                
        if 'writ_no' in ground_truth and ground_truth['writ_no'] is not None:
            writ_val = str(ground_truth['writ_no']).strip()
            if writ_val:
                values['writ_no'].append(writ_val)
                
        if 'contact_person' in ground_truth and ground_truth['contact_person'] is not None:
            contact_val = str(ground_truth['contact_person']).strip()
            if contact_val:
                values['contact_person'].append(contact_val)
            
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
    """Apply value mappings to ground truth JSON string with proper amount handling"""
    if not json_str or pd.isna(json_str):
        return json_str
    
    try:
        ground_truth = json.loads(json_str)
        
        # Apply mappings recursively with special handling for amounts
        ground_truth = apply_mappings_recursive_enhanced(ground_truth, mappings)
        
        return json.dumps(ground_truth, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error processing ground truth: {e}")
        return json_str

def apply_mappings_recursive_enhanced(obj, mappings):
    """Apply mappings recursively with enhanced amount handling"""
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if k in ['amount', 'cancel_amount_requested'] and v is not None:
                # Handle amount fields specifically
                str_value = str(v)
                # Try exact match first
                if str_value in mappings:
                    try:
                        # Convert to number if possible
                        new_obj[k] = float(mappings[str_value]) if '.' in mappings[str_value] else int(mappings[str_value])
                    except ValueError:
                        new_obj[k] = mappings[str_value]
                else:
                    # Try normalized amount matching
                    from data_processor import strict_normalization_functions
                    normalized_amount = strict_normalization_functions['amount'](str_value)
                    if normalized_amount in mappings:
                        try:
                            new_obj[k] = float(mappings[normalized_amount]) if '.' in mappings[normalized_amount] else int(mappings[normalized_amount])
                        except ValueError:
                            new_obj[k] = mappings[normalized_amount]
                    else:
                        new_obj[k] = v
            else:
                new_obj[k] = apply_mappings_recursive_enhanced(v, mappings)
        return new_obj
    elif isinstance(obj, list):
        return [apply_mappings_recursive_enhanced(item, mappings) for item in obj]
    elif isinstance(obj, str):
        return apply_single_mapping(obj, mappings)
    elif isinstance(obj, (int, float)) and obj is not None:
        # Handle numeric values
        str_value = str(obj)
        if str_value in mappings:
            try:
                return float(mappings[str_value]) if '.' in mappings[str_value] else int(mappings[str_value])
            except ValueError:
                return mappings[str_value]
        else:
            # Try normalized amount matching
            from data_processor import strict_normalization_functions
            normalized_amount = strict_normalization_functions['amount'](str_value)
            if normalized_amount in mappings:
                try:
                    return float(mappings[normalized_amount]) if '.' in mappings[normalized_amount] else int(mappings[normalized_amount])
                except ValueError:
                    return mappings[normalized_amount]
        return obj
    else:
        return obj

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
    
    # Ensure the new columns are at the end in the correct order
    cols = df_copy.columns.tolist()
    new_cols = ['Normalized_Original', 'Original_Values', 'Randomized_Normalized', 'Randomized_Values']
    
    for col in new_cols:
        if col in cols:
            cols.remove(col)
    cols.extend([col for col in new_cols if col in df_copy.columns])
    
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
        
        # Save with properly indented JSON
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

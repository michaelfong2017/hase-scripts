import pandas as pd
import json
from io import StringIO
import re
from collections import defaultdict
import ast

def safe_parse_csv(csv_str):
    """Safely parse CSV string, handling various formats"""
    if pd.isna(csv_str) or not csv_str:
        return None
    
    try:
        csv_str = str(csv_str).strip()
        
        # Handle single values (not actual CSV)
        if ',' not in csv_str and '\n' not in csv_str:
            return pd.DataFrame([csv_str], columns=['value'])
        
        # Try to parse as CSV
        df = pd.read_csv(StringIO(csv_str))
        return df
    except Exception as e:
        # If CSV parsing fails, treat as single value
        return pd.DataFrame([str(csv_str)], columns=['value'])

def safe_parse_source_data(data_str):
    """Safely parse Source column data which may contain various formats"""
    if pd.isna(data_str) or not data_str:
        return None, "empty"
    
    data_str = str(data_str).strip()
    
    # Check if it's a datetime object string
    if 'datetime.datetime' in data_str:
        return data_str, "datetime"
    
    # Check if it's an AST object string
    if '<_ast.' in data_str:
        return data_str, "ast_object"
    
    # Check if it's a simple number
    try:
        float(data_str)
        return data_str, "number"
    except ValueError:
        pass
    
    # Check if it contains leading zeros (problematic for JSON)
    if re.match(r'^0\d+', data_str):
        return data_str, "leading_zero_number"
    
    # Try to parse as JSON
    try:
        parsed = json.loads(data_str)
        return parsed, "json"
    except:
        pass
    
    # Try to evaluate as Python literal (with safety checks)
    try:
        # Only try literal_eval on simple strings
        if not any(dangerous in data_str for dangerous in ['import', 'exec', 'eval', '__']):
            parsed = ast.literal_eval(data_str)
            return parsed, "literal"
    except:
        pass
    
    return data_str, "string"

def extract_field_info_from_transactions(df):
    """Extract field information from Transaction columns"""
    if df is None:
        return []
    
    fields = []
    
    # Get column names
    if hasattr(df, 'columns'):
        for col in df.columns:
            fields.append(f"column_{col}")
    
    # Get unique values to understand data patterns
    for col in df.columns:
        unique_vals = df[col].dropna().unique()[:5]  # Sample first 5 unique values
        for val in unique_vals:
            val_str = str(val)
            if len(val_str) > 0 and val_str not in ['0', 'nan']:
                fields.append(f"value_{val_str}")
    
    return fields

def analyze_excel_file_robust(file_path):
    """Robust analysis of Excel file handling various data formats"""
    try:
        # Read the Excel file
        df = pd.read_excel(file_path, engine='openpyxl')
        print(f"Successfully loaded Excel file with {len(df)} rows and {len(df.columns)} columns")
        
        # Find Transaction_ and Source_ columns
        transaction_cols = [col for col in df.columns if col.startswith('Transaction_')]
        source_cols = [col for col in df.columns if col.startswith('Source_')]
        
        print(f"\nFound {len(transaction_cols)} Transaction_ columns")
        print(f"Found {len(source_cols)} Source_ columns")
        
        # Analyze Transaction_ columns
        transaction_analysis = {}
        
        print("\n=== ANALYZING TRANSACTION COLUMNS ===")
        for col in transaction_cols:
            print(f"\nAnalyzing {col}...")
            non_null_values = df[col].dropna()
            print(f"  Non-null values: {len(non_null_values)}")
            
            # Sample analysis
            sample_data = []
            field_patterns = set()
            
            sample_size = min(10, len(non_null_values))
            for i in range(sample_size):
                raw_value = non_null_values.iloc[i]
                parsed_csv = safe_parse_csv(raw_value)
                
                if parsed_csv is not None:
                    fields = extract_field_info_from_transactions(parsed_csv)
                    field_patterns.update(fields)
                    
                    if i == 0:  # Show first sample
                        print(f"  Sample data shape: {parsed_csv.shape}")
                        print(f"  Sample columns: {list(parsed_csv.columns)}")
                        if len(parsed_csv) > 0:
                            print(f"  First row: {parsed_csv.iloc[0].to_dict()}")
            
            transaction_analysis[col] = {
                'non_null_count': len(non_null_values),
                'field_patterns': list(field_patterns),
                'sample_values': [str(x) for x in non_null_values.head(3).tolist()]
            }
            
            print(f"  Extracted patterns: {len(field_patterns)} unique patterns")
        
        # Analyze Source_ columns
        source_analysis = {}
        
        print("\n=== ANALYZING SOURCE COLUMNS ===")
        for col in source_cols:
            print(f"\nAnalyzing {col}...")
            non_null_values = df[col].dropna()
            print(f"  Non-null values: {len(non_null_values)}")
            
            # Analyze data types and patterns
            data_types = defaultdict(int)
            sample_values = []
            
            sample_size = min(10, len(non_null_values))
            for i in range(sample_size):
                raw_value = non_null_values.iloc[i]
                parsed_data, data_type = safe_parse_source_data(raw_value)
                data_types[data_type] += 1
                
                if i < 3:  # Keep first 3 samples
                    sample_values.append({
                        'raw': str(raw_value)[:100],
                        'type': data_type,
                        'parsed': str(parsed_data)[:100] if parsed_data != raw_value else "same"
                    })
            
            source_analysis[col] = {
                'non_null_count': len(non_null_values),
                'data_types': dict(data_types),
                'sample_values': sample_values
            }
            
            print(f"  Data types found: {dict(data_types)}")
            for sample in sample_values:
                print(f"    Type: {sample['type']}, Raw: {sample['raw'][:50]}...")
        
        # Field mapping analysis
        print("\n=== FIELD MAPPING ANALYSIS ===")
        
        # Map Transaction columns to target fields
        target_fields = ['date', 'amount', 'currency', 'name', 'account_number', 'bank', 'channel']
        
        transaction_mappings = {}
        for target in target_fields:
            matches = []
            for col in transaction_cols:
                col_lower = col.lower()
                if target in col_lower or any(keyword in col_lower for keyword in [target]):
                    matches.append(col)
            if matches:
                transaction_mappings[target] = matches
        
        source_mappings = {}
        for target in target_fields:
            matches = []
            for col in source_cols:
                col_lower = col.lower()
                if target in col_lower or any(keyword in col_lower for keyword in [target]):
                    matches.append(col)
            if matches:
                source_mappings[target] = matches
        
        print("\nTransaction column mappings:")
        for target, cols in transaction_mappings.items():
            print(f"  {target}: {cols}")
        
        print("\nSource column mappings:")
        for target, cols in source_mappings.items():
            print(f"  {target}: {cols}")
        
        # Save comprehensive results
        results = {
            'file_info': {
                'rows': len(df),
                'columns': len(df.columns),
                'transaction_columns': len(transaction_cols),
                'source_columns': len(source_cols)
            },
            'transaction_analysis': transaction_analysis,
            'source_analysis': source_analysis,
            'field_mappings': {
                'transaction_mappings': transaction_mappings,
                'source_mappings': source_mappings
            },
            'column_lists': {
                'transaction_columns': transaction_cols,
                'source_columns': source_cols
            }
        }
        
        with open('excel_analysis_results_robust.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nDetailed results saved to 'excel_analysis_results_robust.json'")
        
        # Generate field extraction recommendations
        print("\n=== FIELD EXTRACTION RECOMMENDATIONS ===")
        
        print("\nFor Transaction columns (appear to contain single values, not CSV):")
        for col in transaction_cols:
            field_name = col.replace('Transaction_', '').lower().replace(' ', '_')
            print(f"  {col} -> extract as '{field_name}' (direct value)")
        
        print("\nFor Source columns (contain various data types):")
        for col in source_cols:
            field_name = col.replace('Source_', '').lower().replace(' ', '_')
            analysis = source_analysis.get(col, {})
            data_types = analysis.get('data_types', {})
            
            if 'ast_object' in data_types:
                print(f"  {col} -> '{field_name}' (WARNING: Contains AST objects, needs special handling)")
            elif 'leading_zero_number' in data_types:
                print(f"  {col} -> '{field_name}' (WARNING: Contains leading zeros, treat as string)")
            elif 'datetime' in data_types:
                print(f"  {col} -> '{field_name}' (Contains datetime objects)")
            elif 'number' in data_types:
                print(f"  {col} -> '{field_name}' (Numeric values)")
            else:
                print(f"  {col} -> '{field_name}' (Mixed/String values)")
        
        return results
        
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error analyzing file: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_extraction_code(results):
    """Generate Python code for extracting data from the Excel file"""
    if not results:
        return
    
    print("\n=== GENERATED EXTRACTION CODE ===")
    
    code = '''
import pandas as pd
import json
import ast
import re

def extract_data_from_excel(file_path):
    """Extract and normalize data from the Excel file"""
    df = pd.read_excel(file_path, engine='openpyxl')
    
    extracted_data = []
    
    for idx, row in df.iterrows():
        record = {}
        
        # Extract Transaction fields (direct values)
'''
    
    transaction_cols = results['column_lists']['transaction_columns']
    for col in transaction_cols:
        field_name = col.replace('Transaction_', '').lower().replace(' ', '_').replace('(', '').replace(')', '')
        code += f'        record["{field_name}"] = str(row["{col}"]) if pd.notna(row["{col}"]) else None\n'
    
    code += '''
        # Extract Source fields (with type handling)
'''
    
    source_cols = results['column_lists']['source_columns']
    for col in source_cols:
        field_name = col.replace('Source_', '').lower().replace(' ', '_').replace('(', '').replace(')', '')
        code += f'''        # Handle {col}
        source_val = row["{col}"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["{field_name}"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["{field_name}"] = source_str  # Keep datetime string
            elif re.match(r'^0\\d+', source_str):
                record["{field_name}"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["{field_name}"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["{field_name}"] = source_str
                except:
                    record["{field_name}"] = source_str
        else:
            record["{field_name}"] = None
        
'''
    
    code += '''        extracted_data.append(record)
    
    return pd.DataFrame(extracted_data)

# Usage
if __name__ == "__main__":
    result_df = extract_data_from_excel("Transaction_From_IR_and_Source.xlsx")
    result_df.to_csv("extracted_data.csv", index=False, encoding='utf-8-sig')
    print(f"Extracted {len(result_df)} records to extracted_data.csv")
'''
    
    with open('data_extraction_code.py', 'w', encoding='utf-8') as f:
        f.write(code)
    
    print("Generated extraction code saved to 'data_extraction_code.py'")
    print("\nYou can run this code to extract the data:")
    print("python data_extraction_code.py")

if __name__ == "__main__":
    file_path = "Transaction_From_IR_and_Source.xlsx"
    
    print("Starting robust Excel file analysis...")
    results = analyze_excel_file_robust(file_path)
    
    if results:
        print("\n" + "="*60)
        print("Analysis completed successfully!")
        generate_extraction_code(results)
    else:
        print("Analysis failed. Please check the file and try again.")

import os
import pandas as pd
import uuid
import re

def add_transaction_ids_to_csvs():
    """Add Transaction ID column to all transaction CSV files"""
    transaction_dir = '../Input Data/Transaction Records'
    pattern = re.compile(r'Case_(\d+)_transaction_records\.csv')
    
    updated_files = []
    
    # Walk through the directory recursively
    for root, dirs, files in os.walk(transaction_dir):
        for file in files:
            if pattern.match(file):
                file_path = os.path.join(root, file)
                try:
                    df = pd.read_csv(file_path)
                    
                    # Add Transaction ID column if it doesn't exist
                    if 'Transaction ID' not in df.columns:
                        df['Transaction ID'] = [str(uuid.uuid4()) for _ in range(len(df))]
                        # Save back to the same file
                        df.to_csv(file_path, index=False)
                        updated_files.append(file_path)
                        print(f'Added Transaction ID to: {file_path}')
                    else:
                        print(f'Transaction ID already exists in: {file_path}')
                        
                except Exception as e:
                    print(f'Error processing {file_path}: {e}')
    
    return updated_files

def create_csv_with_transaction_ids():
    """Create a new CSV file with Transaction IDs from Excel data"""
    excel_path = '../Input Data Summary/Transaction_From_IR_and_Source.xlsx'
    output_csv_path = '../Input Data Summary/Transaction_From_IR_and_Source_with_TransactionID.csv'
    
    # Check if Excel file exists
    if not os.path.exists(excel_path):
        print(f"Excel file not found: {excel_path}")
        return
    
    # Read the Excel file (all sheets) and combine them
    all_sheets = pd.read_excel(excel_path, sheet_name=None, dtype=str)
    combined_df = pd.concat(all_sheets.values(), ignore_index=True)
    
    print(f"Combined {len(all_sheets)} sheets into one DataFrame with {len(combined_df)} rows")
    
    # Normalize Case Number column
    if 'Case Number' in combined_df.columns:
        combined_df['Case Number'] = combined_df['Case Number'].astype(str).str.strip()
    
    # Find the index of 'GroundTruth_Fraud Payment' column
    if 'GroundTruth_Fraud Payment' in combined_df.columns:
        fraud_payment_idx = combined_df.columns.get_loc('GroundTruth_Fraud Payment')
    else:
        print("'GroundTruth_Fraud Payment' column not found")
        return
    
    # Build mapping from CSV files
    transaction_dir = '../Input Data/Transaction Records'
    pattern = re.compile(r'Case_(\d+)_transaction_records\.csv')
    mapping = {}
    
    for root, dirs, files in os.walk(transaction_dir):
        for file in files:
            match = pattern.match(file)
            if match:
                case_num = match.group(1)
                file_path = os.path.join(root, file)
                try:
                    df = pd.read_csv(file_path, dtype=str)
                    
                    # Build mapping from Fraud Payment to Transaction ID
                    if 'Fraud Payment' in df.columns and 'Transaction ID' in df.columns:
                        for idx, row in df.iterrows():
                            fraud_payment = row['Fraud Payment'].strip() if pd.notna(row['Fraud Payment']) else None
                            key = (case_num.strip(), fraud_payment)
                            mapping[key] = row['Transaction ID']
                            
                        print(f'Loaded {len(df)} transaction mappings from Case {case_num}')
                except Exception as e:
                    print(f'Error reading {file_path}: {e}')
    
    print(f'Total mappings created: {len(mapping)}')
    
    # Assign Transaction ID based on Case Number and Fraud Payment
    transaction_ids = []
    matches_found = 0
    
    for idx, row in combined_df.iterrows():
        case_num = str(row['Case Number']).strip() if pd.notna(row['Case Number']) else None
        fraud_payment = str(row['GroundTruth_Fraud Payment']).strip() if pd.notna(row['GroundTruth_Fraud Payment']) else None
        key = (case_num, fraud_payment)
        
        transaction_id = mapping.get(key, None)
        transaction_ids.append(transaction_id)
        
        if transaction_id is not None:
            matches_found += 1
    
    # Insert the Transaction ID column after GroundTruth_Fraud Payment
    combined_df.insert(fraud_payment_idx + 1, 'Transaction ID', transaction_ids)
    
    # Save to new CSV file
    combined_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    
    print(f"Created new CSV file: {output_csv_path}")
    print(f"Matched {matches_found} out of {len(combined_df)} rows with Transaction IDs")

def main():
    """Main function to execute both operations"""
    print("Step 1: Adding Transaction IDs to CSV files...")
    updated_csvs = add_transaction_ids_to_csvs()
    
    print(f"\nStep 2: Creating new CSV file with Transaction IDs...")
    create_csv_with_transaction_ids()
    
    print(f"\nProcess completed!")
    print(f"Updated {len(updated_csvs)} CSV files")
    print(f"Created new CSV file: ../Input Data Summary/Transaction_From_IR_and_Source_with_TransactionID.csv")

if __name__ == "__main__":
    main()

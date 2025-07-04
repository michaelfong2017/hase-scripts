import os
import pandas as pd
import uuid
import re

def add_transaction_ids_to_csvs():
    """Add Transaction ID column to all transaction CSV files"""
    transaction_dir = 'Transaction Records'
    pattern = re.compile(r'Case_([a-zA-Z]+)_transaction_records\.csv')
    
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

def main():
    """Main function to execute both operations"""
    print("Step 1: Adding Transaction IDs to CSV files...")
    updated_csvs = add_transaction_ids_to_csvs()
  
if __name__ == "__main__":
    main()

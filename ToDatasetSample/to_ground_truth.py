import pandas as pd
import json

def extract_and_update_ground_truth(transactions_file, dataset_file):
    """
    Extract transaction data from transactions.csv and update Ground Truth columns
    in Dataset_Source_v5.csv for matching [case, intelligence] pairs
    Following the exact JSON schema provided with proper formatting
    
    Args:
        transactions_file (str): Path to the transactions CSV file
        dataset_file (str): Path to the Dataset_Source_v5 CSV file
    """
    # Read both CSV files
    transactions_df = pd.read_csv(transactions_file)
    dataset_df = pd.read_csv(dataset_file)
    
    def get_value(col_name, row):
        value = row.get(col_name, None)
        if pd.isna(value) or value == "" or str(value).lower() == "nan":
            return None
        return value

    # Group transactions by Case Number and Intelligence Number
    grouped_data = {}
    
    for _, row in transactions_df.iterrows():
        case_number = get_value('Case Number', row)
        intelligence_number = get_value('Intelligence Number', row)
        
        # Create unique key for grouping
        group_key = f"{case_number}_{intelligence_number}"
        
        if group_key not in grouped_data:
            grouped_data[group_key] = []
        
        # Create transaction object following exact schema
        transaction = {
            "date": get_value('Ground_Truth_Transaction Date (value)', row),
            "amount": get_value('Ground_Truth_Originating Amount', row),
            "currency": get_value('Ground_Truth_Originating Currency', row),
            "from": {
                "name": get_value('Ground_Truth_Originator Name', row),
                "account_number": get_value('Ground_Truth_Originator Account Number', row),
                "bank": get_value('Ground_Truth_Originator Bank Raw', row)
            },
            "to": {
                "name": get_value('Ground_Truth_Beneficiary Name', row),
                "account_number": get_value('Ground_Truth_Beneficiary Account Number', row),
                "bank": get_value('Ground_Truth_Beneficiary Bank Raw', row)
            },
            "channel": get_value('Ground_Truth_Transaction Channel', row)
        }
        
        grouped_data[group_key].append(transaction)
    
    # Update Dataset_Source_v5.csv with Ground Truth data
    for idx, row in dataset_df.iterrows():
        case_number = row.get('Case Number')
        intelligence_number = row.get('Intelligence Number')
        group_key = f"{case_number}_{intelligence_number}"
        
        if group_key in grouped_data:
            # Create JSON object following exact schema
            json_object = {
                "alerted_transactions": grouped_data[group_key]
            }
            
            # Convert to JSON string with proper formatting
            json_data = json.dumps(json_object, indent=2, ensure_ascii=False)
            
            # Update the Ground Truth column
            if 'Ground_Truth_Alerted_Transactions' in dataset_df.columns:
                dataset_df.at[idx, 'Ground_Truth_Alerted_Transactions'] = json_data
            else:
                # Create the column if it doesn't exist
                dataset_df.loc[idx, 'Ground_Truth_Alerted_Transactions'] = json_data
    
    # Save the updated dataset
    dataset_df.to_csv('Dataset_Source_v5_updated.csv', index=False)
    print("Updated Dataset_Source_v5.csv with Ground Truth data")
    
    return dataset_df

# Usage
updated_df = extract_and_update_ground_truth('transactions.csv', 'Dataset_Source_v5.csv')

# Optional: Preview the JSON structure for verification
def preview_json_output(transactions_file):
    transactions_df = pd.read_csv(transactions_file)
    
    def get_value(col_name, row):
        value = row.get(col_name, None)
        if pd.isna(value) or value == "" or str(value).lower() == "nan":
            return None
        return value

    # Get first few transactions as example
    sample_transactions = []
    for _, row in transactions_df.head(3).iterrows():
        transaction = {
            "date": get_value('Ground_Truth_Transaction Date (value)', row),
            "amount": get_value('Ground_Truth_Originating Amount', row),
            "currency": get_value('Ground_Truth_Originating Currency', row),
            "from": {
                "name": get_value('Ground_Truth_Originator Name', row),
                "account_number": get_value('Ground_Truth_Originator Account Number', row),
                "bank": get_value('Ground_Truth_Originator Bank Raw', row)
            },
            "to": {
                "name": get_value('Ground_Truth_Beneficiary Name', row),
                "account_number": get_value('Ground_Truth_Beneficiary Account Number', row),
                "bank": get_value('Ground_Truth_Beneficiary Bank Raw', row)
            },
            "channel": get_value('Ground_Truth_Transaction Channel', row)
        }
        sample_transactions.append(transaction)
    
    # Create sample JSON output
    sample_json = {
        "alerted_transactions": sample_transactions
    }
    
    print("Sample JSON output:")
    print(json.dumps(sample_json, indent=2, ensure_ascii=False))

# Preview the output format
preview_json_output('transactions.csv')


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
        record["fraud_payment"] = str(row["Transaction_Fraud Payment"]) if pd.notna(row["Transaction_Fraud Payment"]) else None
        record["located"] = str(row["Transaction_Located"]) if pd.notna(row["Transaction_Located"]) else None
        record["transaction_date_value"] = str(row["Transaction_Transaction Date (value)"]) if pd.notna(row["Transaction_Transaction Date (value)"]) else None
        record["originating_amount"] = str(row["Transaction_Originating Amount"]) if pd.notna(row["Transaction_Originating Amount"]) else None
        record["originating_currency"] = str(row["Transaction_Originating Currency"]) if pd.notna(row["Transaction_Originating Currency"]) else None
        record["originator_name"] = str(row["Transaction_Originator Name"]) if pd.notna(row["Transaction_Originator Name"]) else None
        record["originator_account_number"] = str(row["Transaction_Originator Account Number"]) if pd.notna(row["Transaction_Originator Account Number"]) else None
        record["originator_bank_raw"] = str(row["Transaction_Originator Bank Raw"]) if pd.notna(row["Transaction_Originator Bank Raw"]) else None
        record["beneficiary_name"] = str(row["Transaction_Beneficiary Name"]) if pd.notna(row["Transaction_Beneficiary Name"]) else None
        record["beneficiary_account_number"] = str(row["Transaction_Beneficiary Account Number"]) if pd.notna(row["Transaction_Beneficiary Account Number"]) else None
        record["beneficiary_bank_raw"] = str(row["Transaction_Beneficiary Bank Raw"]) if pd.notna(row["Transaction_Beneficiary Bank Raw"]) else None

        # Extract Source fields (with type handling)
        # Handle Source_Transaction Date (value)
        source_val = row["Source_Transaction Date (value)"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["transaction_date_value"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["transaction_date_value"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["transaction_date_value"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["transaction_date_value"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["transaction_date_value"] = source_str
                except:
                    record["transaction_date_value"] = source_str
        else:
            record["transaction_date_value"] = None
        
        # Handle Source_Originating Amount
        source_val = row["Source_Originating Amount"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["originating_amount"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["originating_amount"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["originating_amount"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["originating_amount"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["originating_amount"] = source_str
                except:
                    record["originating_amount"] = source_str
        else:
            record["originating_amount"] = None
        
        # Handle Source_Originating Currency
        source_val = row["Source_Originating Currency"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["originating_currency"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["originating_currency"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["originating_currency"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["originating_currency"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["originating_currency"] = source_str
                except:
                    record["originating_currency"] = source_str
        else:
            record["originating_currency"] = None
        
        # Handle Source_Cancel Amount Requested
        source_val = row["Source_Cancel Amount Requested"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["cancel_amount_requested"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["cancel_amount_requested"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["cancel_amount_requested"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["cancel_amount_requested"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["cancel_amount_requested"] = source_str
                except:
                    record["cancel_amount_requested"] = source_str
        else:
            record["cancel_amount_requested"] = None
        
        # Handle Source_Originator Name
        source_val = row["Source_Originator Name"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["originator_name"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["originator_name"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["originator_name"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["originator_name"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["originator_name"] = source_str
                except:
                    record["originator_name"] = source_str
        else:
            record["originator_name"] = None
        
        # Handle Source_Originator Account Number
        source_val = row["Source_Originator Account Number"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["originator_account_number"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["originator_account_number"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["originator_account_number"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["originator_account_number"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["originator_account_number"] = source_str
                except:
                    record["originator_account_number"] = source_str
        else:
            record["originator_account_number"] = None
        
        # Handle Source_Originator Bank Raw
        source_val = row["Source_Originator Bank Raw"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["originator_bank_raw"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["originator_bank_raw"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["originator_bank_raw"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["originator_bank_raw"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["originator_bank_raw"] = source_str
                except:
                    record["originator_bank_raw"] = source_str
        else:
            record["originator_bank_raw"] = None
        
        # Handle Source_Beneficiary Name
        source_val = row["Source_Beneficiary Name"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["beneficiary_name"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["beneficiary_name"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["beneficiary_name"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["beneficiary_name"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["beneficiary_name"] = source_str
                except:
                    record["beneficiary_name"] = source_str
        else:
            record["beneficiary_name"] = None
        
        # Handle Source_Beneficiary Account Number
        source_val = row["Source_Beneficiary Account Number"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["beneficiary_account_number"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["beneficiary_account_number"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["beneficiary_account_number"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["beneficiary_account_number"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["beneficiary_account_number"] = source_str
                except:
                    record["beneficiary_account_number"] = source_str
        else:
            record["beneficiary_account_number"] = None
        
        # Handle Source_Beneficiary Bank Raw
        source_val = row["Source_Beneficiary Bank Raw"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["beneficiary_bank_raw"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["beneficiary_bank_raw"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["beneficiary_bank_raw"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["beneficiary_bank_raw"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["beneficiary_bank_raw"] = source_str
                except:
                    record["beneficiary_bank_raw"] = source_str
        else:
            record["beneficiary_bank_raw"] = None
        
        # Handle Source_Transaction Channel
        source_val = row["Source_Transaction Channel"]
        if pd.notna(source_val):
            source_str = str(source_val)
            if '<_ast.' in source_str:
                record["transaction_channel"] = "AST_OBJECT"  # Placeholder for AST objects
            elif 'datetime.datetime' in source_str:
                record["transaction_channel"] = source_str  # Keep datetime string
            elif re.match(r'^0\d+', source_str):
                record["transaction_channel"] = source_str  # Keep leading zeros as string
            else:
                try:
                    # Try to convert to appropriate type
                    if source_str.replace('.', '').isdigit():
                        record["transaction_channel"] = float(source_str) if '.' in source_str else int(source_str)
                    else:
                        record["transaction_channel"] = source_str
                except:
                    record["transaction_channel"] = source_str
        else:
            record["transaction_channel"] = None
        
        extracted_data.append(record)
    
    return pd.DataFrame(extracted_data)

# Usage
if __name__ == "__main__":
    result_df = extract_data_from_excel("Transaction_From_IR_and_Source.xlsx")
    result_df.to_csv("extracted_data.csv", index=False, encoding='utf-8-sig')
    print(f"Extracted {len(result_df)} records to extracted_data.csv")

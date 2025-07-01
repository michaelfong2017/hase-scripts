import pandas as pd
import os
import re
import json
import numpy as np
import random
from io import StringIO
from datetime import datetime

def safe_int_convert(series):
    """Safely convert a series to int, handling float strings like '7.0'"""
    return series.astype(str).str.strip().astype(float).astype(int)

def parse_intelligence_numbers(val):
    """Parse intelligence number(s), handling cases like '5', '5&6', '7.0' etc."""
    if pd.isnull(val):
        return []
    if isinstance(val, (int, float)):
        return [int(val)]
    # Split on '&', strip whitespace, convert to float then int
    result = []
    for x in str(val).split('&'):
        x = x.strip()
        if x:
            try:
                result.append(int(float(x)))
            except ValueError:
                continue
    return result

def remove_last_fraud_payment_column(csv_content):
    """Remove the last 'Fraud Payment' column from a CSV content string"""
    # Read CSV content into DataFrame
    df = pd.read_csv(StringIO(csv_content))
    # Find columns that contain 'Fraud Payment'
    fraud_payment_cols = [col for col in df.columns if 'Fraud Payment' in col]
    if fraud_payment_cols:
        # Remove the last such column
        last_col = fraud_payment_cols[-1]
        df = df.drop(columns=[last_col])
    # Return CSV string without index
    return df.to_csv(index=False)

def convert_to_bool(val):
    """Convert TRUE/FALSE strings or booleans to actual booleans"""
    if isinstance(val, str):
        if val.upper() == 'TRUE':
            return True
        elif val.upper() == 'FALSE':
            return False
    return val

def treat_null(val):
    """Treat 'null' string and empty cells as None"""
    if pd.isnull(val):
        return None
    if isinstance(val, str) and val.strip().lower() == 'null':
        return None
    if isinstance(val, str) and val.strip() == '':
        return None
    return val

def clean_date_string(date_str):
    """Clean date strings to remove time portion if it's 00:00:00"""
    if pd.isnull(date_str) or date_str is None:
        return None
    
    date_str = str(date_str).strip()
    
    # If it ends with " 00:00:00", remove that part
    if date_str.endswith(" 00:00:00"):
        return date_str.replace(" 00:00:00", "")
    
    return date_str

def convert_to_number(val):
    """Convert string values to numbers, handling 'null' and empty values"""
    val = treat_null(val)  # First handle null/empty values
    if val is None:
        return None
    try:
        # Try to convert to float first, then to int if it's a whole number
        num = float(val)
        if num.is_integer():
            return int(num)
        return num
    except (ValueError, TypeError):
        return None

def randomly_remove_transactions(csv_content, removal_probability=0.3):
    """Randomly remove some transactions from CSV content and return removed transaction IDs"""
    if csv_content is None or pd.isnull(csv_content):
        return csv_content, []
    
    try:
        df = pd.read_csv(StringIO(csv_content))
        if 'Transaction ID' not in df.columns or len(df) == 0:
            return csv_content, []
        
        # Randomly select transactions to remove
        num_to_remove = max(1, int(len(df) * removal_probability))
        indices_to_remove = random.sample(range(len(df)), min(num_to_remove, len(df)))
        
        # Get the Transaction IDs of removed transactions
        removed_transaction_ids = df.iloc[indices_to_remove]['Transaction ID'].tolist()
        
        # Remove the selected transactions
        df_filtered = df.drop(indices_to_remove)
        
        return df_filtered.to_csv(index=False), removed_transaction_ids
    except Exception as e:
        print(f"Error processing transactions: {e}")
        return csv_content, []

def build_ground_truth_with_removed_transactions(gt_row, transaction_rows, row_type, removed_transaction_ids):
    """Build ground truth with removed transactions marked as can_be_located=False"""
    alerted_transactions = []
    
    for tx_row in transaction_rows:
        # Get transaction references from Transaction ID column and split by semicolon
        transaction_id_raw = tx_row.get("Transaction ID", None)
        transaction_references = []
        if transaction_id_raw and pd.notna(transaction_id_raw):
            # Split by semicolon and clean up each reference
            transaction_references = [ref.strip() for ref in str(transaction_id_raw).split(';') if ref.strip()]
        
        # Check if any of the transaction references were removed
        is_removed = any(ref in removed_transaction_ids for ref in transaction_references)
        
        if is_removed:
            # Use SourceOnlyGroundTruth columns for removed transactions (NO transaction_references)
            transaction = {
                "date": clean_date_string(tx_row.get("SourceOnlyGroundTruth_Transaction Date (value)", None)),
                "amount": convert_to_number(tx_row.get("Source_Originating Amount", None)),
                "currency": treat_null(tx_row.get("Source_Originating Currency", None)),
                "from": {
                    "name": treat_null(tx_row.get("SourceOnlyGroundTruth_Originator Name", None)),
                    "account_number": treat_null(tx_row.get("SourceOnlyGroundTruth_Originator Account Number", None)),
                    "bank": treat_null(tx_row.get("SourceOnlyGroundTruth_Originator Bank Raw", None))
                },
                "to": {
                    "name": treat_null(tx_row.get("Source_Beneficiary Name", None)),
                    "account_number": treat_null(tx_row.get("Source_Beneficiary Account Number", None)),
                    "bank": treat_null(tx_row.get("SourceOnlyGroundTruth_Beneficiary Bank Raw", None))
                },
                "channel": treat_null(tx_row.get("Source_Transaction Channel", None)),
                "can_be_located": False
            }
        else:
            # Use GroundTruth columns for non-removed transactions (WITH transaction_references)
            transaction = {
                "date": clean_date_string(tx_row.get("GroundTruth_Transaction Date (value)", None)),
                "amount": convert_to_number(tx_row.get("GroundTruth_Originating Amount", None)),
                "currency": treat_null(tx_row.get("GroundTruth_Originating Currency", None)),
                "from": {
                    "name": treat_null(tx_row.get("GroundTruth_Originator Name", None)),
                    "account_number": treat_null(tx_row.get("GroundTruth_Originator Account Number", None)),
                    "bank": treat_null(tx_row.get("GroundTruth_Originator Bank Raw", None))
                },
                "to": {
                    "name": treat_null(tx_row.get("GroundTruth_Beneficiary Name", None)),
                    "account_number": treat_null(tx_row.get("GroundTruth_Beneficiary Account Number", None)),
                    "bank": treat_null(tx_row.get("GroundTruth_Beneficiary Bank Raw", None))
                },
                "channel": treat_null(tx_row.get("GroundTruth_Transaction Channel", None)),
                "can_be_located": convert_to_bool(tx_row.get("GroundTruth_Can Be Located", None)),
                "transaction_references": transaction_references
            }
        
        # Add cancel_amount_requested only for UAR type
        if row_type == 'UAR':
            if is_removed:
                transaction["cancel_amount_requested"] = convert_to_number(tx_row.get("Source_Cancel Amount Requested", None))
            else:
                transaction["cancel_amount_requested"] = convert_to_number(tx_row.get("GroundTruth_Cancel Amount Requested", None))
        
        alerted_transactions.append(transaction)
    
    # Build ground truth based on type
    if row_type == 'ADCC' or row_type == 'Police Letter':
        gt_dict = {
            "fraud_type": treat_null(gt_row.get("GroundTruth_Fraud Type", None)),
            "police_reference": treat_null(gt_row.get("GroundTruth_Police Reference", None)),
            "police_team": treat_null(gt_row.get("GroundTruth_Police Team", None)),
            "alerted_transactions": alerted_transactions
        }
    elif row_type in ['HSBC Referral', 'UAR', 'ODFT']:
        gt_dict = {
            "fraud_type": treat_null(gt_row.get("GroundTruth_Fraud Type", None)),
            "alerted_transactions": alerted_transactions
        }
    elif row_type == 'Search Warrant':
        gt_dict = {
            "fraud_type": treat_null(gt_row.get("GroundTruth_Fraud Type", None)),
            "police_reference": treat_null(gt_row.get("GroundTruth_Police Reference", None)),
            "writ_no": treat_null(gt_row.get("GroundTruth_Writ No", None)),
            "contact_person": treat_null(gt_row.get("GroundTruth_Contact Person", None)),
            "police_team": treat_null(gt_row.get("GroundTruth_Police Team", None)),
            "alerted_transactions": alerted_transactions
        }
    else:
        return None
    
    return gt_dict

# --- Load the original CSV file ---
csv_path = 'Dataset_Source_v5.csv'
df = pd.read_csv(csv_path)

# Ensure columns are normalized for matching - use safe conversion
df['Case Number'] = safe_int_convert(df['Case Number'])

# --- Fill 'Input' column ---
input_dir = '../Input Source/'
input_pattern = re.compile(r'Case_(\d+)_.*_Intelligence_(\d+)_.*\.md')
input_map = {}
for root, dirs, files in os.walk(input_dir):
    for file in files:
        match = input_pattern.match(file)
        if match:
            case_num = int(match.group(1))
            intelligence_num = int(match.group(2))
            full_path = os.path.join(root, file)
            input_map[(case_num, intelligence_num)] = full_path

inputs = []
for idx, row in df.iterrows():
    case_num = int(row['Case Number'])
    intelligence_numbers = parse_intelligence_numbers(row['Intelligence Number'])
    found = False
    for int_num in intelligence_numbers:
        key = (case_num, int_num)
        if key in input_map:
            print(f"Found input file for Case Number {key[0]}, Intelligence Number {key[1]}: {input_map[key]}")
            try:
                with open(input_map[key], 'r', encoding='utf-8') as f:
                    content = f.read()
                inputs.append(content)
                found = True
                break
            except Exception as e:
                print(f"Error reading input file for Case Number {key[0]}, Intelligence Number {key[1]}: {e}")
    if not found:
        print(f"No input file found for Case Number {case_num}, Intelligence Number(s) {intelligence_numbers}")
        inputs.append(None)
df['Input'] = inputs

# --- Fill 'Transactions' column ---
transaction_dir = '../Input Data/Transaction Records'
transaction_pattern = re.compile(r'Case_(\d+)_.*records\.csv')
transaction_map = {}
for root, dirs, files in os.walk(transaction_dir):
    for file in files:
        match = transaction_pattern.match(file)
        if match:
            case_num = int(match.group(1))
            full_path = os.path.join(root, file)
            transaction_map[case_num] = full_path

transactions = []
for idx, row in df.iterrows():
    case_num = int(row['Case Number'])
    if case_num in transaction_map:
        print(f"Found transaction file for Case Number {case_num}: {transaction_map[case_num]}")
        try:
            with open(transaction_map[case_num], 'r', encoding='utf-8') as f:
                content = f.read()
            # Remove the last Fraud Payment column
            cleaned_content = remove_last_fraud_payment_column(content)
            transactions.append(cleaned_content)
        except Exception as e:
            print(f"Error reading transaction file for Case Number {case_num}: {e}")
            transactions.append(None)
    else:
        print(f"No transaction file found for Case Number {case_num}")
        transactions.append(None)
df['Transactions'] = transactions

# --- Fill 'Instruction' column ---
instruction_dir = 'instruction'
instruction_types = df['Type'].unique()
instruction_map = {}
for t in instruction_types:
    instruction_file = os.path.join(instruction_dir, f'{t} instruction.txt')
    if os.path.exists(instruction_file):
        try:
            with open(instruction_file, 'r', encoding='utf-8') as f:
                content = f.read()
            instruction_map[t] = content
            print(f"Loaded instruction for type {t} from {instruction_file}")
        except Exception as e:
            print(f"Error reading instruction file for type {t}: {e}")
            instruction_map[t] = None
    else:
        print(f"Instruction file not found for type {t}: {instruction_file}")
        instruction_map[t] = None

instructions = []
for idx, row in df.iterrows():
    t = row['Type']
    instructions.append(instruction_map.get(t, None))
df['Instruction'] = instructions

# --- Fill 'Ground Truth' column for different types ---
ground_truth_path = '../Input Data Summary/OtherFields_From_IR_and_Source.xlsx'
transaction_gt_path = '../Input Data Summary/Transaction_From_IR_and_Source.xlsx'

# Check if files exist before trying to read them
if not os.path.exists(ground_truth_path):
    print(f"Warning: Ground truth file not found: {ground_truth_path}")
    print("Skipping Ground Truth column...")
    df['Ground Truth'] = None
else:
    gt_df = pd.read_excel(ground_truth_path, dtype=str)
    
    # Safe conversion for ground truth data
    gt_df['Case Number'] = safe_int_convert(gt_df['Case Number'])
    
    # Load transaction ground truth data from all sheets
    if not os.path.exists(transaction_gt_path):
        print(f"Warning: Transaction ground truth file not found: {transaction_gt_path}")
        transaction_gt_df = pd.DataFrame()
    else:
        all_sheets = pd.read_excel(transaction_gt_path, sheet_name=None, dtype=str)
        transaction_gt_df = pd.concat(all_sheets.values(), ignore_index=True)
        
        # Clean up the data
        # First apply treat_null to all columns
        transaction_gt_df = transaction_gt_df.applymap(treat_null)
        
        # Convert TRUE/FALSE to boolean for can_be_located field
        if 'GroundTruth_Can Be Located' in transaction_gt_df.columns:
            transaction_gt_df['GroundTruth_Can Be Located'] = transaction_gt_df['GroundTruth_Can Be Located'].apply(convert_to_bool)
        
        # Filter rows where GroundTruth_Fraud Payment is not null
        if 'GroundTruth_Fraud Payment' in transaction_gt_df.columns:
            transaction_gt_df = transaction_gt_df[transaction_gt_df['GroundTruth_Fraud Payment'].notnull()]
        
        # Safe conversion for transaction ground truth
        if not transaction_gt_df.empty:
            transaction_gt_df['Case Number'] = safe_int_convert(transaction_gt_df['Case Number'])

    # Build lookups for ground truth
    gt_lookup = {}
    for idx, row in gt_df.iterrows():
        case_num = int(row['Case Number'])
        intelligence_numbers = parse_intelligence_numbers(row['Intelligence Number'])
        for int_num in intelligence_numbers:
            key = (case_num, int_num)
            gt_lookup[key] = row

    # Build lookup for transaction ground truth - allows multiple transactions per key
    transaction_gt_lookup = {}
    if not transaction_gt_df.empty:
        for idx, row in transaction_gt_df.iterrows():
            case_num = int(row['Case Number'])
            intelligence_numbers = parse_intelligence_numbers(row['Intelligence Number'])
            for int_num in intelligence_numbers:
                key = (case_num, int_num)
                if key not in transaction_gt_lookup:
                    transaction_gt_lookup[key] = []
                transaction_gt_lookup[key].append(row)

    ground_truths = []
    for idx, row in df.iterrows():
        case_num = int(row['Case Number'])
        intelligence_numbers = parse_intelligence_numbers(row['Intelligence Number'])
        gt_row = None
        transaction_rows = []
        
        # Find ground truth data
        for int_num in intelligence_numbers:
            key = (case_num, int_num)
            if key in gt_lookup:
                gt_row = gt_lookup[key]
            if key in transaction_gt_lookup:
                transaction_rows.extend(transaction_gt_lookup[key])
            if gt_row is not None and transaction_rows:
                break
        
        if gt_row is not None:
            row_type = row['Type']
            
            # Build alerted_transactions array - can contain multiple transactions
            alerted_transactions = []
            for tx_row in transaction_rows:
                # Get transaction references from Transaction ID column and split by semicolon
                transaction_id_raw = tx_row.get("Transaction ID", None)
                transaction_references = []
                if transaction_id_raw and pd.notna(transaction_id_raw):
                    # Split by semicolon and clean up each reference
                    transaction_references = [ref.strip() for ref in str(transaction_id_raw).split(';') if ref.strip()]
                
                # Base transaction structure
                transaction = {
                    "date": clean_date_string(tx_row.get("GroundTruth_Transaction Date (value)", None)),
                    "amount": convert_to_number(tx_row.get("GroundTruth_Originating Amount", None)),
                    "currency": treat_null(tx_row.get("GroundTruth_Originating Currency", None)),
                    "from": {
                        "name": treat_null(tx_row.get("GroundTruth_Originator Name", None)),
                        "account_number": treat_null(tx_row.get("GroundTruth_Originator Account Number", None)),
                        "bank": treat_null(tx_row.get("GroundTruth_Originator Bank Raw", None))
                    },
                    "to": {
                        "name": treat_null(tx_row.get("GroundTruth_Beneficiary Name", None)),
                        "account_number": treat_null(tx_row.get("GroundTruth_Beneficiary Account Number", None)),
                        "bank": treat_null(tx_row.get("GroundTruth_Beneficiary Bank Raw", None))
                    },
                    "channel": treat_null(tx_row.get("GroundTruth_Transaction Channel", None)),
                    "can_be_located": convert_to_bool(tx_row.get("GroundTruth_Can Be Located", None)),
                    "transaction_references": transaction_references
                }
                
                # Add cancel_amount_requested only for UAR type
                if row_type == 'UAR':
                    transaction["cancel_amount_requested"] = convert_to_number(tx_row.get("GroundTruth_Cancel Amount Requested", None))
                
                alerted_transactions.append(transaction)
            
            # Build ground truth based on type
            if row_type == 'ADCC' or row_type == 'Police Letter':
                gt_dict = {
                    "fraud_type": treat_null(gt_row.get("GroundTruth_Fraud Type", None)),
                    "police_reference": treat_null(gt_row.get("GroundTruth_Police Reference", None)),
                    "police_team": treat_null(gt_row.get("GroundTruth_Police Team", None)),
                    "alerted_transactions": alerted_transactions
                }
            elif row_type in ['HSBC Referral', 'UAR', 'ODFT']:
                gt_dict = {
                    "fraud_type": treat_null(gt_row.get("GroundTruth_Fraud Type", None)),
                    "alerted_transactions": alerted_transactions
                }
            elif row_type == 'Search Warrant':
                gt_dict = {
                    "fraud_type": treat_null(gt_row.get("GroundTruth_Fraud Type", None)),
                    "police_reference": treat_null(gt_row.get("GroundTruth_Police Reference", None)),
                    "writ_no": treat_null(gt_row.get("GroundTruth_Writ No", None)),
                    "contact_person": treat_null(gt_row.get("GroundTruth_Contact Person", None)),
                    "police_team": treat_null(gt_row.get("GroundTruth_Police Team", None)),
                    "alerted_transactions": alerted_transactions
                }
            else:
                gt_dict = None
            
            if gt_dict:
                ground_truths.append(json.dumps(gt_dict, ensure_ascii=False, indent=2))
                print(f"Ground Truth for Case {case_num}, Intelligence {intelligence_numbers}, Type {row_type}: Found {len(alerted_transactions)} transactions")
            else:
                ground_truths.append(None)
        else:
            ground_truths.append(None)
            print(f"No Ground Truth found for Case {case_num}, Intelligence {intelligence_numbers}")

    df['Ground Truth'] = ground_truths

# Add Original Case Number and Set Number columns to original data
df.insert(df.columns.get_loc('Case Number') + 1, 'Original Case Number', df['Case Number'])
df['Set Number'] = 1

# --- Create all 5 sets of data ---
print("Creating all 5 sets of data...")

all_dataframes = []

# Set 1: Original data (Case Numbers 1-50)
print("Set 1: Original data")
set1_df = df.copy()
set1_df['Set Number'] = 1
all_dataframes.append(set1_df)

# Set 2: Empty transactions with Source_ columns (Case Numbers 51-100)
print("Set 2: Empty transactions with Source_ columns")
set2_df = df.copy()
set2_df['Case Number'] = set2_df['Case Number'] + 50
set2_df['Set Number'] = 2
set2_df['Transactions'] = None

# Process Ground Truth column for Source_ prefixed columns (without can_be_located and transaction_references)
source_ground_truths = []
for idx, row in set2_df.iterrows():
    case_num = int(row['Original Case Number'])  # Use original case number for lookup
    intelligence_numbers = parse_intelligence_numbers(row['Intelligence Number'])
    gt_row = None
    transaction_rows = []
    
    # Find ground truth data
    for int_num in intelligence_numbers:
        key = (case_num, int_num)
        if key in gt_lookup:
            gt_row = gt_lookup[key]
        if key in transaction_gt_lookup:
            transaction_rows.extend(transaction_gt_lookup[key])
        if gt_row is not None and transaction_rows:
            break
    
    if gt_row is not None:
        row_type = row['Type']
        
        # Build alerted_transactions array using Source_ columns (simplified)
        alerted_transactions = []
        for tx_row in transaction_rows:
            # Base transaction structure with Source_ columns (no can_be_located or transaction_references)
            transaction = {
                "date": clean_date_string(tx_row.get("SourceOnlyGroundTruth_Transaction Date (value)", None)),
                "amount": convert_to_number(tx_row.get("Source_Originating Amount", None)),
                "currency": treat_null(tx_row.get("Source_Originating Currency", None)),
                "from": {
                    "name": treat_null(tx_row.get("SourceOnlyGroundTruth_Originator Name", None)),
                    "account_number": treat_null(tx_row.get("SourceOnlyGroundTruth_Originator Account Number", None)),
                    "bank": treat_null(tx_row.get("SourceOnlyGroundTruth_Originator Bank Raw", None))
                },
                "to": {
                    "name": treat_null(tx_row.get("Source_Beneficiary Name", None)),
                    "account_number": treat_null(tx_row.get("Source_Beneficiary Account Number", None)),
                    "bank": treat_null(tx_row.get("SourceOnlyGroundTruth_Beneficiary Bank Raw", None))
                },
                "channel": treat_null(tx_row.get("Source_Transaction Channel", None))
            }
            
            # Add cancel_amount_requested only for UAR type
            if row_type == 'UAR':
                transaction["cancel_amount_requested"] = convert_to_number(tx_row.get("Source_Cancel Amount Requested", None))
            
            alerted_transactions.append(transaction)
        
        # Build ground truth based on type using Source_ columns
        if row_type == 'ADCC' or row_type == 'Police Letter':
            gt_dict = {
                "fraud_type": treat_null(gt_row.get("Source_Fraud Type", None)),
                "police_reference": treat_null(gt_row.get("Source_Police Reference", None)),
                "police_team": treat_null(gt_row.get("Source_Police Team", None)),
                "alerted_transactions": alerted_transactions
            }
        elif row_type in ['HSBC Referral', 'UAR', 'ODFT']:
            gt_dict = {
                "fraud_type": treat_null(gt_row.get("Source_Fraud Type", None)),
                "alerted_transactions": alerted_transactions
            }
        elif row_type == 'Search Warrant':
            gt_dict = {
                "fraud_type": treat_null(gt_row.get("Source_Fraud Type", None)),
                "police_reference": treat_null(gt_row.get("Source_Police Reference", None)),
                "writ_no": treat_null(gt_row.get("Source_Writ No", None)),
                "contact_person": treat_null(gt_row.get("Source_Contact Person", None)),
                "police_team": treat_null(gt_row.get("Source_Police Team", None)),
                "alerted_transactions": alerted_transactions
            }
        else:
            gt_dict = None
        
        if gt_dict:
            source_ground_truths.append(json.dumps(gt_dict, ensure_ascii=False, indent=2))
        else:
            source_ground_truths.append(None)
    else:
        source_ground_truths.append(None)

set2_df['Ground Truth'] = source_ground_truths
all_dataframes.append(set2_df)

# Sets 3, 4, 5: Different degrees of transaction removal (Case Numbers 101-150, 151-200, 201-250)
removal_probabilities = [0.2, 0.5, 0.8]  # Updated removal probabilities

for set_num in range(3, 6):
    print(f"Set {set_num}: {int(removal_probabilities[set_num-3]*100)}% transaction removal")
    
    # Create a copy of the original DataFrame
    modified_df = df.copy()
    modified_df['Case Number'] = modified_df['Case Number'] + (set_num - 1) * 50
    modified_df['Set Number'] = set_num
    
    # Store removed transaction IDs for each row
    removed_transactions_per_row = []
    
    # Modify transactions and store removed IDs
    modified_transactions = []
    for idx, row in modified_df.iterrows():
        original_transactions = row['Transactions']
        modified_content, removed_ids = randomly_remove_transactions(original_transactions, removal_probabilities[set_num-3])
        modified_transactions.append(modified_content)
        removed_transactions_per_row.append(removed_ids)
    
    modified_df['Transactions'] = modified_transactions
    
    # Build modified ground truth
    modified_ground_truths = []
    for idx, row in modified_df.iterrows():
        case_num = int(row['Original Case Number'])  # Use original case number for lookup
        intelligence_numbers = parse_intelligence_numbers(row['Intelligence Number'])
        gt_row = None
        transaction_rows = []
        removed_ids = removed_transactions_per_row[idx]
        
        # Find ground truth data
        for int_num in intelligence_numbers:
            key = (case_num, int_num)
            if key in gt_lookup:
                gt_row = gt_lookup[key]
            if key in transaction_gt_lookup:
                transaction_rows.extend(transaction_gt_lookup[key])
            if gt_row is not None and transaction_rows:
                break
        
        if gt_row is not None:
            row_type = row['Type']
            gt_dict = build_ground_truth_with_removed_transactions(gt_row, transaction_rows, row_type, removed_ids)
            
            if gt_dict:
                modified_ground_truths.append(json.dumps(gt_dict, ensure_ascii=False, indent=2))
            else:
                modified_ground_truths.append(None)
        else:
            modified_ground_truths.append(None)
    
    modified_df['Ground Truth'] = modified_ground_truths
    all_dataframes.append(modified_df)

# Combine all dataframes
final_df = pd.concat(all_dataframes, ignore_index=True)

# --- Save to a new CSV file ---
output_csv_path = 'Dataset_Source_v5_updated_with_groundtruth.csv'
final_df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')

# --- Save original set separately ---
# Filter original set (Set Number == 1)
set1_df = final_df[final_df['Set Number'] == 1].copy()
# Save to CSV
output_original_set_csv_path = 'Dataset_Source_v5_original_set.csv'
set1_df.to_csv(output_original_set_csv_path, index=False, encoding='utf-8-sig')
print(f'Original set (Set 1) saved to {output_original_set_csv_path}')
print(f'Original set contains {len(set1_df)} rows (Case Numbers 1-50)')

print(f'Updated data with all 5 sets saved to {output_csv_path}')
print(f'Total sets: 5')
print(f'Total rows: {len(final_df)}')
print(f'Breakdown:')
print(f'  - Set 1 (Original): {len(set1_df)} rows, Case Numbers 1-50')
print(f'  - Set 2 (Empty transactions): {len(set2_df)} rows, Case Numbers 51-100')
print(f'  - Set 3 (20% removal): {len(all_dataframes[2])} rows, Case Numbers 101-150')
print(f'  - Set 4 (50% removal): {len(all_dataframes[3])} rows, Case Numbers 151-200')
print(f'  - Set 5 (80% removal): {len(all_dataframes[4])} rows, Case Numbers 201-250')

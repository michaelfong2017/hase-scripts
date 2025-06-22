import pathlib
import pandas as pd
import re
import difflib

def trim_dataframe(df):
    """Trim leading and trailing spaces from every cell in the DataFrame."""
    return df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

def find_fraud_payment_column(columns):
    """Find the closest matching column name to 'Fraud Payment'."""
    target = 'Fraud Payment'
    matches = difflib.get_close_matches(target, columns, n=1, cutoff=0.6)
    if matches:
        return matches[0]
    for col in columns:
        if col.replace('_', ' ').replace(' ', '').lower() == target.replace(' ', '').lower():
            return col
    return None

def combine_case_transactions():
    input_dir = pathlib.Path('Raw Transaction Records')
    output_dir = pathlib.Path('Transaction Records')
    output_dir.mkdir(exist_ok=True)
    
    case_file_pattern = re.compile(r'Case_(\d+)_.*_transaction_record\.csv')
    case_files = {}
    for file in input_dir.glob('Case_*_*_transaction_record.csv'):
        match = case_file_pattern.match(file.name)
        if match:
            case_num = match.group(1)
            case_files.setdefault(case_num, []).append(file)

    removal_log = []
    before_count = 0
    emptied_counterparty_log = []

    for case_num, files in case_files.items():
        dfs = []
        fraud_col_used = None
        for file in files:
            df = pd.read_csv(file, dtype=str)
            df = trim_dataframe(df)
            file_lower = file.name.lower()
            is_suspect = 'suspect' in file_lower and 'victim' not in file_lower

            cell_occurrences = []
            rows_to_clear = set()
            for col in df.columns:
                mask = df[col].astype(str).str.upper().str.contains("COUNTERPARTY_NOT_STATED")
                for idx in df[mask].index:
                    cell_value = df.at[idx, col]
                    before_count += 1
                    cell_occurrences.append({
                        "File": file.name,
                        "Column": col,
                        "Row": idx + 2,
                        "OriginalValue": cell_value,
                        "RowIdx": idx
                    })
                    if is_suspect:
                        rows_to_clear.add(idx)

            if is_suspect and rows_to_clear:
                cols_to_clear = ['Counterparty Name', 'Counterparty ID', 'Originator Account Number']
                for idx in rows_to_clear:
                    for col_name in cols_to_clear:
                        if col_name in df.columns:
                            original_val = df.at[idx, col_name]
                            if original_val is not None and str(original_val).strip() != '':
                                emptied_counterparty_log.append({
                                    'File': file.name,
                                    'Row': idx + 2,
                                    'Column': col_name,
                                    'OriginalValue': str(original_val)
                                })
                            df.at[idx, col_name] = ''

            for occ in cell_occurrences:
                if is_suspect:
                    removal_log.append({
                        "File": occ["File"],
                        "Column": occ["Column"],
                        "Row": occ["Row"],
                        "OriginalValue": occ["OriginalValue"]
                    })

            fraud_col = find_fraud_payment_column(df.columns)
            if not fraud_col:
                continue
            fraud_col_used = fraud_col
            dfs.append(df)
        
        if dfs and fraud_col_used:
            combined_df = pd.concat(dfs, ignore_index=True)
            def extract_first_number(value):
                if pd.isna(value):
                    return float('inf')
                match = re.match(r'\s*(\d+)', str(value))
                if match:
                    return int(match.group(1))
                else:
                    return float('inf')
            combined_df['SortKey'] = combined_df[fraud_col_used].apply(extract_first_number)
            combined_df = combined_df.sort_values(by='SortKey').drop(columns=['SortKey'])
            output_file = output_dir / f"Case_{case_num}_transaction_records.csv"
            combined_df.to_csv(output_file, index=False)

    print(f"Total cells containing 'COUNTERPARTY_NOT_STATED': {before_count}")
    print(f"Total suspect transaction cells cleared: {len(removal_log)}")
    if removal_log:
        print("\nDetails of cleared suspect transaction cells:")
        for info in removal_log:
            print(f"File: {info['File']}, Column: {info['Column']}, Row: {info['Row']}, "
                  f"Original: {info['OriginalValue']}")
    else:
        print("No suspect transaction cells required clearing.")

    if emptied_counterparty_log:
        emptied_log_df = pd.DataFrame(emptied_counterparty_log)
        emptied_log_df.to_csv('emptied_counterparty_log.csv', index=False)
        print(f"Emptied COUNTERPARTY log saved to: {pathlib.Path('emptied_counterparty_log.csv').resolve()}")
    else:
        print("No COUNTERPARTY_NOT_STATED cells were emptied.")

def process_transaction_columns():
    """Process each case file to remove and add columns as specified."""
    input_dir = pathlib.Path('Transaction Records')
    case_files = list(input_dir.glob('Case_*_transaction_records.csv'))

    ordered_cols = [
        'Transaction Date (value)', 'Originating Currency',
        'Originating Amount', 'Debit Credit Indicator', 'Beneficiary Bank Raw', 'Originator Bank Raw',
        'Originator Account Number', 'Beneficiary Account Number',
        'Originator Name', 'Beneficiary Name',
        'Subject Type',
        'Transaction Type Source', 'Transaction Code Description',
        'Sending Bank Account Number', 'Sending Bank Address', 'Converted Amount', 'Fraud Payment'
    ]

    transaction_logs = []
    conflict_logs = []

    for case_file in case_files:
        df = pd.read_csv(case_file, dtype=str)
        df = trim_dataframe(df)
        
        df['Originator Name'] = ''
        df['Beneficiary Account Number'] = ''
        df['Subject Type'] = ''
        
        for idx, row in df.iterrows():
            transaction_log = {
                'File': case_file.name,
                'Row': idx + 2,
                'Fraud_Payment': row.get('Fraud Payment', ''),
                'Debit_Credit_Indicator': row.get('Debit Credit Indicator', ''),
                'Dropped_Account_ID': '',
                'Dropped_Counterparty_Name': '',
                'Dropped_Counterparty_ID': '',
                'Added_Originator_Name': '',
                'Added_Beneficiary_Account_Number': '',
                'Added_Subject_Type': '',
                'Preservation_Actions': '',
                'Conflicts_Resolved': ''
            }
            
            account_id = row.get('Account ID', '')
            originator_account_number = row.get('Originator Account Number', '')
            counterparty_id = row.get('Counterparty ID', '')
            counterparty_name = row.get('Counterparty Name', '')
            beneficiary_name = row.get('Beneficiary Name', '')
            debit_credit_indicator = row.get('Debit Credit Indicator', '').upper().strip()
            
            transaction_log['Dropped_Account_ID'] = account_id
            transaction_log['Dropped_Counterparty_Name'] = counterparty_name
            transaction_log['Dropped_Counterparty_ID'] = counterparty_id
            
            preservation_actions = []
            conflicts_resolved = []
            
            if debit_credit_indicator == 'C':
                # Beneficiary logic
                subject_type_value = 'Beneficiary'
                originator_name_value = counterparty_name if counterparty_name else ''
                beneficiary_account_value = account_id if account_id else ''
                
                # Check if counterparty_id should be preserved in originator_account_number
                if counterparty_id and str(counterparty_id).strip():
                    if not originator_account_number or str(originator_account_number).strip() == '':
                        # Empty - preserve counterparty_id
                        df.at[idx, 'Originator Account Number'] = counterparty_id
                        preservation_actions.append(f"Preserved Counterparty ID '{counterparty_id}' in empty Originator Account Number")
                    elif str(originator_account_number).strip() != str(counterparty_id).strip():
                        # Conflict - trust dropped column
                        conflict_logs.append({
                            'File': case_file.name,
                            'Row': idx + 2,
                            'Conflict_Type': 'Originator Account Number vs Counterparty ID',
                            'Original_Value': originator_account_number,
                            'Dropped_Value': counterparty_id,
                            'Action': 'Replaced with dropped value'
                        })
                        df.at[idx, 'Originator Account Number'] = counterparty_id
                        conflicts_resolved.append(f"Replaced Originator Account Number '{originator_account_number}' with Counterparty ID '{counterparty_id}'")
                
                df.at[idx, 'Originator Name'] = originator_name_value
                df.at[idx, 'Beneficiary Account Number'] = beneficiary_account_value
                df.at[idx, 'Subject Type'] = subject_type_value
                
                transaction_log['Added_Originator_Name'] = originator_name_value
                transaction_log['Added_Beneficiary_Account_Number'] = beneficiary_account_value
                transaction_log['Added_Subject_Type'] = subject_type_value
                
            else:
                # Originator logic
                subject_type_value = 'Originator'
                beneficiary_account_value = counterparty_id if counterparty_id else ''
                originator_name_value = ''
                
                # Check if account_id should be preserved in originator_account_number
                if account_id and str(account_id).strip():
                    if not originator_account_number or str(originator_account_number).strip() == '':
                        # Empty - preserve account_id
                        df.at[idx, 'Originator Account Number'] = account_id
                        preservation_actions.append(f"Preserved Account ID '{account_id}' in empty Originator Account Number")
                    elif str(originator_account_number).strip() != str(account_id).strip():
                        # Conflict - trust dropped column
                        conflict_logs.append({
                            'File': case_file.name,
                            'Row': idx + 2,
                            'Conflict_Type': 'Originator Account Number vs Account ID',
                            'Original_Value': originator_account_number,
                            'Dropped_Value': account_id,
                            'Action': 'Replaced with dropped value'
                        })
                        df.at[idx, 'Originator Account Number'] = account_id
                        conflicts_resolved.append(f"Replaced Originator Account Number '{originator_account_number}' with Account ID '{account_id}'")
                
                # Check if counterparty_name should be preserved in beneficiary_name
                if counterparty_name and str(counterparty_name).strip():
                    if not beneficiary_name or str(beneficiary_name).strip() == '':
                        # Empty - preserve counterparty_name
                        df.at[idx, 'Beneficiary Name'] = counterparty_name
                        preservation_actions.append(f"Preserved Counterparty Name '{counterparty_name}' in empty Beneficiary Name")
                    elif str(beneficiary_name).strip() != str(counterparty_name).strip():
                        # Conflict - trust dropped column
                        conflict_logs.append({
                            'File': case_file.name,
                            'Row': idx + 2,
                            'Conflict_Type': 'Beneficiary Name vs Counterparty Name',
                            'Original_Value': beneficiary_name,
                            'Dropped_Value': counterparty_name,
                            'Action': 'Replaced with dropped value'
                        })
                        df.at[idx, 'Beneficiary Name'] = counterparty_name
                        conflicts_resolved.append(f"Replaced Beneficiary Name '{beneficiary_name}' with Counterparty Name '{counterparty_name}'")
                
                df.at[idx, 'Beneficiary Account Number'] = beneficiary_account_value
                df.at[idx, 'Originator Name'] = originator_name_value
                df.at[idx, 'Subject Type'] = subject_type_value
                
                transaction_log['Added_Originator_Name'] = originator_name_value
                transaction_log['Added_Beneficiary_Account_Number'] = beneficiary_account_value
                transaction_log['Added_Subject_Type'] = subject_type_value
            
            transaction_log['Preservation_Actions'] = '; '.join(preservation_actions) if preservation_actions else ''
            transaction_log['Conflicts_Resolved'] = '; '.join(conflicts_resolved) if conflicts_resolved else ''
            transaction_logs.append(transaction_log)

        df = df.drop(columns=['Account ID', 'Counterparty Name', 'Counterparty ID'], errors='ignore')

        final_cols = [col for col in ordered_cols if col in df.columns]
        remaining_cols = [col for col in df.columns if col not in final_cols]
        final_cols.extend(remaining_cols)
        df = df[final_cols]

        fraud_col = find_fraud_payment_column(df.columns)
        if fraud_col:
            def extract_first_number(value):
                if pd.isna(value):
                    return float('inf')
                match = re.match(r'\s*(\d+)', str(value))
                if match:
                    return int(match.group(1))
                else:
                    return float('inf')
            df['SortKey'] = df[fraud_col].apply(extract_first_number)
            df = df.sort_values(by='SortKey').drop(columns=['SortKey'])

        df.to_csv(case_file, index=False)

    # Combine transaction logs and conflict logs
    all_logs = transaction_logs.copy()
    for conflict in conflict_logs:
        all_logs.append({
            'File': conflict['File'],
            'Row': conflict['Row'],
            'Fraud_Payment': '',
            'Debit_Credit_Indicator': '',
            'Dropped_Account_ID': '',
            'Dropped_Counterparty_Name': '',
            'Dropped_Counterparty_ID': '',
            'Added_Originator_Name': '',
            'Added_Beneficiary_Account_Number': '',
            'Added_Subject_Type': '',
            'Preservation_Actions': '',
            'Conflicts_Resolved': '',
            'Conflict_Type': conflict['Conflict_Type'],
            'Original_Value': conflict['Original_Value'],
            'Dropped_Value': conflict['Dropped_Value'],
            'Action': conflict['Action']
        })

    if all_logs:
        logs_df = pd.DataFrame(all_logs)
        logs_df.to_csv('transaction_transformation_log.csv', index=False)
        print(f"Transaction transformation log saved to: {pathlib.Path('transaction_transformation_log.csv').resolve()}")
        print(f"Total transactions logged: {len(transaction_logs)}")
        if conflict_logs:
            print(f"Total conflicts resolved: {len(conflict_logs)}")
            print("\nConflict Summary:")
            for conflict in conflict_logs:
                print(f"  {conflict['File']} Row {conflict['Row']}: {conflict['Conflict_Type']}")
        else:
            print("No conflicts detected.")

if __name__ == "__main__":
    combine_case_transactions()
    process_transaction_columns()

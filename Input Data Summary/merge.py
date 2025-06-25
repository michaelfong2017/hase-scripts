import pandas as pd

# Load the CSV files WITHOUT converting 'null' strings to NaN
try:
    transaction_ir_source = pd.read_csv('Transaction_From_IR_only.csv', keep_default_na=False, na_values=[''])
    transaction_csv = pd.read_csv('Transaction_From_CSV.csv', keep_default_na=False, na_values=[''])
    
    print("Files loaded successfully!")
    print(f"Transaction_From_IR_only.csv shape: {transaction_ir_source.shape}")
    print(f"Transaction_From_CSV.csv shape: {transaction_csv.shape}")
    
except FileNotFoundError as e:
    print(f"Error: {e}")
    exit()

# Fill only truly empty cells with "null"
transaction_csv = transaction_csv.fillna("null")

# Handle conversions safely
def safe_payment_convert(x):
    if pd.isna(x) or x == '' or x == ' ':
        return '0'
    elif str(x).lower() == 'null':
        return 'null'
    else:
        try:
            return str(int(float(x)))
        except:
            return str(x)

def safe_case_convert(x):
    if pd.isna(x) or x == '':
        return ''
    else:
        return str(x)

# Create matching keys
transaction_ir_source['matching_key'] = (
    transaction_ir_source['Case Number'].apply(safe_case_convert) + '|' + 
    transaction_ir_source['IR_Fraud Payment'].apply(safe_payment_convert)
)

transaction_csv['matching_key'] = (
    transaction_csv['Case Number'].apply(safe_case_convert) + '|' + 
    transaction_csv['Fraud Payment'].astype(str)
)

print(f"IR matching keys sample: {transaction_ir_source['matching_key'].head(3).tolist()}")
print(f"CSV matching keys sample: {transaction_csv['matching_key'].head(3).tolist()}")

# Check for duplicates in CSV that could cause row multiplication
csv_duplicates = transaction_csv['matching_key'].duplicated().sum()
print(f"Duplicate keys in CSV: {csv_duplicates}")

if csv_duplicates > 0:
    print("Removing duplicates from CSV to prevent row multiplication...")
    transaction_csv = transaction_csv.drop_duplicates(subset=['matching_key'], keep='first')
    print(f"CSV rows after deduplication: {len(transaction_csv)}")

# Create result data - start with original IR data
result_data = transaction_ir_source.copy()

# Get all columns from CSV (excluding matching key)
csv_columns = [col for col in transaction_csv.columns if col != 'matching_key']
print(f"Columns to append from CSV: {csv_columns}")

# TASK 1: Append columns from CSV where matches exist
print("\nTask 1: Appending columns from CSV...")
csv_dict = transaction_csv.set_index('matching_key').to_dict('index')

matches_found = 0
for idx, row in result_data.iterrows():
    key = row['matching_key']
    if key in csv_dict:
        matches_found += 1
        csv_row = csv_dict[key]
        
        # Add all CSV columns to this row
        for col in csv_columns:
            if col in csv_row:
                # Add suffix if column already exists
                new_col_name = f"{col}_from_csv" if col in result_data.columns else col
                result_data.at[idx, new_col_name] = csv_row[col]

print(f"Task 1 complete: {matches_found} rows updated with CSV data")

# TASK 2: Copy values between rows with same [Case Number, IR_Fraud Payment]
print("\nTask 2: Copying values between rows with same key...")
grouped = result_data.groupby('matching_key')
internal_updates = 0

for key, group in grouped:
    if len(group) > 1:
        # Get the row with the most non-null values as source
        non_null_counts = group.count(axis=1)
        source_idx = non_null_counts.idxmax()
        source_row = result_data.loc[source_idx]
        
        # Copy to all other rows in the group
        for idx in group.index:
            if idx != source_idx:
                for col in result_data.columns:
                    if col != 'matching_key' and pd.isna(result_data.at[idx, col]) and pd.notna(source_row[col]):
                        result_data.at[idx, col] = source_row[col]
                internal_updates += 1

print(f"Task 2 complete: {internal_updates} rows updated internally")

# Clean up temporary column
result_data = result_data.drop(columns=['matching_key'], errors='ignore')

# Final verification
print(f"\nFinal verification:")
print(f"Original IR rows: {len(transaction_ir_source)}")
print(f"Final result rows: {len(result_data)}")
print(f"Row count preserved: {len(result_data) == len(transaction_ir_source)}")

# Save result
output_filename = 'Transaction_From_IR_only_Updated.csv'
result_data.to_csv(output_filename, index=False)

print(f"\nFinal data saved to: {output_filename}")
print(f"External matches: {matches_found}")
print(f"Internal updates: {internal_updates}")

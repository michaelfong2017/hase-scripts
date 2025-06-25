import glob
import pandas as pd

# Read all files matching the pattern
file_pattern = '../Input Data/Transaction Records/Case_*'
file_list = glob.glob(file_pattern)

case_data = []

for file_path in file_list:
    # Fix case number extraction - need to get the second part after splitting
    case_number = file_path.split('Case_')[1].split('_')[0]
    
    # Read the file
    df = pd.read_csv(file_path)
    
    # Strip whitespace from column names
    df.columns = df.columns.str.strip()
    
    # Add each record with case number and all requested columns
    for index, row in df.iterrows():
        case_data.append({
            'Case Number': case_number,
            'Fraud Payment': row['Fraud Payment'],
            'Located': True,
            'Transaction Date (value)': row.get('Transaction Date (value)', None),
            'Originating Amount': row.get('Originating Amount', None),
            'Originating Currency': row.get('Originating Currency', None),
            'Originator Name': row.get('Originator Name', None),
            'Originator Account Number': row.get('Originator Account Number', None),
            'Originator Bank Raw': row.get('Originator Bank Raw', None),
            'Beneficiary Name': row.get('Beneficiary Name', None),
            'Beneficiary Account Number': row.get('Beneficiary Account Number', None),
            'Beneficiary Bank Raw': row.get('Beneficiary Bank Raw', None),
            'Transaction Type Source': row.get('Transaction Type Source', None),
            'Transaction Code Description': row.get('Transaction Code Description', None)
        })

# Create DataFrame
fraud_df = pd.DataFrame(case_data)

# Convert Case Number to numeric for proper sorting
fraud_df['Case Number'] = pd.to_numeric(fraud_df['Case Number'], errors='coerce')

# Sort by Case Number first, then by Fraud Payment
fraud_df = fraud_df.sort_values(by=['Case Number', 'Fraud Payment'])

# Save to CSV
fraud_df.to_csv('output_case_fraud_payments.csv', index=False)

print(f"Done! {len(fraud_df)} records exported")
print(fraud_df.head())

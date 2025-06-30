import pandas as pd
import os
import re

# Load the original CSV file
csv_path = 'Dataset_Source_v5.csv'
df = pd.read_csv(csv_path)

# Clean up columns for robust matching
df['Case Number'] = df['Case Number'].astype(str).str.strip().astype(int)
df['Intelligence Number'] = df['Intelligence Number'].astype(str).str.strip().astype(int)

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
    key = (int(row['Case Number']), int(row['Intelligence Number']))
    if key in input_map:
        print(f"Found input file for Case Number {key[0]}, Intelligence Number {key[1]}: {input_map[key]}")
        try:
            with open(input_map[key], 'r', encoding='utf-8') as f:
                content = f.read()
            inputs.append(content)
        except Exception as e:
            print(f"Error reading input file for Case Number {key[0]}, Intelligence Number {key[1]}: {e}")
            inputs.append(None)
    else:
        print(f"No input file found for Case Number {key[0]}, Intelligence Number {key[1]}")
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
            transactions.append(content)
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

# Save to a new CSV file
output_csv_path = 'Dataset_Source_v5_updated_with_instructions.csv'
df.to_csv(output_csv_path, index=False)
print(f'Updated data with Input, Transactions, and Instruction saved to {output_csv_path}')

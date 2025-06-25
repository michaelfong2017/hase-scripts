import pandas as pd
import os
import re  # Added for regex substitution
import argparse  # For command-line arguments

# Define the field mappings
normal_mapping = {
    "Transaction Date (value)": "Template_Located_FraudPayment1_Date",
    "Originating Amount": "Template_Located_FraudPayment1_Amount",
    "Beneficiary Bank Raw": "Template_Located_FraudPayment1_ToBank",
    "Originator Bank Raw": "Template_Located_FraudPayment1_FromBank",
    "Originator Account Number": "Template_Located_FraudPayment1_FromAccountNumber",
    "Beneficiary Account Number": "Template_Located_FraudPayment1_ToAccountNumber",
    "Originator Name": "Template_Located_FraudPayment1_FromName",
    "Originating Currency": "Template_Located_FraudPayment1_Currency",
    "Beneficiary Name": "Template_Located_FraudPayment1_ToName",
    "Converted Amount": "Template_Located_FraudPayment1_Amount",
    "Fraud Payment": "",  # Empty value for special handling
}

# No edge cases anymore - using normal mapping for all rows

def wrap_value(value, tag):
    """Wrap value in XML tags if value exists"""
    return f"<{tag}>{value}</{tag}>" if pd.notna(value) else value

def process_csv_file(filepath, verbose=False):
    """Process a single CSV file with XML tagging"""
    df = pd.read_csv(filepath)
    
    # Prepare output filename with _edited suffix
    filename, ext = os.path.splitext(filepath)
    output_filepath = f"{filename}_edited{ext}"
    
    # Debug: Print column names to verify structure
    if verbose:
        print(f"Columns in file: {list(df.columns)}")
    
    # No more edge case handling - using normal mapping for all rows
    
    # Create list for processed rows
    processed_rows = []
    
    for index, row in df.iterrows():
        new_row = {}
        # Use normal mapping for all rows
        mapping = normal_mapping
        payment_index = str(row["Fraud Payment"])
            
        # Debug: Create a variable to track if we've seen the Fraud Payment column
        has_fraud_payment_column = "Fraud Payment" in df.columns
        if verbose:
            print(f"Has Fraud Payment column: {has_fraud_payment_column}")
        
        for col in df.columns:
            # Debug: Print column name and type to check exact match
            if verbose and "fraud" in str(col).lower():
                print(f"Found column: '{col}', type: {type(col)}, comparing with 'Fraud Payment'")
                print(f"Equal?: {col == 'Fraud Payment'}")
            
            # Get base tag if exists in mapping
            base_tag = mapping.get(col)
            value = row[col]
            
            # Special handling for Fraud Payment column
            if col == "Fraud Payment":
                # Just add the closing tag to the value
                new_row[col] = f"{value}</Template_Located_FraudPayment{payment_index}>"
                if verbose:
                    print(f"Added closing tag to Fraud Payment column: {new_row[col]}")
            elif base_tag:
                # Generate dynamic tag using payment index
                dynamic_tag = re.sub(
                    r'FraudPayment\d+', 
                    f'FraudPayment{payment_index}', 
                    base_tag
                )
                
                if col == "Transaction Date (value)":
                    # Wrap with field tag and prepend root tag
                    wrapped = wrap_value(value, dynamic_tag)
                    new_row[col] = f"<Template_Located_FraudPayment{payment_index}>{wrapped}"
                else:
                    # Apply normal field wrapping
                    new_row[col] = wrap_value(value, dynamic_tag)
            else:
                new_row[col] = value
        
        # Debug: If we don't have a Fraud Payment column, add the closing tag to the last column
        if not has_fraud_payment_column:
            last_col = list(df.columns)[-1]
            if verbose:
                print(f"No Fraud Payment column found. Adding closing tag to last column: {last_col}")
            new_row[last_col] = f"{new_row[last_col]}</Template_Located_FraudPayment{payment_index}>"
        
        processed_rows.append(new_row)
        
    # Create new DataFrame and save to new file
    processed_df = pd.DataFrame(processed_rows)
    
    # Debug: Print a sample of the processed data
    if verbose:
        print("\nSample of processed data:")
        print(processed_df.head(1).to_string())
    
    # Ensure the closing tag is properly added by directly manipulating the CSV content
    processed_df.to_csv(output_filepath, index=False, quoting=1)  # quoting=1 means QUOTE_ALL
    print(f"Processed: {filepath}")
    print(f"Saved as: {output_filepath}")

def process_all_csv_files(directory, verbose=False):
    """Process all CSV files in the given directory"""
    count = 0
    for filename in os.listdir(directory):
        if filename.endswith(".csv"):
            filepath = os.path.join(directory, filename)
            process_csv_file(filepath, verbose)
            count += 1
    
    if count == 0:
        print("No CSV files found in the directory.")
    else:
        print(f"Processed {count} CSV files.")

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Process CSV files and add XML tags.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-f', '--file', help='Process a specific CSV file')
    group.add_argument('--all', action='store_true', help='Process all CSV files in the script directory')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose debug output')
    
    args = parser.parse_args()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    if args.all:
        process_all_csv_files(script_dir, args.verbose)
    else:
        # Handle specific file
        if os.path.isabs(args.file):
            filepath = args.file
        else:
            filepath = os.path.join(script_dir, args.file)
        
        if not os.path.exists(filepath):
            print(f"Error: File '{filepath}' not found.")
        elif not filepath.endswith('.csv'):
            print(f"Error: File '{filepath}' is not a CSV file.")
        else:
            process_csv_file(filepath, args.verbose)

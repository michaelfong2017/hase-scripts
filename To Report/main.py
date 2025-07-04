import json
import pandas as pd
from datetime import datetime
from tqdm import tqdm
import argparse
import os
import sys
import re

# Function to extract content inside json tags
def extract_json_content(text):
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    match2 = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
    match3 = re.search(r'```json\s*(\{.*\})', text, re.DOTALL)  # New case for no closing tag
    match4 = re.search(r'```\s*(\{.*\})', text, re.DOTALL)  # New case for no closing tag

    if match:
        return match.group(1)
    elif match2:
        return match2.group(1)
    elif match3:
        return match3.group(1)
    elif match4:
        return match4.group(1)
    else:
        return text

def format_amount(amount, currency):
    """Format amount with proper comma separators"""
    if amount is None:
        return "null"
    return f"{currency}{amount:,}" if currency else f"{amount:,}"

def check_same_person(from_name, to_name):
    """Check if from and to names refer to the same person"""
    if not from_name or not to_name:
        return False
    return from_name.strip().upper() == to_name.strip().upper()

def safe_get_string(value):
    """Safely get string value, handling None and converting to string"""
    if value is None:
        return ""
    return str(value).strip()

def build_payment_description(tx, idx, debug_messages):
    """Build payment description handling ALL combinations of missing fields with null safety"""
    
    # Required fields - alert if missing but continue processing
    date_str = "null"
    amount_str = "null"
    
    if tx.get('date'):
        try:
            date_str = datetime.strptime(str(tx['date']), '%Y-%m-%d').strftime('%d %b %Y')
        except ValueError:
            date_str = str(tx['date'])
            debug_msg = f"Payment {idx}: Invalid date format - {tx['date']}"
            debug_messages.append(debug_msg)
    else:
        debug_msg = f"Payment {idx}: ALERT - Missing required date field"
        debug_messages.append(debug_msg)
    
    if tx.get('amount') is not None:
        amount_str = format_amount(tx['amount'], safe_get_string(tx.get('currency', '')))
    else:
        debug_msg = f"Payment {idx}: ALERT - Missing required amount field"
        debug_messages.append(debug_msg)
    
    # Extract all available information - safely handle nulls
    from_info = tx.get('from', {}) or {}
    to_info = tx.get('to', {}) or {}
    
    from_name = safe_get_string(from_info.get('name'))
    from_bank = safe_get_string(from_info.get('bank'))
    from_account = safe_get_string(from_info.get('account_number'))
    
    to_name = safe_get_string(to_info.get('name'))
    to_bank = safe_get_string(to_info.get('bank'))
    to_account = safe_get_string(to_info.get('account_number'))
    
    channel = safe_get_string(tx.get('channel'))
    can_be_located = tx.get('can_be_located', True)
    is_cancelled = tx.get('is_cancelled', False)
    
    # Convert empty strings to None for easier logic
    from_name = from_name if from_name else None
    from_bank = from_bank if from_bank else None
    from_account = from_account if from_account else None
    to_name = to_name if to_name else None
    to_bank = to_bank if to_bank else None
    to_account = to_account if to_account else None
    channel = channel if channel else None
    
    # Status indicators
    location_status = "it can be located in banking system" if can_be_located else "it cannot be located in banking system"
    cancellation_note = "; payment cancellation has been requested" if is_cancelled else ""
    
    # Template selection for ALL possible combinations
    description_parts = [f"Payment {idx}: {date_str}, {amount_str}"]
    
    # Template 1: Complete information with channel
    if from_name and from_bank and from_account and to_name and to_bank and to_account and channel:
        if check_same_person(from_name, to_name) and from_bank == to_bank:
            description_parts.append(f"via {channel}, from {from_name}'s same name {from_bank} account {from_account}, to {to_name}'s {to_bank} account {to_account}")
        else:
            description_parts.append(f"via {channel}, from {from_name}'s {from_bank} account {from_account}, to {to_name}'s {to_bank} account {to_account}")
    
    # Template 2: Complete information without channel
    elif from_name and from_bank and from_account and to_name and to_bank and to_account:
        if check_same_person(from_name, to_name) and from_bank == to_bank:
            description_parts.append(f"from {from_name}'s same name {from_bank} account {from_account}, to {to_name}'s {to_bank} account {to_account}")
        else:
            description_parts.append(f"from {from_name}'s {from_bank} account {from_account}, to {to_name}'s {to_bank} account {to_account}")
    else:
        # Fallback template logic
        parts = []
        if channel:
            parts.append(f"via {channel}")
        
        if from_name or from_bank or from_account:
            from_desc = []
            if from_name:
                from_desc.append(f"{from_name}'s")
            if from_bank:
                from_desc.append(f"{from_bank}")
            from_desc.append("account")
            if from_account:
                from_desc.append(from_account)
            parts.append(f"from {' '.join(from_desc)}")
        
        if to_name or to_bank or to_account:
            to_desc = []
            if to_name:
                to_desc.append(f"{to_name}'s")
            if to_bank:
                to_desc.append(f"{to_bank}")
            to_desc.append("account")
            if to_account:
                to_desc.append(to_account)
            parts.append(f"to {' '.join(to_desc)}")
        
        if parts:
            description_parts.append(", ".join(parts))
        else:
            description_parts.append("incomplete transaction information")
    
    # Combine all parts
    full_description = ", ".join(description_parts)
    full_description += f" - {location_status}{cancellation_note}."
    
    return full_description

def map_ground_truth_to_summary_updated_format(row):
    """Convert Ground Truth JSON data with updated format for no transactions"""
    debug_messages = []
    
    try:
        data = json.loads(row['Ground Truth'])
        
        summary = []
        summary.append('Source: ADCC')
        
        # Handle fraud_type specially - use "Not provided" if null or empty
        fraud_type = safe_get_string(data.get('fraud_type'))
        if not fraud_type:
            fraud_type = "Not provided"
        summary.append(f"Fraud Type: {fraud_type}")
        
        # Handle other global fields - only include if they have values (null-safe)
        police_reference = safe_get_string(data.get('police_reference'))
        if police_reference:
            summary.append(f"Police Reference: {police_reference}")
        
        police_team = safe_get_string(data.get('police_team'))
        if police_team:
            summary.append(f"Police Team: {police_team}")
        
        writ_no = safe_get_string(data.get('writ_no'))
        if writ_no:
            summary.append(f"Writ No.: {writ_no}")
        
        contact_person = safe_get_string(data.get('contact_person'))
        if contact_person:
            summary.append(f"Contact Person: {contact_person}")
        
        transactions = data.get('alerted_transactions', [])
        if not transactions:
            # NEW FORMAT: No "Alerted transaction:" header, direct message
            summary.append("No transaction provided in the intelligence")
        else:
            # Only add the header if there are actual transactions
            summary.append("")  # Empty line before transactions
            summary.append('Alerted transaction:')
            
            for idx, tx in enumerate(transactions, 1):
                payment_desc = build_payment_description(tx, idx, debug_messages)
                summary.append(payment_desc)
        
        return '\n'.join(summary), '; '.join(debug_messages) if debug_messages else ""
    
    except json.JSONDecodeError as e:
        error_msg = f"Error processing JSON: Invalid JSON format - {str(e)}"
        return error_msg, error_msg
    
    except Exception as e:
        error_msg = f"Error processing data: {str(e)}"
        return error_msg, error_msg

def get_user_column_selections(available_columns):
    """Interactive function to get column selections from user"""
    print("\n" + "="*60)
    print("COLUMN SELECTION INTERFACE")
    print("="*60)
    print(f"Available columns: {len(available_columns)}")
    for i, col in enumerate(available_columns, 1):
        print(f"  {i:2d}. {col}")
    
    print("\nEnter column numbers separated by commas (e.g., 1,3,5)")
    print("Or type 'all' to select all columns")
    
    while True:
        user_input = input("Your selection: ").strip()
        
        if user_input.lower() == 'all':
            return available_columns
        
        if not user_input:
            print("Please enter a selection or type 'all'")
            continue
        
        try:
            # Parse column numbers
            col_numbers = [int(x.strip()) for x in user_input.split(',')]
            
            # Validate column numbers
            invalid_nums = [num for num in col_numbers if num < 1 or num > len(available_columns)]
            if invalid_nums:
                print(f"Invalid column numbers: {invalid_nums}")
                print("Please try again.")
                continue
            
            # Convert to column names
            selected_columns = [available_columns[num-1] for num in col_numbers]
            return selected_columns
            
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")
            continue

def process_selected_columns(input_file, selected_columns, output_file):
    """Process selected columns and save to single output file with separate columns for each analysis"""
    
    # Read the original dataframe
    print(f"Reading input file: {input_file}")
    df = pd.read_csv(input_file)
    
    print(f"Original data shape: {df.shape}")
    print(f"Selected columns: {selected_columns}")
    
    # Start with ALL original columns
    df_result = df.copy()
    
    print(f"Processing {len(df_result)} rows for {len(selected_columns)} column analyses...")
    
    # Process each selected column separately
    for col in selected_columns:
        print(f"Processing analysis for column: {col}")
        
        def safe_process_row(row):
            try:
                # Create a temporary row with the selected column as 'Ground Truth' for processing
                temp_row = pd.Series({'Ground Truth': extract_json_content(row[col])})
                summary, debug_info = map_ground_truth_to_summary_updated_format(temp_row)
                return pd.Series([summary, debug_info])
            except Exception as e:
                error_msg = f"Error in row {row.name}: {str(e)}"
                return pd.Series([error_msg, error_msg])
        
        # Apply processing with progress bar for this column
        tqdm.pandas(desc=f"Processing {col}")
        result_columns = df_result.progress_apply(safe_process_row, axis=1)
        
        # Create column-specific names
        summary_col_name = f"{col}_text_summary"
        debug_col_name = f"{col}_debug_alerts"
        
        # Add the results as new columns
        df_result[summary_col_name] = result_columns[0]
        df_result[debug_col_name] = result_columns[1]
        
        # Calculate statistics for this column
        rows_with_alerts = len(df_result[df_result[debug_col_name] != ''])
        print(f"  - Column {col}: {rows_with_alerts} rows with alerts")
    
    # Save to output file
    df_result.to_csv(output_file, index=False)
    
    # Calculate overall statistics
    total_alert_columns = [col for col in df_result.columns if col.endswith('_debug_alerts')]
    total_summary_columns = [col for col in df_result.columns if col.endswith('_text_summary')]
    
    print(f"\nProcessing completed:")
    print(f"  - Total rows: {len(df_result)}")
    print(f"  - Original columns: {len(df.columns)}")
    print(f"  - Analyses performed: {len(selected_columns)}")
    print(f"  - Summary columns created: {total_summary_columns}")
    print(f"  - Debug columns created: {total_alert_columns}")
    print(f"  - Total columns in output: {len(df_result.columns)}")
    print(f"  - Output file: {output_file}")
    
    return df_result

def main():
    parser = argparse.ArgumentParser(description='Process CSV file with selected columns')
    parser.add_argument('--input', '-i', default='exam18_test_set_v1_test_set_model_responses.csv',
                       help='Input CSV file (default: exam18_test_set_v1_test_set_model_responses.csv)')
    parser.add_argument('--columns', '-c', nargs='+',
                       help='Specify column names directly (space separated)')
    parser.add_argument('--no-interactive', action='store_true',
                       help='Disable interactive mode (requires --columns)')
    
    args = parser.parse_args()
    
    # Determine input and output files
    input_file = args.input
    base_name = os.path.splitext(input_file)[0]
    output_file = f"{base_name}_text.csv"
    
    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        sys.exit(1)
    
    try:
        # Read CSV to get available columns
        df = pd.read_csv(input_file)
        
        available_columns = list(df.columns)  # Include ALL columns including Ground Truth
        
        # Get column selection - DEFAULT TO INTERACTIVE MODE
        if args.columns and args.no_interactive:
            # Use command line specified columns only if explicitly disabled interactive
            selected_columns = args.columns
            # Validate columns exist
            invalid_cols = [col for col in selected_columns if col not in available_columns]
            if invalid_cols:
                print(f"Error: Invalid columns specified: {invalid_cols}")
                print(f"Available columns: {available_columns}")
                sys.exit(1)
            print(f"Using command line column selection: {selected_columns}")
        elif args.columns and not args.no_interactive:
            # Show command line columns but still allow interactive override
            print(f"Command line columns specified: {args.columns}")
            print("You can press Enter to use these, or make a new selection:")
            selected_columns = get_user_column_selections(available_columns)
        else:
            # DEFAULT: Interactive mode
            selected_columns = get_user_column_selections(available_columns)
        
        if not selected_columns:
            print("No valid columns selected. Exiting.")
            sys.exit(0)
        
        # Process selected columns
        result_df = process_selected_columns(input_file, selected_columns, output_file)
        
        print(f"\n{'='*50}")
        print("PROCESSING COMPLETE")
        print(f"{'='*50}")
        print(f"Input file: {input_file}")
        print(f"Output file: {output_file}")
        print(f"Columns processed: {selected_columns}")
        
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

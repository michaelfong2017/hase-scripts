import pandas as pd
import json
import random
import re
import os
from typing import Dict, List, Tuple, Any
from pattern import *
from json_parser import JSONParser
from field_mapper import FieldMapper
from text_replacer import TextReplacer
from diff_reporter import DiffReporter

# Global set number tracker
global_set_number = 0

def initialize_global_set_number(df):
    global global_set_number
    if 'Set Number' in df.columns:
        global_set_number = df['Set Number'].max()
    else:
        global_set_number = 0
    print(f"Initialized global set number to: {global_set_number}")

def get_next_set_number():
    global global_set_number
    global_set_number += 1
    return global_set_number

def main():
    random.seed(42)
    
    csv_file_path = input("Enter CSV file path (or press Enter for default): ").strip()
    if not csv_file_path:
        csv_file_path = 'Dataset_Source_v5_updated_with_groundtruth.csv'
    
    try:
        df = pd.read_csv(csv_file_path, na_filter=False)
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return
    
    initialize_global_set_number(df)
    
    input_column = 'Input'
    json_column = 'Ground Truth'
    transaction_column = 'Transactions'
    
    if 'Randomization Set' not in df.columns:
        df['Randomization Set'] = 0
    if 'Variant Number' not in df.columns:
        df['Variant Number'] = 1
    
    all_dataframes = [df.copy()]
    
    for type_name in df['Type'].unique():
        for variant_num in df[df['Type'] == type_name]['Variant Number'].unique():
            type_variant_rows = df[(df['Type'] == type_name) & (df['Variant Number'] == variant_num)].copy()
            randomization_count = RANDOMIZATION_COUNTS.get(type_name, 3)
            
            print(f"Creating {randomization_count} randomized sets for Type: {type_name}, Variant: {variant_num}")
            
            for randomization_num in range(1, randomization_count + 1):
                print(f"  Processing randomization set {randomization_num}...")
                
                randomized_df = type_variant_rows.copy()
                randomized_df['Randomization Set'] = randomization_num
                
                current_set_number = get_next_set_number()
                randomized_df['Set Number'] = current_set_number
                
                case_increment = current_set_number * 50
                if 'Case Number' in randomized_df.columns:
                    randomized_df['Case Number'] = randomized_df['Original Case Number'] + case_increment
                
                # Process each row for this randomization
                for index, row in randomized_df.iterrows():
                    original_input = str(row[input_column])
                    ground_truth_str = str(row[json_column])
                    original_transactions = str(row[transaction_column])
                    document_type = str(row['Type'])
                    
                    try:
                        # Step 1: Parse Ground Truth JSON
                        parser = JSONParser()
                        ground_truth_json = parser.parse_json(ground_truth_str)
                        
                        # Step 2: Collect all mappings needed
                        mapper = FieldMapper(document_type)
                        mappings, field_types = mapper.collect_mappings(ground_truth_json)
                        
                        # Step 3: Apply replacements to all texts
                        replacer = TextReplacer(mappings)
                        
                        # Replace in JSON
                        randomized_json = replacer.replace_in_json(ground_truth_json)
                        
                        # Replace in Input and Transactions
                        randomized_input = replacer.replace_in_text(original_input)
                        randomized_transactions = replacer.replace_in_text(original_transactions)
                        
                        # Convert JSON back to string
                        randomized_ground_truth_str = json.dumps(randomized_json, indent=2, ensure_ascii=False)
                        
                        # Step 4: Generate reports
                        reporter = DiffReporter(mappings, field_types)

                        # Generate all reports
                        original_values = reporter.get_original_values()
                        replacement_values = reporter.get_replacement_values()
                        replacement_summary = reporter.generate_replacement_summary(original_input, original_transactions, ground_truth_str)
                        replacement_alerts = reporter.generate_alerts(original_input, original_transactions, ground_truth_str, document_type)
                        field_specific_alerts = reporter.generate_field_specific_alerts(original_input, original_transactions, ground_truth_str, document_type)

                        # Update the DataFrame with all columns including field-specific alerts
                        randomized_df.at[index, input_column] = randomized_input
                        randomized_df.at[index, json_column] = randomized_ground_truth_str
                        randomized_df.at[index, transaction_column] = randomized_transactions
                        randomized_df.at[index, 'Original_Values'] = original_values
                        randomized_df.at[index, 'Replacement_Values'] = replacement_values
                        randomized_df.at[index, 'Replacement_Summary'] = replacement_summary
                        randomized_df.at[index, 'Replacement_Alerts'] = replacement_alerts

                        # Add field-specific alert columns
                        for field_name, alert_content in field_specific_alerts.items():
                            randomized_df.at[index, field_name] = alert_content
                        
                    except Exception as e:
                        print(f"Error processing row {index}, randomization {randomization_num}: {str(e)}")
                        randomized_df.at[index, 'Original_Values'] = f"Error: {str(e)}"
                        randomized_df.at[index, 'Replacement_Values'] = ""
                        randomized_df.at[index, 'Replacement_Summary'] = f"Error: {str(e)}"
                        randomized_df.at[index, 'Replacement_Alerts'] = ""
                        
                        # Set all field alert columns to empty on error
                        field_alert_columns = ['Alert_Dates', 'Alert_Amounts', 'Alert_Names', 'Alert_Account_Numbers', 
                                            'Alert_Banks', 'Alert_Police_References', 'Alert_Contact_Persons', 
                                            'Alert_Writ_Numbers', 'Alert_Cancel_Amount_Requested']
                        for col in field_alert_columns:
                            randomized_df.at[index, col] = ""

                all_dataframes.append(randomized_df)
    
    final_df = pd.concat(all_dataframes, ignore_index=True)
    
    columns_to_clean = ['Transactions', 'Input', 'Instruction', 'Ground Truth']
    for col in columns_to_clean:
        if col in final_df.columns:
            final_df[col] = final_df[col].fillna('')
    
    input_dir = os.path.dirname(csv_file_path)
    input_filename = os.path.basename(csv_file_path)
    input_name, input_ext = os.path.splitext(input_filename)
    
    output_filename = os.path.join(input_dir, f'{input_name}_RANDOMIZED_ROWS{input_ext}')
    
    final_df.to_csv(output_filename, index=False, encoding='utf-8-sig', na_rep='')
    
    print(f"Randomization complete! Saved to: {output_filename}")
    print(f"Total rows in output: {len(final_df)}")

if __name__ == "__main__":
    print("Enhanced CSV Data Randomizer - Modular Version")
    print("=" * 60)
    main()

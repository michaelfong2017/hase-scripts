from data_processor import (
    extract_unique_values, strict_normalization_functions, 
    random_generation_functions, replace_in_dataframe,
    save_json_utf8, load_json_utf8
)
import pandas as pd

def main():
    """Main execution function"""
    csv_file = "Dataset_Source_v5_updated_with_groundtruth.csv"
    
    try:
        print("Extracting unique values...")
        unique_values = extract_unique_values(csv_file)
        
        print("\n=== EXTRACTION RESULTS ===")
        for field, values in unique_values.items():
            print(f"\n{field.upper()}: {len(values)} unique values")
            if len(values) <= 10:
                print(f"  All values: {values}")
            else:
                print(f"  First 5 values: {values[:5]}")
                print(f"  Last 5 values: {values[-5:]}")
        
        save_json_utf8(unique_values, 'unique_values_extracted.json')
        print(f"\nResults saved to 'unique_values_extracted.json'")
        
        print("\n=== TESTING NORMALIZATION (■ KEPT AS-IS) ===")
        test_values = {
            'name': ['Mr    Chan Tai Man', 'MS. WONG SIU MING', 'DR LEE KA WAI AND OTHERS'],
            'bank': ['The Hongkong and Shanghai Banking Corporation Limited', 'HASE', '滙豐', '渣打银行', 'ICBKCNB■■■■'],
            'amount': ['HKD 77,000.50', '50000', '$123,456.78'],
            'account_number': ['333-333333-101', '444 444444 202', 'FPS:122222221', '000402■■■■■■■'],
            'police_reference': ['TYRN240■■■■', 'CASE123■■■', 'ESPS ■■■■/2024 and WTSDIST ■■■■■■■■'],
            'writ_no': ['01■■■', 'TM86■■/2024', '3■■■/2025'],
            'contact_person': ['PC 2■■■■', 'SGT A■■■', 'PC■■■■■']
        }
        
        for field, test_vals in test_values.items():
            if field in strict_normalization_functions:
                print(f"\n{field.upper()} normalization:")
                for val in test_vals:
                    normalized = strict_normalization_functions[field](val)
                    print(f"  '{val}' → '{normalized}'")
        
        print("\n=== TESTING RANDOM GENERATION ===")
        for field, generator in random_generation_functions.items():
            try:
                random_value = generator()
                print(f"Random {field}: {random_value}")
            except Exception as e:
                print(f"Error generating random {field}: {e}")
        
        print("\n=== NORMALIZATION WORKFLOW DEMO ===")
        demonstrate_workflow(unique_values)
        
    except FileNotFoundError:
        print(f"CSV file '{csv_file}' not found. Please ensure the file exists in the current directory.")
    except Exception as e:
        print(f"Error occurred: {e}")

def demonstrate_workflow(unique_values):
    """Demonstrate the complete normalization workflow"""
    print("Demonstrating normalization workflow...")
    
    if 'name' in unique_values:
        print(f"\nOriginal names found: {unique_values['name'][:5]}...")
    
    normalized_mappings = {}
    for field, values in unique_values.items():
        if field in strict_normalization_functions:
            normalized_mappings[field] = {}
            normalizer = strict_normalization_functions[field]
            for value in values:
                normalized = normalizer(value)
                if normalized != value:
                    normalized_mappings[field][value] = normalized
    
    print("\nNormalization mappings created (■ kept as-is):")
    for field, mappings in normalized_mappings.items():
        if mappings:
            print(f"\n{field.upper()}:")
            for original, normalized in list(mappings.items())[:3]:
                print(f"  '{original}' → '{normalized}'")
            if len(mappings) > 3:
                print(f"  ... and {len(mappings) - 3} more")
    
    save_json_utf8(normalized_mappings, 'normalization_mappings.json')
    print(f"\nNormalization mappings saved to 'normalization_mappings.json'")

if __name__ == "__main__":
    main()

import pandas as pd
import os

def split_dataset():
    """
    Split Dataset_Source_v5_updated_with_groundtruth_RANDOMIZED_ROWS.csv into train and test sets
    """
    # Define the file path
    file_path = 'Dataset_Source_v5_updated_with_groundtruth_RANDOMIZED_ROWS.csv'
    
    # Load the CSV file
    try:
        df = pd.read_csv(file_path, na_filter=False)
        print(f"Successfully loaded {file_path}")
        print(f"Total rows: {len(df)}")
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return
    
    # Define test case numbers
    test_case_numbers = [2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 20, 25]
    
    # Create test set: 
    # - Variant Number 1 with Randomization Set 0 (original data) for test case numbers
    # - Variant Number 1 with Randomization Set 1 for test case numbers
    test_set_variant_1 = df[(df['Original Case Number'].isin(test_case_numbers))]
    
    
    # Combine both test set parts
    test_set = pd.concat([test_set_variant_1], ignore_index=True)
    
    # Create train set: exclude ALL rows with test case numbers (not just test set rows)
    train_set = df[~df['Original Case Number'].isin(test_case_numbers)].copy()
    
    # Save to CSV files
    train_set.to_csv('full3680_train_set_v5.csv', index=False, encoding='utf-8-sig', na_rep='')
    test_set.to_csv('second675_train_set_v5.csv', index=False, encoding='utf-8-sig', na_rep='')
    
    # Print summary information
    print(f"\n=== Split Results ===")
    print(f"Train set: {len(train_set)} rows")
    print(f"Test set: {len(test_set)} rows")
    print(f"Total original rows: {len(df)}")
    
    print(f"\nTest set breakdown by Variant Number:")
    print(test_set['Variant Number'].value_counts().sort_index())
    
    print(f"\nTest set breakdown by Randomization Set:")
    print(test_set['Randomization Set'].value_counts().sort_index())
    
    print(f"\nTest set breakdown by Original Case Number:")
    print(test_set['Original Case Number'].value_counts().sort_index())
    
    print(f"\nTrain set breakdown by Variant Number:")
    print(train_set['Variant Number'].value_counts().sort_index())
    
    # Verify file creation
    if os.path.exists('full3680_train_set_v5.csv') and os.path.exists('second675_train_set_v5.csv'):
        print(f"\n✓ Files saved successfully!")
        print(f"  - full3680_train_set_v5.csv ({len(train_set)} rows)")
        print(f"  - second675_train_set_v5.csv ({len(test_set)} rows)")
    else:
        print(f"\n✗ Error: Files were not created properly.")

if __name__ == "__main__":
    print("Dataset Splitter")
    print("================")
    print("Splitting dataset into train and test sets...")
    print("Test set includes:")
    print("- Variant 1 with Randomization Set 0 (original) for case numbers: 2,3,5,6,7,8,9,10,11,12,13,20,25")
    print("- Variant 1 with Randomization Set 1 for the same case numbers")
    print("Train set excludes ALL rows with these case numbers")
    print()
    
    split_dataset()

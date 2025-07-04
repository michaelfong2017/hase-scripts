import pandas as pd

# Load the two CSV files
source_file = 'Dataset_Source_v5_updated_with_groundtruth_RANDOMIZED_ROWS.csv'
test_set_file = 'full60_test_set_v5.csv'

source_df = pd.read_csv(source_file)
test_set_df = pd.read_csv(test_set_file)

# Define the composite key columns
key_cols = ['Case Number', 'Intelligence Number']

# Set the composite key as index for both dataframes
source_df.set_index(key_cols, inplace=True)
test_set_df.set_index(key_cols, inplace=True)

# Update source_df with rows from test_set_df where the composite key matches
# This will replace entire rows in source_df with corresponding rows from test_set_df
source_df.update(test_set_df)

# Reset index to restore Case Number and Intelligence Number as regular columns
source_df.reset_index(inplace=True)

# Save the updated dataframe
updated_file = 'Dataset_Source_v5_updated_with_groundtruth_RANDOMIZED_ROWS_updated.csv'
source_df.to_csv(updated_file, index=False)

print(f"Updated file saved as: {updated_file}")
print(f"Source dataset shape: {source_df.shape}")
print(f"Test set shape: {test_set_df.shape}")

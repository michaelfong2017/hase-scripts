import os
import pandas as pd

# Recursively find all CSV files in the current directory and subdirectories
csv_files = []
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.lower().endswith('.csv'):
            csv_files.append(os.path.join(root, file))

print(f"Found {len(csv_files)} CSV files")

# Process each CSV file: read and save with utf-8-sig encoding
processed_count = 0
failed_count = 0

for file_path in csv_files:
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Save with UTF-8-BOM encoding (overwrites the original file)
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ Processed: {file_path}")
        processed_count += 1
        
    except Exception as e:
        print(f"❌ Failed to process {file_path}: {e}")
        failed_count += 1

print(f"\n📊 Summary:")
print(f"Total files found: {len(csv_files)}")
print(f"Successfully processed: {processed_count}")
print(f"Failed: {failed_count}")

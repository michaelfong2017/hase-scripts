import os
import pandas as pd
import glob
from step1_create_outputs import create_model_outputs
from step2_aggregate_results import aggregate_model_results
from step3_cross_model_comparison import create_cross_model_comparisons
from step4_custom_aggregation import aggregate_custom_results

def main():
    """Main function to process all files and create comparisons."""
    # Define input folder and automatically find all CSV files
    input_folder = "../Cycle3 Results Raw/"
    input_files = glob.glob(os.path.join(input_folder, "*.csv"))

    print(f"Found {len(input_files)} CSV files in {input_folder}:")
    for file in input_files:
        print(f"  - {os.path.basename(file)}")

    # Define output base folder
    output_base_folder = "evaluation_outputs"
    os.makedirs(output_base_folder, exist_ok=True)

    all_results = []
    
    # Step 1: Process each file and create outputs
    print("\n🔄 Step 1: Creating model outputs...")
    for file_path in input_files:
        result = create_model_outputs(file_path, output_base_folder)
        if result:  # Only add successful results
            all_results.append(result)
    
    # Step 2: Aggregate results for each model
    print("\n🔄 Step 2: Aggregating results...")
    for result in all_results:
        aggregate_model_results(result, output_base_folder)
    
    # Step 3: Create cross-model comparisons
    print("\n🔄 Step 3: Creating cross-model comparisons...")
    if all_results:
        create_cross_model_comparisons(all_results, output_base_folder)
    
    # Step 4: Create custom aggregation (detailed files, half analysis, type analysis)
    print("\n🔄 Step 4: Creating custom aggregation...")
    if all_results:
        aggregate_custom_results(all_results, output_base_folder)
    
    print(f"\n🎉 All processing complete! Check the '{output_base_folder}' folder for results.")
    print(f"Successfully processed {len(all_results)} out of {len(input_files)} files.")

if __name__ == "__main__":
    main()

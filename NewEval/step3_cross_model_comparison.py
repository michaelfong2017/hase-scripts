import os
import pandas as pd
from utils import is_transaction_field

def create_cross_model_comparisons(all_results, output_base_folder):
    """Step 3: Create cross-model comparison files."""
    comparison_folder = os.path.join(output_base_folder, "cross_model_comparisons")
    os.makedirs(comparison_folder, exist_ok=True)
    
    # Aggregate by type global comparison
    type_global_comparison = []
    for result in all_results:
        df = result['agg_type_global'].copy()
        df['Model'] = result['model_name']
        type_global_comparison.append(df)
    
    if type_global_comparison:
        combined_type_global = pd.concat(type_global_comparison, ignore_index=True)
        combined_type_global.to_csv(os.path.join(comparison_folder, "cross_model_type_global.csv"), index=False, encoding="utf-8-sig")
    
    # Aggregate by field global comparison - FILTER OUT TRANSACTION FIELDS MORE AGGRESSIVELY
    field_global_comparison = []
    for result in all_results:
        df = result['agg_field_global'].copy()
        # FILTER OUT any fields that are transaction-related
        df = df[~df['Field'].apply(is_transaction_field)]
        df['Model'] = result['model_name']
        field_global_comparison.append(df)
    
    if field_global_comparison:
        combined_field_global = pd.concat(field_global_comparison, ignore_index=True)
        combined_field_global.to_csv(os.path.join(comparison_folder, "cross_model_field_global.csv"), index=False, encoding="utf-8-sig")
    
    # Aggregate by type and field global comparison - FILTER OUT TRANSACTION FIELDS MORE AGGRESSIVELY
    composite_global_comparison = []
    for result in all_results:
        df = result['agg_composite_global'].copy()
        # FILTER OUT any fields that are transaction-related
        df = df[~df['Field'].apply(is_transaction_field)]
        df['Model'] = result['model_name']
        composite_global_comparison.append(df)
    
    if composite_global_comparison:
        combined_composite_global = pd.concat(composite_global_comparison, ignore_index=True)
        combined_composite_global.to_csv(os.path.join(comparison_folder, "cross_model_type_and_field_global.csv"), index=False, encoding="utf-8-sig")
    
    # Aggregate by type transaction comparison
    type_tx_comparison = []
    for result in all_results:
        df = result['agg_type_tx'].copy()
        df['Model'] = result['model_name']
        type_tx_comparison.append(df)
    
    if type_tx_comparison:
        combined_type_tx = pd.concat(type_tx_comparison, ignore_index=True)
        combined_type_tx.to_csv(os.path.join(comparison_folder, "cross_model_type_transaction.csv"), index=False, encoding="utf-8-sig")
    
    # Aggregate by field transaction comparison
    field_tx_comparison = []
    for result in all_results:
        df = result['agg_field_tx'].copy()
        df['Model'] = result['model_name']
        field_tx_comparison.append(df)
    
    if field_tx_comparison:
        combined_field_tx = pd.concat(field_tx_comparison, ignore_index=True)
        combined_field_tx.to_csv(os.path.join(comparison_folder, "cross_model_field_transaction.csv"), index=False, encoding="utf-8-sig")
    
    # Aggregate by type and field transaction comparison
    composite_tx_comparison = []
    for result in all_results:
        df = result['agg_composite_tx'].copy()
        df['Model'] = result['model_name']
        composite_tx_comparison.append(df)
    
    if composite_tx_comparison:
        combined_composite_tx = pd.concat(composite_tx_comparison, ignore_index=True)
        combined_composite_tx.to_csv(os.path.join(comparison_folder, "cross_model_type_and_field_transaction.csv"), index=False, encoding="utf-8-sig")
    
    print(f"✅ Saved cross-model comparisons in {comparison_folder}")

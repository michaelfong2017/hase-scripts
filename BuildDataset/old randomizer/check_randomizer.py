import pandas as pd
import re
import json
from typing import List, Dict, Tuple, Set

def load_randomized_data(csv_file_path: str) -> pd.DataFrame:
    """Load the randomized CSV file"""
    try:
        df = pd.read_csv(csv_file_path, na_filter=False, encoding='utf-8-sig')
        print(f"Successfully loaded: {csv_file_path}")
        print(f"Total rows: {len(df)}")
        return df
    except Exception as e:
        print(f"Error loading file: {str(e)}")
        return None

def extract_changes_from_complete_mapping(complete_mapping: str) -> List[Tuple[str, str, str, str]]:
    """Extract old->new value pairs from complete mapping with location and transaction ref info"""
    if not complete_mapping or complete_mapping == "No changes":
        return []
    
    changes = []
    lines = complete_mapping.split('\n')
    
    for line in lines:
        if ' → ' in line:
            # Parse format: [Input+JSON | TxnRef: uuid] old_value → new_value
            if line.startswith('[') and ']' in line:
                bracket_content = line.split(']', 1)[0][1:]  # Remove [ and ]
                rest = line.split(']', 1)[1].strip()
                
                # Extract location and transaction ref
                location = ""
                txn_ref = ""
                
                if ' | TxnRef: ' in bracket_content:
                    location, txn_ref = bracket_content.split(' | TxnRef: ', 1)
                else:
                    location = bracket_content
                
                # Extract old and new values
                if ' → ' in rest:
                    old_val, new_val = rest.split(' → ', 1)
                    changes.append((old_val.strip(), new_val.strip(), location.strip(), txn_ref.strip()))
            elif ' → ' in line:
                # Fallback for lines without proper formatting
                old_val, new_val = line.split(' → ', 1)
                changes.append((old_val.strip(), new_val.strip(), "Unknown", ""))
    
    return changes

def check_value_replacement(text: str, old_value: str, new_value: str) -> Dict[str, any]:
    """Check if a value was properly replaced in text"""
    result = {
        'old_value_found': old_value in text,
        'new_value_found': new_value in text,
        'old_count': text.count(old_value),
        'new_count': text.count(new_value),
        'replacement_status': 'unknown'
    }
    
    if result['old_count'] == 0 and result['new_count'] > 0:
        result['replacement_status'] = 'fully_replaced'
    elif result['old_count'] > 0 and result['new_count'] > 0:
        result['replacement_status'] = 'partially_replaced'
    elif result['old_count'] > 0 and result['new_count'] == 0:
        result['replacement_status'] = 'not_replaced'
    elif result['old_count'] == 0 and result['new_count'] == 0:
        result['replacement_status'] = 'neither_found'
    
    return result

def analyze_single_row(row: pd.Series) -> Dict[str, any]:
    """Analyze a single row for replacement issues"""
    analysis = {
        'row_index': row.name,
        'randomization_set': row.get('Randomization Set', 'Unknown'),
        'document_type': row.get('Type', 'Unknown'),
        'variant_number': row.get('Variant Number', 'Unknown'),
        'changes_summary': row.get('Changes_Summary', 'No summary'),
        'issues': [],
        'replacement_summary': {}
    }
    
    # Get text columns
    input_text = str(row.get('Input', ''))
    transactions_text = str(row.get('Transactions', ''))
    ground_truth_text = str(row.get('Ground Truth', ''))
    
    # Extract changes from Complete_Mapping
    complete_mapping = str(row.get('Complete_Mapping', ''))
    changes = extract_changes_from_complete_mapping(complete_mapping)
    
    if not changes:
        analysis['replacement_summary'] = {'status': 'no_changes'}
        return analysis
    
    # Check each change
    total_issues = 0
    for old_val, new_val, location, txn_ref in changes:
        if new_val == "SKIPPED":
            continue
            
        # Check replacement in each column based on location info
        columns_to_check = []
        if 'Input' in location:
            columns_to_check.append(('Input', input_text))
        if 'Transactions' in location:
            columns_to_check.append(('Transactions', transactions_text))
        if 'JSON' in location:
            columns_to_check.append(('Ground Truth', ground_truth_text))
        
        # If no specific location, check all columns
        if not columns_to_check:
            columns_to_check = [
                ('Input', input_text),
                ('Transactions', transactions_text),
                ('Ground Truth', ground_truth_text)
            ]
        
        # Check replacement in relevant columns
        for col_name, col_text in columns_to_check:
            check_result = check_value_replacement(col_text, old_val, new_val)
            
            if check_result['replacement_status'] in ['not_replaced', 'partially_replaced']:
                analysis['issues'].append({
                    'column': col_name,
                    'old_value': old_val[:50] + "..." if len(old_val) > 50 else old_val,
                    'new_value': new_val[:50] + "..." if len(new_val) > 50 else new_val,
                    'status': check_result['replacement_status'],
                    'old_count': check_result['old_count'],
                    'new_count': check_result['new_count'],
                    'location': location,
                    'transaction_ref': txn_ref if txn_ref else 'N/A'
                })
                total_issues += 1
    
    analysis['replacement_summary'] = {
        'total_changes': len(changes),
        'issues_found': total_issues,
        'success_rate': ((len(changes) - total_issues) / len(changes) * 100) if changes else 100
    }
    
    return analysis

def generate_detailed_report(df: pd.DataFrame, analyses: List[Dict]) -> str:
    """Generate a comprehensive report"""
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("RANDOMIZATION VERIFICATION REPORT")
    report_lines.append("=" * 80)
    
    # Overall statistics
    total_rows = len(df)
    randomized_rows = len(df[df['Randomization Set'] != 0]) if 'Randomization Set' in df.columns else 0
    
    report_lines.append(f"Total rows analyzed: {total_rows}")
    report_lines.append(f"Randomized rows: {randomized_rows}")
    report_lines.append(f"Original rows: {total_rows - randomized_rows}")
    report_lines.append("")
    
    # Issue summary
    rows_with_issues = [a for a in analyses if a['issues']]
    total_issues = sum(len(a['issues']) for a in analyses)
    
    report_lines.append("ISSUE SUMMARY")
    report_lines.append("-" * 40)
    report_lines.append(f"Rows with replacement issues: {len(rows_with_issues)}")
    report_lines.append(f"Total replacement issues found: {total_issues}")
    
    if randomized_rows > 0:
        success_rate = ((randomized_rows - len(rows_with_issues)) / randomized_rows * 100)
        report_lines.append(f"Overall success rate: {success_rate:.2f}%")
    
    report_lines.append("")
    
    # Issues by document type
    if rows_with_issues:
        report_lines.append("ISSUES BY DOCUMENT TYPE")
        report_lines.append("-" * 40)
        
        type_issues = {}
        for analysis in rows_with_issues:
            doc_type = analysis['document_type']
            if doc_type not in type_issues:
                type_issues[doc_type] = {'count': 0, 'rows': []}
            type_issues[doc_type]['count'] += len(analysis['issues'])
            type_issues[doc_type]['rows'].append(analysis['row_index'])
        
        for doc_type, data in sorted(type_issues.items()):
            report_lines.append(f"{doc_type}: {data['count']} issues in {len(data['rows'])} rows")
            report_lines.append(f"  Affected rows: {', '.join(map(str, data['rows'][:10]))}")
            if len(data['rows']) > 10:
                report_lines.append(f"  ... and {len(data['rows']) - 10} more")
        
        report_lines.append("")
    
    # Detailed issues (first 20)
    if rows_with_issues:
        report_lines.append("DETAILED ISSUES (First 20)")
        report_lines.append("-" * 40)
        
        issue_count = 0
        for analysis in rows_with_issues[:20]:
            report_lines.append(f"\nRow {analysis['row_index']} ({analysis['document_type']}, Set {analysis['randomization_set']}):")
            report_lines.append(f"  Summary: {analysis['changes_summary']}")
            
            for issue in analysis['issues'][:5]:  # Max 5 issues per row
                report_lines.append(f"  ❌ {issue['column']}: {issue['status']}")
                report_lines.append(f"     '{issue['old_value']}' → '{issue['new_value']}'")
                report_lines.append(f"     Old count: {issue['old_count']}, New count: {issue['new_count']}")
                report_lines.append(f"     Location: {issue['location']}, TxnRef: {issue['transaction_ref']}")
                
                issue_count += 1
                if issue_count >= 50:  # Limit total issues shown
                    break
            
            if issue_count >= 50:
                break
    
    # Recommendations
    report_lines.append("\nRECOMMENDATIONS")
    report_lines.append("-" * 40)
    
    if total_issues == 0:
        report_lines.append("✅ All randomizations appear to be working correctly!")
    else:
        report_lines.append("1. Review the replacement logic in apply_changes_to_input() function")
        report_lines.append("2. Check for edge cases in pattern matching")
        report_lines.append("3. Verify that all value formats are being captured")
        report_lines.append("4. Consider adding more specific regex patterns")
        report_lines.append("5. Pay attention to transaction-specific issues using TxnRef info")
        
        if len(rows_with_issues) > 20:
            report_lines.append("6. Run this checker again after fixes to verify improvements")
    
    return "\n".join(report_lines)

def main():
    """Main function to check randomization quality"""
    print("Randomization Quality Checker")
    print("=" * 50)
    
    # Get CSV file path
    csv_file_path = input("Enter path to randomized CSV file (or press Enter for default): ").strip()
    if not csv_file_path:
        csv_file_path = 'Dataset_Source_v5_updated_with_groundtruth_RANDOMIZED_ROWS.csv'
    
    # Load data
    df = load_randomized_data(csv_file_path)
    if df is None:
        return
    
    # Check if required columns exist
    required_columns = ['Input', 'Transactions', 'Ground Truth', 'Complete_Mapping']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        print("Make sure you're using the updated randomizer that creates the Complete_Mapping column.")
        return
    
    # Analyze each row
    print("Analyzing randomization quality...")
    analyses = []
    
    # Only analyze randomized rows (skip original rows)
    randomized_rows = df[df.get('Randomization Set', 0) != 0] if 'Randomization Set' in df.columns else df
    
    for index, row in randomized_rows.iterrows():
        analysis = analyze_single_row(row)
        analyses.append(analysis)
        
        if index % 100 == 0:
            print(f"  Processed {index} rows...")
    
    # Generate report
    report = generate_detailed_report(df, analyses)
    print("\n" + report)
    
    # Save report to file
    save_report = input("\nSave detailed report to file? (y/n): ").strip().lower()
    if save_report == 'y':
        import os
        input_dir = os.path.dirname(csv_file_path)
        input_filename = os.path.basename(csv_file_path)
        input_name, input_ext = os.path.splitext(input_filename)
        
        report_filename = os.path.join(input_dir, f'{input_name}_QUALITY_REPORT.txt')
        
        try:
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Report saved to: {report_filename}")
        except Exception as e:
            print(f"Error saving report: {str(e)}")
    
    return analyses

if __name__ == "__main__":
    main()

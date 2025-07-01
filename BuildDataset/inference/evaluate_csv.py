# evaluate_csv.py
import pandas as pd
import sys
import os
import json
import unittest
from io import StringIO
from tqdm import tqdm
# Import the evaluation function from your core logic file
from core_logic import generate_evaluation_report

class CSVMultiColumnComparator:
    """An interactive tool to compare JSON in multiple CSV column pairs with summary reporting."""
    def __init__(self, file_path, split_mode='full'):
        try:
            self.df = pd.read_csv(file_path)
            print(f"Loaded {len(self.df)} rows from {file_path}.")
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
            sys.exit(1)
        self.column_pairs = []
        self.summary_stats = {}
        self.split_mode = split_mode  # 'full', 'half' or 'quadrant'

    def auto_select_column_pairs(self):
        """Automatically select Ground Truth as GT and all columns ending with '-Instruct' or starting with 'job_' as LLM columns."""
        columns = self.df.columns.tolist()
        
        # Find Ground Truth column
        gt_col = None
        if "Ground Truth" in columns:
            gt_col = "Ground Truth"
            print(f"✅ Found Ground Truth column: '{gt_col}'")
        else:
            print("❌ Error: 'Ground Truth' column not found in the CSV file.")
            print(f"Available columns: {', '.join(columns)}")
            return False
        
        # Find LLM columns (ending with '-Instruct' or starting with 'job_')
        llm_columns = []
        for col in columns:
            if col.endswith('-Instruct') or col.startswith('job_'):
                llm_columns.append(col)
        
        if not llm_columns:
            print("❌ Error: No columns found ending with '-Instruct' or starting with 'job_'.")
            print(f"Available columns: {', '.join(columns)}")
            return False
        
        # Create pairs
        for llm_col in llm_columns:
            self.column_pairs.append((gt_col, llm_col))
            print(f"✅ Added pair: ('{gt_col}', '{llm_col}')")
        
        print(f"\n📊 Total pairs created: {len(self.column_pairs)}")
        return True

    def select_column_pairs(self):
        """Interactive column pair selection (fallback method)."""
        columns = self.df.columns.tolist()
        while True:
            print("\n--- Select a New Pair of Columns ---")
            print("Available:", ", ".join(f"{i+1}.{c}" for i, c in enumerate(columns)))
            gt_col, llm_col = None, None
            while gt_col is None:
                try:
                    choice = input("> Enter number for GROUND TRUTH column (or 'done'): ")
                    if choice.lower() == 'done': return
                    gt_col = columns[int(choice) - 1]
                except (ValueError, IndexError):
                    print("Invalid input.")
            while llm_col is None:
                try:
                    llm_col = columns[int(input(f"> Enter number for LLM OUTPUT to compare with '{gt_col}': ")) - 1]
                except (ValueError, IndexError):
                    print("Invalid input.")
            self.column_pairs.append((gt_col, llm_col))
            print(f"Added pair: ('{gt_col}', '{llm_col}')")

    def calculate_full_statistics(self, pass_series, total_rows):
        """Calculate statistics for the full dataset without splitting."""
        count = int(pass_series.sum())
        rate = f"{(count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%"
        return {"count": count, "total": total_rows, "rate": rate}
    
    def calculate_half_statistics(self, pass_series, total_rows):
        """Calculate statistics for first half and second half of the data."""
        midpoint = total_rows // 2
        
        first_half = pass_series.iloc[:midpoint]
        second_half = pass_series.iloc[midpoint:]
        
        first_half_count = int(first_half.sum())
        second_half_count = int(second_half.sum())
        first_half_total = len(first_half)
        second_half_total = len(second_half)
        
        return {
            "first_half": {
                "count": first_half_count,
                "total": first_half_total,
                "rate": f"{(first_half_count / first_half_total * 100):.2f}%" if first_half_total > 0 else "0.00%"
            },
            "second_half": {
                "count": second_half_count,
                "total": second_half_total,
                "rate": f"{(second_half_count / second_half_total * 100):.2f}%" if second_half_total > 0 else "0.00%"
            }
        }
    
    def calculate_quadrant_statistics(self, pass_series, total_rows):
        """Calculate statistics for four quarters of the data (e.g., fraud transactions)."""
        q1_end = total_rows // 4
        q2_end = total_rows // 2
        q3_end = 3 * total_rows // 4

        first_quarter = pass_series.iloc[:q1_end]
        second_quarter = pass_series.iloc[q1_end:q2_end]
        third_quarter = pass_series.iloc[q2_end:q3_end]
        fourth_quarter = pass_series.iloc[q3_end:]

        def stats(quarter):
            count = int(quarter.sum())
            total = len(quarter)
            rate = f"{(count / total * 100):.2f}%" if total > 0 else "0.00%"
            return {"count": count, "total": total, "rate": rate}

        return {
            "first_quarter_fraud_transactions": stats(first_quarter),
            "second_quarter_fraud_transactions": stats(second_quarter),
            "third_quarter_all_transactions": stats(third_quarter),
            "fourth_quarter_all_transactions": stats(fourth_quarter)
        }
    
    def reorder_extracted_columns_among_new(self, gt_col, llm_col, original_columns):
        """Reorder only among newly added columns to put extracted columns first among new columns."""
        extracted_gt_col = f"{gt_col}_extracted_json"
        extracted_llm_col = f"{llm_col}_extracted_json"
        
        # Get all current columns
        current_columns = self.df.columns.tolist()
        
        # Identify newly added columns (not in original)
        new_columns = [col for col in current_columns if col not in original_columns]
        
        # Separate extracted columns from other new columns
        extracted_cols = [extracted_gt_col, extracted_llm_col]
        other_new_cols = [col for col in new_columns if col not in extracted_cols]
        
        # Rebuild column order:
        # 1. Original columns (keep their order)
        # 2. Extracted columns first among new columns
        # 3. Other new columns
        new_order = original_columns + extracted_cols + other_new_cols
        
        # Filter out any columns that don't exist and reorder
        new_order = [col for col in new_order if col in current_columns]
        self.df = self.df[new_order]

    def run_all_comparisons(self):
        if not self.column_pairs:
            print("No pairs selected.")
            return

        # Store original columns before adding new ones
        original_columns = self.df.columns.tolist()

        for gt_col, llm_col in self.column_pairs:
            print(f"\nProcessing pair: GT='{gt_col}', LLM='{llm_col}'")
            base_name = f"{llm_col}_vs_{gt_col}"
            
            report_col = f"{base_name}_report"; overall_pass_col = f"{base_name}_overall_pass"
            alert_pass_col = f"{base_name}_alert_pass"; other_pass_col = f"{base_name}_other_pass"
            extracted_llm_col = f"{llm_col}_extracted_json"; extracted_gt_col = f"{gt_col}_extracted_json"

            results = []
            for _, row in tqdm(self.df.iterrows(), total=len(self.df), desc=f"Comparing {llm_col}"):
                gt_val, llm_val = row.get(gt_col, ""), row.get(llm_col, "")
                report, alert_p, other_p, overall_p, ext_llm, ext_gt = generate_evaluation_report(str(llm_val), str(gt_val))
                results.append({
                    report_col: report, overall_pass_col: overall_p, alert_pass_col: alert_p,
                    other_pass_col: other_p, extracted_llm_col: ext_llm, extracted_gt_col: ext_gt,
                })
            
            results_df = pd.DataFrame(results, index=self.df.index)
            self.df = pd.concat([self.df, results_df], axis=1)

            # Reorder extracted columns to be first among newly added columns
            self.reorder_extracted_columns_among_new(gt_col, llm_col, original_columns)

            # Calculate overall and split statistics for this pair
            total_rows = len(self.df)
            overall_pass_count = int(self.df[overall_pass_col].sum())
            alert_pass_count = int(self.df[alert_pass_col].sum())
            other_pass_count = int(self.df[other_pass_col].sum())
            
            # User-driven split logic
            if self.split_mode == 'full':
                # No splitting - use full dataset
                self.summary_stats[base_name] = {
                    "total_rows": total_rows,
                    "overall_pass": {
                        "count": overall_pass_count, 
                        "rate": f"{(overall_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%"
                    },
                    "alert_pass": {
                        "count": alert_pass_count, 
                        "rate": f"{(alert_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%"
                    },
                    "other_fields_pass": {
                        "count": other_pass_count, 
                        "rate": f"{(other_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%"
                    }
                }
            elif self.split_mode == 'half':
                # Use original half split
                overall_half_stats = self.calculate_half_statistics(self.df[overall_pass_col], total_rows)
                alert_half_stats = self.calculate_half_statistics(self.df[alert_pass_col], total_rows)
                other_half_stats = self.calculate_half_statistics(self.df[other_pass_col], total_rows)

                self.summary_stats[base_name] = {
                    "total_rows": total_rows,
                    "overall_pass": {
                        "count": overall_pass_count, 
                        "rate": f"{(overall_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%",
                        "first_half": overall_half_stats["first_half"],
                        "second_half": overall_half_stats["second_half"]
                    },
                    "alert_pass": {
                        "count": alert_pass_count, 
                        "rate": f"{(alert_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%",
                        "first_half": alert_half_stats["first_half"],
                        "second_half": alert_half_stats["second_half"]
                    },
                    "other_fields_pass": {
                        "count": other_pass_count, 
                        "rate": f"{(other_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%",
                        "first_half": other_half_stats["first_half"],
                        "second_half": other_half_stats["second_half"]
                    }
                }
            elif self.split_mode == 'quadrant':
                # Use quadrant split
                overall_quadrant_stats = self.calculate_quadrant_statistics(self.df[overall_pass_col], total_rows)
                alert_quadrant_stats = self.calculate_quadrant_statistics(self.df[alert_pass_col], total_rows)
                other_quadrant_stats = self.calculate_quadrant_statistics(self.df[other_pass_col], total_rows)

                self.summary_stats[base_name] = {
                    "total_rows": total_rows,
                    "overall_pass": {
                        "count": overall_pass_count, 
                        "rate": f"{(overall_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%",
                        "first_quarter_fraud_transactions": overall_quadrant_stats["first_quarter_fraud_transactions"],
                        "second_quarter_fraud_transactions": overall_quadrant_stats["second_quarter_fraud_transactions"],
                        "third_quarter_all_transactions": overall_quadrant_stats["third_quarter_all_transactions"],
                        "fourth_quarter_all_transactions": overall_quadrant_stats["fourth_quarter_all_transactions"]
                    },
                    "alert_pass": {
                        "count": alert_pass_count, 
                        "rate": f"{(alert_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%",
                        "first_quarter_fraud_transactions": alert_quadrant_stats["first_quarter_fraud_transactions"],
                        "second_quarter_fraud_transactions": alert_quadrant_stats["second_quarter_fraud_transactions"],
                        "third_quarter_all_transactions": alert_quadrant_stats["third_quarter_all_transactions"],
                        "fourth_quarter_all_transactions": alert_quadrant_stats["fourth_quarter_all_transactions"]
                    },
                    "other_fields_pass": {
                        "count": other_pass_count, 
                        "rate": f"{(other_pass_count / total_rows * 100):.2f}%" if total_rows > 0 else "0.00%",
                        "first_quarter_fraud_transactions": other_quadrant_stats["first_quarter_fraud_transactions"],
                        "second_quarter_fraud_transactions": other_quadrant_stats["second_quarter_fraud_transactions"],
                        "third_quarter_all_transactions": other_quadrant_stats["third_quarter_all_transactions"],
                        "fourth_quarter_all_transactions": other_quadrant_stats["fourth_quarter_all_transactions"]
                    }
                }
            else:
                raise ValueError("split_mode must be 'full', 'half' or 'quadrant'.")

    def display_and_save_summary(self, summary_path, log_path="results.txt"):
        """Prints a formatted summary to the console and saves it to a JSON file and results.txt."""

        # Save the original sys.stdout
        original_stdout = sys.stdout
        buffer = StringIO()

        try:
            # Redirect sys.stdout to the buffer
            sys.stdout = buffer

            print("\n" + "="*25 + " FINAL EVALUATION SUMMARY " + "="*25)
            if not self.summary_stats:
                print("No statistics were generated.")
                return

            half_keys = ["first_half", "second_half"]

            for pair_name, stats in self.summary_stats.items():
                print(f"\n📊 Results for: {pair_name}")
                print(f"  - Overall Pass Rate:      {stats['overall_pass']['count']}/{stats['total_rows']} ({stats['overall_pass']['rate']})")
                overall = stats['overall_pass']
                alert = stats['alert_pass']
                other = stats['other_fields_pass']

                if self.split_mode == 'full':
                    pass

                elif all(key in overall for key in half_keys):
                    print(f"    • First Half:           {overall['first_half']['count']}/{overall['first_half']['total']} ({overall['first_half']['rate']})")
                    print(f"    • Second Half:          {overall['second_half']['count']}/{overall['second_half']['total']} ({overall['second_half']['rate']})")
                else:
                    for label, key in [
                        ("First Quarter (Fraud)", "first_quarter_fraud_transactions"),
                        ("Second Quarter (Fraud)", "second_quarter_fraud_transactions"),
                        ("Third Quarter (All)", "third_quarter_all_transactions"),
                        ("Fourth Quarter (All)", "fourth_quarter_all_transactions"),
                    ]:
                        if key in overall:
                            q = overall[key]
                            print(f"    • {label}:   {q['count']}/{q['total']} ({q['rate']})")

                print(f"  - Alert Transactions Pass: {alert['count']}/{stats['total_rows']} ({alert['rate']})")
                if all(key in alert for key in half_keys):
                    print(f"    • First Half:           {alert['first_half']['count']}/{alert['first_half']['total']} ({alert['first_half']['rate']})")
                    print(f"    • Second Half:          {alert['second_half']['count']}/{alert['second_half']['total']} ({alert['second_half']['rate']})")
                else:
                    for label, key in [
                        ("First Quarter (Fraud)", "first_quarter_fraud_transactions"),
                        ("Second Quarter (Fraud)", "second_quarter_fraud_transactions"),
                        ("Third Quarter (All)", "third_quarter_all_transactions"),
                        ("Fourth Quarter (All)", "fourth_quarter_all_transactions"),
                    ]:
                        if key in alert:
                            q = alert[key]
                            print(f"    • {label}:   {q['count']}/{q['total']} ({q['rate']})")

                print(f"  - Other Fields Pass:      {other['count']}/{stats['total_rows']} ({other['rate']})")
                if all(key in other for key in half_keys):
                    print(f"    • First Half:           {other['first_half']['count']}/{other['first_half']['total']} ({other['first_half']['rate']})")
                    print(f"    • Second Half:          {other['second_half']['count']}/{other['second_half']['total']} ({other['second_half']['rate']})")
                else:
                    for label, key in [
                        ("First Quarter (Fraud)", "first_quarter_fraud_transactions"),
                        ("Second Quarter (Fraud)", "second_quarter_fraud_transactions"),
                        ("Third Quarter (All)", "third_quarter_all_transactions"),
                        ("Fourth Quarter (All)", "fourth_quarter_all_transactions"),
                    ]:
                        if key in other:
                            q = other[key]
                            print(f"    • {label}:   {q['count']}/{q['total']} ({q['rate']})")

            try:
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump(self.summary_stats, f, indent=2)
                print("\n" + "="*70)
                print(f"✅ Summary statistics successfully saved to: {summary_path}")
            except Exception as e:
                print(f"\n❌ Error saving summary JSON: {e}")

            # Restore sys.stdout and print the buffer content to the real console
            sys.stdout = original_stdout
            output = buffer.getvalue()
            print(output, end='')

            # Save the buffer content to results.txt
            with open(log_path, 'w', encoding='utf-8') as log_file:
                log_file.write(output)

        finally:
            sys.stdout = original_stdout
            buffer.close()

    def save_results_csv(self, output_path):
        """Saves the main DataFrame with all details to a CSV file."""
        try:
            self.df.to_csv(output_path, index=False, encoding='utf-8-sig')
            print(f"✅ Detailed evaluation results saved to: {output_path}")
        except Exception as e:
            print(f"\n❌ Error saving results CSV: {e}")

class TestEvaluationScript(unittest.TestCase):
    def test_summary_generation(self):
        csv_data = StringIO('Ground Truth,job_test\n"{\\"bank\\":\\"boc\\"}","{\\"bank\\":\\"bank of china\\"}"\n"{\\"id\\":1}","{\\"id\\":2}"\n"{\\"id\\":3}","{\\"id\\":3}"\n"{\\"id\\":4}","{\\"id\\":4}"')
        comparator = CSVMultiColumnComparator(csv_data)
        comparator.column_pairs.append(('Ground Truth', 'job_test'))
        comparator.run_all_comparisons()
        self.assertIn('job_test_vs_Ground Truth', comparator.summary_stats)
        self.assertEqual(comparator.summary_stats['job_test_vs_Ground Truth']['total_rows'], 4)

def main():
    if 'unittest' in sys.argv:
        unittest.main(argv=sys.argv[:1], exit=False)
        return
    file_path = sys.argv[1] if len(sys.argv) > 1 else input("Enter path to CSV file: ")
    # Prompt user for split mode
    split_mode = input("Choose split mode ('full', 'half', or 'quadrant') [full]: ").strip().lower() or 'full'
    if split_mode not in ('full', 'half', 'quadrant'):
        print("Invalid split mode. Please enter 'full', 'half', or 'quadrant'.")
        sys.exit(1)
    
    comparator = CSVMultiColumnComparator(file_path, split_mode=split_mode)
    
    # Try automatic column selection first
    if not comparator.auto_select_column_pairs():
        print("\n⚠️  Automatic column selection failed. Falling back to manual selection.")
        comparator.select_column_pairs()
    
    comparator.run_all_comparisons()
    if comparator.column_pairs:
        base_name = os.path.splitext(file_path)[0]
        # Save the detailed CSV
        output_csv_file = f"{base_name}_evaluated.csv"
        comparator.save_results_csv(output_csv_file)
        # Save the summary JSON
        output_summary_file = f"{base_name}_summary.json"
        comparator.display_and_save_summary(output_summary_file)

if __name__ == "__main__":
    main()

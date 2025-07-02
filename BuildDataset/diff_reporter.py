import re
from typing import Dict, List, Tuple

class DiffReporter:
    def __init__(self, mappings: Dict[str, str], field_types: Dict[str, str]):
        self.mappings = mappings
        self.field_types = field_types
    
    def get_original_values(self) -> str:
        """Get all original values (left side) separated by newline"""
        if not self.mappings:
            return ""
        
        original_values = list(self.mappings.keys())
        return "\n".join(original_values)

    def get_replacement_values(self) -> str:
        """Get all replacement values (right side) separated by newline"""
        if not self.mappings:
            return ""
        
        replacement_values = list(self.mappings.values())
        return "\n".join(replacement_values)
    
    def generate_replacement_summary(self, original_input: str, original_transactions: str, original_ground_truth: str) -> str:
        """Generate MERGED detailed summary with counts and locations"""
        if not self.mappings:
            return "No replacements made"
        
        summary_lines = []
        summary_lines.append("REPLACEMENT SUMMARY")
        summary_lines.append("=" * 50)
        summary_lines.append(f"Total replacements: {len(self.mappings)}")
        summary_lines.append("")
        
        total_input = 0
        total_transactions = 0
        total_ground_truth = 0
        
        # Group by field types from field_mapper
        field_groups = {}
        for old_val, new_val in self.mappings.items():
            field_type = self.field_types.get(old_val, 'unknown')
            if field_type not in field_groups:
                field_groups[field_type] = []
            field_groups[field_type].append((old_val, new_val))
        
        # Show each field type separately with detailed locations
        for field_type, replacements in field_groups.items():
            if replacements:
                summary_lines.append(f"{field_type.upper().replace('_', ' ')} ({len(replacements)} items):")
                summary_lines.append("-" * 30)
                
                for old_val, new_val in replacements:
                    # Count locations for each replacement
                    locations = []
                    
                    # Count in Input
                    if old_val in original_input:
                        input_count = original_input.count(old_val)
                        total_input += input_count
                        locations.append(f"Input({input_count})")
                    
                    # Count in Transactions
                    if old_val in original_transactions:
                        trans_count = original_transactions.count(old_val)
                        total_transactions += trans_count
                        locations.append(f"Transactions({trans_count})")
                    
                    # Count in Ground Truth
                    if old_val in original_ground_truth:
                        gt_count = original_ground_truth.count(old_val)
                        total_ground_truth += gt_count
                        locations.append(f"Ground Truth({gt_count})")
                    
                    # Show replacement with locations
                    summary_lines.append(f"  {old_val} → {new_val}")
                    if locations:
                        location_str = " + ".join(locations)
                        summary_lines.append(f"    Found in: {location_str}")
                    else:
                        summary_lines.append(f"    Found in: NONE (phantom replacement)")
                    summary_lines.append("")  # Add spacing between items
                
                summary_lines.append("")  # Add spacing between field types
        
        # Summary totals at the end
        summary_lines.append("=" * 50)
        summary_lines.append("SUMMARY TOTALS:")
        summary_lines.append(f"Input: {total_input} total replacements")
        summary_lines.append(f"Transactions: {total_transactions} total replacements")
        summary_lines.append(f"Ground Truth: {total_ground_truth} total replacements")
        summary_lines.append(f"Grand Total: {total_input + total_transactions + total_ground_truth} replacements")
        
        return "\n".join(summary_lines)
    
    def generate_alerts(self, original_input: str, original_transactions: str, original_ground_truth: str, document_type: str = None) -> str:
        """Generate alerts based on where replacements were actually done"""
        alerts = []
        
        has_transactions = bool(original_transactions.strip())
        
        for old_value in self.mappings.keys():
            field_type = self.field_types.get(old_value, 'unknown')
            
            # Check where replacements were actually done
            found_in_input = old_value in original_input
            found_in_transactions = old_value in original_transactions  
            found_in_ground_truth = old_value in original_ground_truth
            
            # Build actual locations set
            actual_locations = set()
            if found_in_input:
                actual_locations.add("Input")
            if found_in_transactions:
                actual_locations.add("Transactions")
            if found_in_ground_truth:
                actual_locations.add("Ground Truth")
            
            # Determine expected locations based on field type and rules
            if field_type in ['police_references', 'contact_persons', 'writ_numbers', 'cancel_amount_requested']:
                expected_locations = {"Input", "Ground Truth"}
                
            elif field_type in ['dates', 'amounts', 'names', 'account_numbers']:
                if not has_transactions:
                    expected_locations = {"Input", "Ground Truth"}
                else:
                    expected_locations = {"Input", "Transactions", "Ground Truth"}
                    
            elif field_type == 'banks':
                # Banks follow same rules as transaction fields, but only for ADCC and Police Letter
                if document_type in ['ADCC', 'Police Letter']:
                    if not has_transactions:
                        expected_locations = {"Input", "Ground Truth"}
                    else:
                        expected_locations = {"Input", "Transactions", "Ground Truth"}
                else:
                    # For other document types, banks should not be randomized, so skip alerting
                    continue
                    
            # REMOVED: police_teams from alert logic since they're not randomized
                    
            else:
                # Only truly unknown field types
                alerts.append(f"⚠️  UNKNOWN FIELD TYPE: {field_type} for value '{old_value}'")
                alerts.append(f"   This field type is not handled by the alert system")
                alerts.append("")
                continue
            
            # Alert if actual doesn't match expected
            if actual_locations != expected_locations:
                alerts.append(f"⚠️  {field_type.upper()}: {old_value}")
                alerts.append(f"   Expected: {' + '.join(sorted(expected_locations))}")
                alerts.append(f"   Actually found in: {' + '.join(sorted(actual_locations)) if actual_locations else 'NONE'}")
                
                missing = expected_locations - actual_locations
                extra = actual_locations - expected_locations
                if missing:
                    alerts.append(f"   Missing from: {' + '.join(sorted(missing))}")
                if extra:
                    alerts.append(f"   Unexpected in: {' + '.join(sorted(extra))}")
                alerts.append("")
        
        # Return blank if no alerts, otherwise return with header
        if not alerts:
            return ""
        else:
            header = ["REPLACEMENT ALERTS", "=" * 30, ""]
            return "\n".join(header + alerts)

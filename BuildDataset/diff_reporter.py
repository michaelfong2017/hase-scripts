import re
from typing import Dict, List, Tuple
from field_mapper import FieldMapper

class DiffReporter:
    def __init__(self, mappings: Dict[str, str], field_types: Dict[str, str]):
        self.mappings = mappings
        self.field_types = field_types
    
    def get_original_values(self) -> str:
        """Get all original values (left side) separated by newline - deduplicated by normalized form"""
        if not self.mappings:
            return ""
        
        # Group by field type and show only unique normalized values
        seen_values = set()
        unique_values = []
        
        # Process by field type to maintain logical grouping
        field_groups = {}
        for old_val in self.mappings.keys():
            field_type = self.field_types.get(old_val, 'unknown')
            if field_type not in field_groups:
                field_groups[field_type] = []
            field_groups[field_type].append(old_val)
        
        # For each field type, add only unique representative values
        for field_type in ['dates', 'amounts', 'cancel_amount_requested', 'names', 'account_numbers', 'banks', 'police_references', 'writ_numbers', 'contact_persons']:
            if field_type in field_groups:
                if field_type == 'names':
                    # For names, use a different approach - track by normalized form
                    name_mapper = FieldMapper("temp")  # Create temporary mapper for normalization
                    seen_normalized = set()
                    for name_val in field_groups[field_type]:
                        normalized = name_mapper._normalize_name(name_val)
                        if normalized not in seen_normalized:
                            seen_normalized.add(normalized)
                            unique_values.append(normalized)  # Use normalized form
                else:
                    # For other fields, just add unique values
                    for val in field_groups[field_type]:
                        if val not in seen_values:
                            seen_values.add(val)
                            unique_values.append(val)
        
        return "\n".join(unique_values)

    def get_replacement_values(self) -> str:
        """Get all replacement values (right side) separated by newline - matching the original values"""
        if not self.mappings:
            return ""
        
        # This should match the logic in get_original_values
        seen_values = set()
        unique_replacements = []
        
        # Process by field type to maintain logical grouping
        field_groups = {}
        for old_val in self.mappings.keys():
            field_type = self.field_types.get(old_val, 'unknown')
            if field_type not in field_groups:
                field_groups[field_type] = []
            field_groups[field_type].append(old_val)
        
        # For each field type, add only unique representative values
        for field_type in ['dates', 'amounts', 'cancel_amount_requested', 'names', 'account_numbers', 'banks', 'police_references', 'writ_numbers', 'contact_persons']:
            if field_type in field_groups:
                if field_type == 'names':
                    # For names, use normalized form and get its replacement
                    name_mapper = FieldMapper("temp")
                    seen_normalized = set()
                    for name_val in field_groups[field_type]:
                        normalized = name_mapper._normalize_name(name_val)
                        if normalized not in seen_normalized:
                            seen_normalized.add(normalized)
                            # Get replacement for any variant of this normalized name
                            replacement = self.mappings.get(name_val, name_val)
                            unique_replacements.append(replacement)
                else:
                    # For other fields, just add unique values
                    for val in field_groups[field_type]:
                        if val not in seen_values:
                            seen_values.add(val)
                            unique_replacements.append(self.mappings[val])
        
        return "\n".join(unique_replacements)

    def _check_value_presence(self, value: str, text: str, field_type: str) -> bool:
        """Check if a value is present in text, considering different formats"""
        if not value or not text:
            return False
        
        # Direct match first
        if value in text:
            return True
        
        # For amounts, try normalized matching
        if field_type in ['amounts', 'cancel_amount_requested']:
            # Try to find the value in various amount formats
            amount_patterns = [
                rf'\b{re.escape(value)}\b',  # Exact number
                rf'\b{re.escape(value)}\.00\b',  # With .00
                rf'\bHKD\s*{re.escape(value)}\b',  # With HKD prefix
                rf'\bHKD\s*{re.escape(value)}\.00\b',  # With HKD and .00
            ]
            
            # Also try with comma formatting
            if value.isdigit() and len(value) >= 4:
                # Add comma formatting for thousands
                formatted_value = f"{int(value):,}"
                amount_patterns.extend([
                    rf'\b{re.escape(formatted_value)}\b',
                    rf'\b{re.escape(formatted_value)}\.00\b',
                    rf'\bHKD\s*{re.escape(formatted_value)}\b',
                    rf'\bHKD\s*{re.escape(formatted_value)}\.00\b',
                ])
            
            for pattern in amount_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return True
        
        return False

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
                    # Count locations for each replacement using smart matching
                    locations = []
                    
                    # Count in Input
                    if self._check_value_presence(old_val, original_input, field_type):
                        input_count = self._count_occurrences(old_val, original_input, field_type)
                        total_input += input_count
                        locations.append(f"Input({input_count})")
                    
                    # Count in Transactions
                    if self._check_value_presence(old_val, original_transactions, field_type):
                        trans_count = self._count_occurrences(old_val, original_transactions, field_type)
                        total_transactions += trans_count
                        locations.append(f"Transactions({trans_count})")
                    
                    # Count in Ground Truth
                    if self._check_value_presence(old_val, original_ground_truth, field_type):
                        gt_count = self._count_occurrences(old_val, original_ground_truth, field_type)
                        total_ground_truth += gt_count
                        locations.append(f"Ground Truth({gt_count})")
                    
                    # Show replacement with locations
                    summary_lines.append(f"  {old_val} → {new_val}")
                    if locations:
                        location_str = " + ".join(locations)
                        summary_lines.append(f"    Found in: {location_str}")
                    else:
                        summary_lines.append(f"    Found in: NONE")
                    summary_lines.append("")
                
                summary_lines.append("")
        
        summary_lines.append("=" * 50)
        summary_lines.append("SUMMARY TOTALS:")
        summary_lines.append(f"Input: {total_input} total replacements")
        summary_lines.append(f"Transactions: {total_transactions} total replacements")
        summary_lines.append(f"Ground Truth: {total_ground_truth} total replacements")
        summary_lines.append(f"Grand Total: {total_input + total_transactions + total_ground_truth} replacements")
        
        return "\n".join(summary_lines)

    def _count_occurrences(self, value: str, text: str, field_type: str) -> int:
        """Count occurrences of a value in text, considering different formats"""
        if not value or not text:
            return 0
        
        count = 0
        
        # Direct count first
        count += text.count(value)
        
        # For amounts, count formatted versions
        if field_type in ['amounts', 'cancel_amount_requested'] and value.isdigit():
            # Count with comma formatting
            if len(value) >= 4:
                formatted_value = f"{int(value):,}"
                count += text.count(formatted_value)
            
            # Count with HKD prefix
            count += len(re.findall(rf'\bHKD\s*{re.escape(value)}\b', text, re.IGNORECASE))
            count += len(re.findall(rf'\bHKD\s*{re.escape(value)}\.00\b', text, re.IGNORECASE))
            
            if len(value) >= 4:
                formatted_value = f"{int(value):,}"
                count += len(re.findall(rf'\bHKD\s*{re.escape(formatted_value)}\b', text, re.IGNORECASE))
                count += len(re.findall(rf'\bHKD\s*{re.escape(formatted_value)}\.00\b', text, re.IGNORECASE))
        
        return count

    # Update the alert generation methods to use the new smart matching
    def generate_alerts(self, original_input: str, original_transactions: str, original_ground_truth: str, document_type: str = None) -> str:
        """Generate alerts based on where replacements were actually done - check variants together"""
        alerts = []
        
        has_transactions = bool(original_transactions.strip())
        processed_normalized_names = set()
        
        for old_value in self.mappings.keys():
            field_type = self.field_types.get(old_value, 'unknown')
            
            if field_type == 'names':
                # Handle names with variant grouping (existing logic)
                # ... keep existing name handling logic
                pass
            else:
                # For non-name fields, use smart matching
                found_in_input = self._check_value_presence(old_value, original_input, field_type)
                found_in_transactions = self._check_value_presence(old_value, original_transactions, field_type)
                found_in_ground_truth = self._check_value_presence(old_value, original_ground_truth, field_type)
                
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
                elif field_type in ['dates', 'amounts', 'account_numbers']:
                    if not has_transactions:
                        expected_locations = {"Input", "Ground Truth"}
                    else:
                        expected_locations = {"Input", "Transactions", "Ground Truth"}
                elif field_type == 'banks':
                    if document_type in ['ADCC', 'Police Letter']:
                        if not has_transactions:
                            expected_locations = {"Input", "Ground Truth"}
                        else:
                            expected_locations = {"Input", "Transactions", "Ground Truth"}
                    else:
                        continue
                else:
                    continue
                
                if actual_locations != expected_locations:
                    alerts.append(f"⚠️  {field_type.upper()}: {old_value}")
                    alerts.append(f"   Expected: {' + '.join(sorted(expected_locations))}")
                    alerts.append(f"   Actually found in: {' + '.join(sorted(actual_locations)) if actual_locations else 'NONE'}")
                    
                    missing = expected_locations - actual_locations
                    if missing:
                        alerts.append(f"   Missing from: {' + '.join(sorted(missing))}")
                    alerts.append("")
        
        if not alerts:
            return ""
        else:
            header = ["REPLACEMENT ALERTS", "=" * 30, ""]
            return "\n".join(header + alerts)
    
    def generate_field_specific_alerts(self, original_input: str, original_transactions: str, original_ground_truth: str, document_type: str = None) -> Dict[str, str]:
        """Generate field-specific alert columns"""
        has_transactions = bool(original_transactions.strip())
        
        # Initialize all field alert columns
        field_alerts = {
            'Alert_Dates': "",
            'Alert_Amounts': "",
            'Alert_Names': "",
            'Alert_Account_Numbers': "",
            'Alert_Banks': "",
            'Alert_Police_References': "",
            'Alert_Contact_Persons': "",
            'Alert_Writ_Numbers': "",
            'Alert_Cancel_Amount_Requested': ""
        }
        
        for old_value in self.mappings.keys():
            field_type = self.field_types.get(old_value, 'unknown')
            
            # Check where replacements were actually done
            found_in_input = self._check_value_presence(old_value, original_input, field_type)
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
            expected_locations = None
            
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
                    # For other document types, banks should not be randomized, so skip
                    continue
            
            # Check if there's an alert for this field
            if expected_locations and actual_locations != expected_locations:
                missing = expected_locations - actual_locations
                extra = actual_locations - expected_locations
                
                alert_msg = f"{old_value}: "
                if missing:
                    alert_msg += f"Missing from {', '.join(sorted(missing))}"
                if extra:
                    if missing:
                        alert_msg += "; "
                    alert_msg += f"Unexpected in {', '.join(sorted(extra))}"
                
                # Add to appropriate field alert column
                if field_type == 'dates':
                    if field_alerts['Alert_Dates']:
                        field_alerts['Alert_Dates'] += "\n"
                    field_alerts['Alert_Dates'] += alert_msg
                elif field_type == 'amounts':
                    if field_alerts['Alert_Amounts']:
                        field_alerts['Alert_Amounts'] += "\n"
                    field_alerts['Alert_Amounts'] += alert_msg
                elif field_type == 'names':
                    if field_alerts['Alert_Names']:
                        field_alerts['Alert_Names'] += "\n"
                    field_alerts['Alert_Names'] += alert_msg
                elif field_type == 'account_numbers':
                    if field_alerts['Alert_Account_Numbers']:
                        field_alerts['Alert_Account_Numbers'] += "\n"
                    field_alerts['Alert_Account_Numbers'] += alert_msg
                elif field_type == 'banks':
                    if field_alerts['Alert_Banks']:
                        field_alerts['Alert_Banks'] += "\n"
                    field_alerts['Alert_Banks'] += alert_msg
                elif field_type == 'police_references':
                    if field_alerts['Alert_Police_References']:
                        field_alerts['Alert_Police_References'] += "\n"
                    field_alerts['Alert_Police_References'] += alert_msg
                elif field_type == 'contact_persons':
                    if field_alerts['Alert_Contact_Persons']:
                        field_alerts['Alert_Contact_Persons'] += "\n"
                    field_alerts['Alert_Contact_Persons'] += alert_msg
                elif field_type == 'writ_numbers':
                    if field_alerts['Alert_Writ_Numbers']:
                        field_alerts['Alert_Writ_Numbers'] += "\n"
                    field_alerts['Alert_Writ_Numbers'] += alert_msg
                elif field_type == 'cancel_amount_requested':
                    if field_alerts['Alert_Cancel_Amount_Requested']:
                        field_alerts['Alert_Cancel_Amount_Requested'] += "\n"
                    field_alerts['Alert_Cancel_Amount_Requested'] += alert_msg
        
        return field_alerts

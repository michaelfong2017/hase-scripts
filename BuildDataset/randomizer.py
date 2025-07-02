import pandas as pd
import json
import random
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from pattern import *

# Global set number tracker
global_set_number = 0

def initialize_global_set_number(df):
    global global_set_number
    if 'Set Number' in df.columns:
        global_set_number = df['Set Number'].max()
    else:
        global_set_number = 0
    print(f"Initialized global set number to: {global_set_number}")

def get_next_set_number():
    global global_set_number
    global_set_number += 1
    return global_set_number

def randomize_date_with_format_preservation(original_date: str, format_mappings: Dict[str, str]) -> Tuple[str, Dict[str, str]]:
    """Randomize date while preserving all formats found in text"""
    try:
        # Try to parse with different formats
        parsed_date = None
        original_format = None
        
        for pattern, fmt in DATE_FORMAT_PATTERNS:
            match = re.match(pattern, original_date)
            if match:
                if fmt == '%Y-%m-%d':
                    parsed_date = datetime.strptime(original_date, fmt)
                elif fmt == '%m/%d/%Y':
                    parsed_date = datetime.strptime(original_date, fmt)
                elif fmt == '%m-%d-%Y':
                    parsed_date = datetime.strptime(original_date, fmt)
                original_format = fmt
                break
        
        if not parsed_date:
            raise ValueError("Unknown date format")
        
        # Generate random offset
        random_offset = random.randint(-365, 365)
        new_date = parsed_date + timedelta(days=random_offset)
        
        # Create mappings for all possible formats of this date
        new_mappings = {}
        
        # Generate all format variations for both original and new dates
        formats = [
            ('%Y-%m-%d', r'\b\d{4}-\d{2}-\d{2}\b'),
            ('%m/%d/%Y', r'\b\d{1,2}/\d{1,2}/\d{4}\b'),
            ('%m-%d-%Y', r'\b\d{1,2}-\d{1,2}-\d{4}\b'),
        ]
        
        for fmt, pattern in formats:
            original_formatted = parsed_date.strftime(fmt)
            new_formatted = new_date.strftime(fmt)
            new_mappings[original_formatted] = new_formatted
        
        return new_date.strftime(original_format), new_mappings
        
    except:
        # Fallback
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2025, 12, 31)
        random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
        return random_date.strftime("%Y-%m-%d"), {original_date: random_date.strftime("%Y-%m-%d")}

def randomize_amount_with_format_preservation(original_amount: str, upper_limit: float = None) -> Tuple[str, Dict[str, str]]:
    """Randomize amount while preserving all formats found in text"""
    try:
        mappings = {}
        
        # Try different amount patterns
        for pattern, format_type in AMOUNT_FORMAT_PATTERNS:
            match = re.match(pattern, original_amount)
            if match:
                if format_type == 'currency_prefix':
                    currency = match.group(1)
                    amount_str = match.group(2).replace(',', '')
                    original_value = float(amount_str)
                    
                    # Calculate new value
                    if upper_limit is not None:
                        min_value = original_value * 0.5
                        max_value = min(original_value * 1.5, upper_limit - 0.01)
                        if min_value >= upper_limit:
                            min_value = upper_limit * 0.1
                            max_value = upper_limit - 0.01
                        if max_value <= min_value:
                            max_value = min_value + 1
                        new_value = random.uniform(min_value, max_value)
                    else:
                        variation = random.uniform(0.5, 1.5)
                        new_value = original_value * variation
                    
                    # Create format mappings
                    new_formatted = f"{currency}{new_value:.2f}"
                    new_formatted_with_commas = f"{currency}{new_value:,.2f}"
                    
                    mappings[original_amount] = new_formatted
                    mappings[f"{currency}{original_value:,.2f}"] = new_formatted_with_commas
                    mappings[f"{currency}{int(original_value):,}"] = f"{currency}{int(new_value):,}"
                    mappings[str(int(original_value))] = str(int(new_value))
                    mappings[f"{original_value:.2f}"] = f"{new_value:.2f}"
                    
                    return new_formatted, mappings
                    
                elif format_type == 'dollar_prefix':
                    currency = match.group(1)
                    amount_str = match.group(2).replace(',', '')
                    original_value = float(amount_str)
                    
                    if upper_limit is not None:
                        min_value = original_value * 0.5
                        max_value = min(original_value * 1.5, upper_limit - 0.01)
                        if min_value >= upper_limit:
                            min_value = upper_limit * 0.1
                            max_value = upper_limit - 0.01
                        if max_value <= min_value:
                            max_value = min_value + 1
                        new_value = random.uniform(min_value, max_value)
                    else:
                        variation = random.uniform(0.5, 1.5)
                        new_value = original_value * variation
                    
                    new_formatted = f"{currency}{new_value:.2f}"
                    mappings[original_amount] = new_formatted
                    
                    return new_formatted, mappings
                    
                elif format_type == 'currency_suffix':
                    amount_str = match.group(1).replace(',', '')
                    currency = match.group(2)
                    original_value = float(amount_str)
                    
                    if upper_limit is not None:
                        min_value = original_value * 0.5
                        max_value = min(original_value * 1.5, upper_limit - 0.01)
                        if min_value >= upper_limit:
                            min_value = upper_limit * 0.1
                            max_value = upper_limit - 0.01
                        if max_value <= min_value:
                            max_value = min_value + 1
                        new_value = random.uniform(min_value, max_value)
                    else:
                        variation = random.uniform(0.5, 1.5)
                        new_value = original_value * variation
                    
                    new_formatted = f"{new_value:.2f} {currency}"
                    mappings[original_amount] = new_formatted
                    
                    return new_formatted, mappings
        
        # Fallback
        random_amount = random.uniform(1000, 100000)
        return f"HKD{random_amount:.2f}", {original_amount: f"HKD{random_amount:.2f}"}
        
    except:
        random_amount = random.uniform(1000, 100000)
        return f"HKD{random_amount:.2f}", {original_amount: f"HKD{random_amount:.2f}"}

def randomize_account_number(original_account: str) -> str:
    """Randomize account number preserving format"""
    try:
        if re.match(r'\d{3}-\d{6}-\d{3}', original_account):
            return f"{random.randint(100, 999)}-{random.randint(100000, 999999)}-{random.randint(100, 999)}"
        elif re.match(r'\d{10,16}', original_account):
            length = len(original_account)
            return ''.join([str(random.randint(0, 9)) for _ in range(length)])
        elif re.match(r'[A-Z]{2}\d+', original_account):
            bank_code = original_account[:2]
            digit_part = original_account[2:]
            new_digits = ''.join([str(random.randint(0, 9)) for _ in range(len(digit_part))])
            return f"{bank_code}{new_digits}"
        else:
            return re.sub(r'\d', lambda x: str(random.randint(0, 9)), original_account)
    except:
        return f"{random.randint(100, 999)}-{random.randint(100000, 999999)}-{random.randint(100, 999)}"

def replace_placeholders(template: str) -> str:
    result = template
    for placeholder, func in PLACEHOLDER_FUNCTIONS.items():
        result = result.replace(placeholder, func())
    return result

def randomize_police_reference(original_ref: Any) -> Any:
    if original_ref is None:
        return None
    template = random.choice(REPLACEMENT_OPTIONS['police_references'])
    return replace_placeholders(template)

def randomize_police_team(original_team: Any) -> Any:
    if original_team is None:
        return None
    template = random.choice(REPLACEMENT_OPTIONS['police_teams'])
    return replace_placeholders(template)

def randomize_writ_no(original_writ: Any) -> Any:
    if original_writ is None:
        return None
    template = random.choice(REPLACEMENT_OPTIONS['writ_numbers'])
    return replace_placeholders(template)

def randomize_contact_person(original_contact: Any) -> Any:
    if original_contact is None:
        return None
    template = random.choice(REPLACEMENT_OPTIONS['contact_persons'])
    return replace_placeholders(template)

def randomize_bank(original_bank: Any, document_type: str = None) -> Tuple[Any, str]:
    """Randomize bank using the mapping system"""
    if original_bank is None or original_bank == "":
        return original_bank, None
    
    if document_type not in BANK_RANDOMIZATION_TYPES:
        return original_bank, None
    
    # Find the root of the original bank
    original_root = find_bank_root(original_bank)
    
    # Get a different random bank root
    new_root = get_random_bank_root(exclude_root=original_root)
    
    if new_root and new_root in BANK_ROOT_TO_FULL_NAME:
        return BANK_ROOT_TO_FULL_NAME[new_root], new_root
    
    # Fallback to original selection if mapping fails
    selected_bank = random.choice(list(BANK_ROOT_TO_FULL_NAME.values()))
    return selected_bank, None

def randomize_name(original_name: Any) -> Tuple[Any, List[Tuple[str, str]], bool]:
    if original_name is None:
        return None, [], True
    
    if not re.match(NAME_VALIDATION_PATTERN, str(original_name)):
        return original_name, [], False
    
    selected_name = random.choice(REPLACEMENT_OPTIONS['names'])
    
    original_parts = str(original_name).split()
    new_parts = selected_name.split()
    
    part_changes = []
    for i in range(min(len(original_parts), len(new_parts))):
        part_changes.append((original_parts[i], new_parts[i]))
        
    return selected_name, part_changes, True

def randomize_json_fields(json_data: Dict, changes: List[Tuple[str, str]], document_type: str = None, global_mappings: Dict[str, str] = None) -> Dict:
    """Recursively randomize JSON fields with format preservation"""
    if global_mappings is None:
        global_mappings = {}

    # Handle ADCC special patterns first
    if document_type == 'ADCC':
        # Process the entire JSON string for special patterns
        json_str = json.dumps(json_data, ensure_ascii=False)
        adcc_changes = process_adcc_special_patterns(json_str, document_type)
        changes.extend(adcc_changes)
        
    if isinstance(json_data, dict):
        new_data = {}
        for key, value in json_data.items():
            # Skip excluded fields
            if key in EXCLUDED_FIELDS:
                new_data[key] = value
                continue
                
            if key == "date" and isinstance(value, str):
                new_value, date_mappings = randomize_date_with_format_preservation(value, global_mappings)
                global_mappings.update(date_mappings)
                if new_value != value:
                    changes.append((value, new_value))
                new_data[key] = new_value
                
            elif key == "amount" and isinstance(value, (str, int, float)):
                # Check for cancel_amount_requested constraint
                cancel_amount_limit = None
                if document_type in UAR_TYPES and "cancel_amount_requested" in json_data and json_data["cancel_amount_requested"] is not None:
                    try:
                        cancel_amount_limit = float(json_data["cancel_amount_requested"])
                    except (ValueError, TypeError):
                        cancel_amount_limit = None
                
                original_str = str(value)
                if isinstance(value, (int, float)):
                    new_value_str, amount_mappings = randomize_amount_with_format_preservation(f"HKD{value}", cancel_amount_limit)
                    global_mappings.update(amount_mappings)
                    
                    amount_match = re.search(r'[A-Z]{3}([0-9,]+\.?\d*)', new_value_str)
                    if amount_match:
                        formatted_new_amount = amount_match.group(1)
                        new_numeric_value = float(formatted_new_amount.replace(',', ''))
                        
                        if abs(new_numeric_value - value) > 1e-9:
                            changes.append((original_str, formatted_new_amount))
                        
                        new_data[key] = new_numeric_value
                    else:
                        new_data[key] = value
                else:
                    new_value, amount_mappings = randomize_amount_with_format_preservation(value, cancel_amount_limit)
                    global_mappings.update(amount_mappings)
                    
                    if new_value != value:
                        changes.append((value, new_value))
                    new_data[key] = new_value
                    
            elif key == "cancel_amount_requested" and document_type in UAR_TYPES and isinstance(value, (str, int, float)):
                # For UAR, ensure cancel_amount_requested <= amount
                amount_value = json_data.get("amount", 0)
                if isinstance(amount_value, (int, float)) and amount_value > 0:
                    # Set cancel_amount_requested to be between 50% and 100% of amount
                    min_cancel = amount_value * 0.5
                    max_cancel = amount_value
                    new_cancel_value = random.uniform(min_cancel, max_cancel)
                    
                    if isinstance(value, (int, float)):
                        new_data[key] = new_cancel_value
                        changes.append((str(value), str(new_cancel_value)))
                    else:
                        new_cancel_str = f"HKD{new_cancel_value:.2f}"
                        new_data[key] = new_cancel_str
                        changes.append((value, new_cancel_str))
                else:
                    new_data[key] = value
                    
            elif key == "account_number" and isinstance(value, str):
                new_value = randomize_account_number(value)
                if new_value != value:
                    changes.append((value, new_value))
                new_data[key] = new_value
                
            elif key == "police_reference":
                new_value = randomize_police_reference(value)
                if new_value != value:
                    changes.append((str(value), str(new_value)))
                new_data[key] = new_value
                
            elif key == "police_team":
                new_value = randomize_police_team(value)
                if new_value != value:
                    changes.append((str(value), str(new_value)))
                new_data[key] = new_value
                
            elif key == "writ_no":
                new_value = randomize_writ_no(value)
                if new_value != value:
                    changes.append((str(value), str(new_value)))
                new_data[key] = new_value
                
            elif key == "contact_person":
                new_value = randomize_contact_person(value)
                if new_value != value:
                    changes.append((str(value), str(new_value)))
                new_data[key] = new_value
                
            elif key == "bank" and isinstance(value, (str, type(None))):
                new_value, bank_code = randomize_bank(value, document_type)
                if new_value != value:
                    changes.append(("BANK:" + str(value), str(new_value)))
                new_data[key] = new_value
                
            elif key == "name" and isinstance(value, (str, type(None))):
                new_value, part_changes, was_randomized = randomize_name(value)
                if was_randomized:
                    if new_value != value:
                        changes.extend(part_changes)
                else:
                    changes.append((f"Name not randomized due to special characters: '{value}'", "SKIPPED"))
                new_data[key] = new_value
                
            elif key in ["from", "to"] and isinstance(value, dict):
                new_value = randomize_json_fields(value, changes, document_type, global_mappings)
                new_data[key] = new_value
                
            else:
                new_data[key] = randomize_json_fields(value, changes, document_type, global_mappings)
                
        return new_data
    elif isinstance(json_data, list):
        return [randomize_json_fields(item, changes, document_type, global_mappings) for item in json_data]
    else:
        return json_data

def apply_changes_to_input(input_text: str, changes: List[Tuple[str, str]], global_mappings: Dict[str, str] = None, document_type: str = None) -> str:
    """Apply changes to input text with enhanced search patterns and bank mapping"""
    modified_input = input_text

    # Handle ADCC special patterns first
    if document_type == 'ADCC':
        adcc_changes = process_adcc_special_patterns(input_text, document_type)
        modified_input = apply_adcc_special_replacements(modified_input, adcc_changes)
        # Add ADCC changes to the main changes list
        changes.extend(adcc_changes)
    
    # Apply global mappings first (for format preservation)
    if global_mappings:
        for old_format, new_format in sorted(global_mappings.items(), key=lambda x: len(x[0]), reverse=True):
            if old_format in modified_input:
                modified_input = modified_input.replace(old_format, new_format)
    
    # Then apply individual changes with enhanced search
    for old_value, new_value in changes:
        if new_value == "SKIPPED":
            continue
        
        if old_value.startswith("BANK:"):
            original_bank = old_value[5:]  # Remove "BANK:" prefix
            if not original_bank or original_bank.lower() == "none":
                continue
            
            # Use the bank mapping system to find what to replace
            bank_root = find_bank_root(original_bank)
            replacement_made = False
            
            if bank_root:
                # Get all variants for this bank root and try to replace them
                bank_variants_to_replace = [variant for variant, root in BANK_VARIANT_TO_ROOT.items() if root == bank_root]
                
                # Sort by length (longest first) to avoid partial replacements
                bank_variants_to_replace.sort(key=len, reverse=True)
                
                for variant in bank_variants_to_replace:
                    # Try exact case match first
                    if variant in modified_input:
                        modified_input = modified_input.replace(variant, new_value)
                        replacement_made = True
                        break
                    
                    # Try case-insensitive match
                    pattern = re.compile(re.escape(variant), re.IGNORECASE)
                    if pattern.search(modified_input):
                        modified_input = pattern.sub(new_value, modified_input)
                        replacement_made = True
                        break
                    
                    # Try word boundary match
                    try:
                        word_pattern = re.compile(r'\b' + re.escape(variant) + r'\b', re.IGNORECASE)
                        if word_pattern.search(modified_input):
                            modified_input = word_pattern.sub(new_value, modified_input)
                            replacement_made = True
                            break
                    except re.error:
                        pass
            
            # If mapping didn't work, try direct replacement of original bank
            if not replacement_made:
                # Try exact match
                if original_bank in modified_input:
                    modified_input = modified_input.replace(original_bank, new_value)
                    replacement_made = True
                else:
                    # Try case-insensitive
                    pattern = re.compile(re.escape(original_bank), re.IGNORECASE)
                    if pattern.search(modified_input):
                        modified_input = pattern.sub(new_value, modified_input)
                        replacement_made = True
                    else:
                        # Try word boundary
                        try:
                            word_pattern = re.compile(r'\b' + re.escape(original_bank) + r'\b', re.IGNORECASE)
                            if word_pattern.search(modified_input):
                                modified_input = word_pattern.sub(new_value, modified_input)
                                replacement_made = True
                        except re.error:
                            pass
            
            continue
            
        old_value_str = str(old_value)
        new_value_str = str(new_value)
        
        # Track if replacement happened
        replacement_made = False
        
        # Method 1: Try exact string replacement first
        if old_value_str in modified_input:
            modified_input = modified_input.replace(old_value_str, new_value_str)
            replacement_made = True
            continue
        
        # Method 2: Try numeric variations for amounts
        try:
            old_float = float(old_value_str)
            old_int = int(old_float)
            
            search_variations = [
                f"{old_int:,}.00",
                f"{old_int}.00", 
                f"{old_int:,}",
                str(old_int),
                str(old_float),
                f"{old_float:.2f}",
                f"{old_float:.1f}",
                f"{old_float:.0f}"
            ]
            
            search_variations = sorted(set(search_variations), key=len, reverse=True)
            
            for var in search_variations:
                if var in modified_input:
                    modified_input = modified_input.replace(var, new_value_str)
                    replacement_made = True
                    break
                else:
                    # Try with word boundaries
                    pattern = re.compile(r'\b' + re.escape(var) + r'\b')
                    if pattern.search(modified_input):
                        modified_input = pattern.sub(new_value_str, modified_input, count=1)
                        replacement_made = True
                        break
            
            if replacement_made:
                continue
                
        except (ValueError, TypeError):
            pass
        
        # Method 3: Try case-insensitive search
        if not replacement_made:
            if old_value_str.lower() in modified_input.lower():
                # Find the actual case in the text
                start_idx = modified_input.lower().find(old_value_str.lower())
                if start_idx != -1:
                    end_idx = start_idx + len(old_value_str)
                    modified_input = modified_input[:start_idx] + new_value_str + modified_input[end_idx:]
                    replacement_made = True
        
        # Method 4: Try word boundary matching for names and other text
        if not replacement_made:
            try:
                pattern = re.compile(r'\b' + re.escape(old_value_str) + r'\b', re.IGNORECASE)
                if pattern.search(modified_input):
                    modified_input = pattern.sub(new_value_str, modified_input)
                    replacement_made = True
            except re.error:
                pass
                
    return modified_input

def get_transaction_context_for_changes(ground_truth_str: str) -> Dict[str, Dict]:
    """Extract transaction context mapping values to their transaction references"""
    context = {}
    
    try:
        # Extract JSON content
        if ground_truth_str.strip().startswith('```json'):
            match = re.search(r'```json\s*(.*?)\s*```', ground_truth_str, re.DOTALL)
            if match:
                json_content = match.group(1).strip()
            else:
                json_content = ground_truth_str
        else:
            json_content = ground_truth_str
            
        json_data = json.loads(json_content)
        
        # Look for alerted_transactions array
        if 'alerted_transactions' in json_data and isinstance(json_data['alerted_transactions'], list):
            for txn_index, txn in enumerate(json_data['alerted_transactions']):
                if isinstance(txn, dict):
                    # Get transaction reference(s)
                    txn_refs = txn.get('transaction_references', [])
                    
                    # Create a unique identifier for this transaction
                    if txn_refs and isinstance(txn_refs, list) and len(txn_refs) > 0:
                        primary_ref = txn_refs  # Use first reference
                    else:
                        primary_ref = f"txn_{txn_index}"  # Use index if no reference
                        
                    # Map all values in this specific transaction to its reference
                    def map_values_to_ref(obj, ref, parent_key=""):
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if key != 'transaction_references' and value is not None:
                                    if isinstance(value, (str, int, float)):
                                        # Create unique key to avoid conflicts
                                        unique_key = f"{parent_key}_{key}_{str(value)}" if parent_key else f"{key}_{str(value)}"
                                        context[str(value)] = {
                                            'transaction_ref': ref,
                                            'field': key,
                                            'unique_key': unique_key
                                        }
                                    elif isinstance(value, dict):
                                        map_values_to_ref(value, ref, key)
                        elif isinstance(obj, list):
                            for item in obj:
                                map_values_to_ref(item, ref, parent_key)
                    
                    map_values_to_ref(txn, primary_ref)
        
    except (json.JSONDecodeError, AttributeError, KeyError):
        pass
    
    return context

def find_transaction_reference_for_value(value: str, transaction_context: Dict[str, Dict]) -> str:
    """Find which transaction reference a value belongs to"""
    if str(value) in transaction_context:
        return transaction_context[str(value)]['transaction_ref']
    
    # Try to find partial matches for complex values
    for context_value, context_info in transaction_context.items():
        if str(value) in context_value or context_value in str(value):
            return context_info['transaction_ref']
    
    return None

def format_comprehensive_diff(changes: List[Tuple[str, str]], original_input: str, original_transactions: str, original_ground_truth: str) -> Dict[str, str]:
    """Comprehensive diff with complete mapping and transaction context"""
    if not changes:
        return {
            'Changes_Summary': "No changes (0)",
            'Complete_Mapping': "",
            'Phantom_Changes': ""
        }
    
    total_changes = len([c for c in changes if c[1] != "SKIPPED"])
    skipped = len([c for c in changes if c[1] == "SKIPPED"])
    
    # Simple summary
    summary = f"Total: {total_changes} changes"
    if skipped > 0:
        summary += f", {skipped} skipped"
    
    # Parse JSON to get transaction context
    transaction_context = get_transaction_context_for_changes(original_ground_truth)
    
    # Complete mapping and phantom changes
    complete_mapping = []
    phantom_changes = []
    
    for old_val, new_val in changes:
        if new_val == "SKIPPED":
            complete_mapping.append(f"SKIPPED: {old_val}")
            continue
        
        # Show where it appears
        locations = []
        if old_val in original_input:
            locations.append("Input")
        if old_val in original_transactions:
            locations.append("Transactions") 
        if old_val in original_ground_truth:
            locations.append("JSON")
        
        # Find which transaction this change belongs to
        txn_ref = find_transaction_reference_for_value(old_val, transaction_context)
        txn_info = f" | TxnRef: {txn_ref}" if txn_ref else ""
        
        if locations:
            # Normal replacement
            location_str = "+".join(locations)
            complete_mapping.append(f"{old_val} → {new_val} | Location: {location_str}{txn_info}")
        else:
            # Phantom change - value doesn't exist in any text
            phantom_changes.append(f"{old_val} → {new_val} | PHANTOM CHANGE{txn_info}")
    
    # Add phantom count to summary
    phantom_count = len(phantom_changes)
    if phantom_count > 0:
        summary += f", {phantom_count} phantom"
    
    return {
        'Changes_Summary': summary,
        'Complete_Mapping': "\n".join(complete_mapping),
        'Phantom_Changes': "\n".join(phantom_changes) if phantom_changes else ""
    }

def main():
    random.seed(42)
    
    csv_file_path = input("Enter CSV file path (or press Enter for default): ").strip()
    if not csv_file_path:
        csv_file_path = 'Dataset_Source_v5_updated_with_groundtruth.csv'
    
    try:
        df = pd.read_csv(csv_file_path, na_filter=False)
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return
    
    initialize_global_set_number(df)
    
    input_column = 'Input'
    json_column = 'Ground Truth'
    transaction_column = 'Transactions'
    
    if 'Randomization Set' not in df.columns:
        df['Randomization Set'] = 0
    if 'Variant Number' not in df.columns:
        df['Variant Number'] = 1
    
    all_dataframes = [df.copy()]
    
    for type_name in df['Type'].unique():
        for variant_num in df[df['Type'] == type_name]['Variant Number'].unique():
            type_variant_rows = df[(df['Type'] == type_name) & (df['Variant Number'] == variant_num)].copy()
            randomization_count = RANDOMIZATION_COUNTS.get(type_name, 3)
            
            print(f"Creating {randomization_count} randomized sets for Type: {type_name}, Variant: {variant_num}")
            
            for randomization_num in range(1, randomization_count + 1):
                print(f"  Processing randomization set {randomization_num}...")
                
                randomized_df = type_variant_rows.copy()
                randomized_df['Randomization Set'] = randomization_num
                
                current_set_number = get_next_set_number()
                randomized_df['Set Number'] = current_set_number
                
                case_increment = current_set_number * 50
                if 'Case Number' in randomized_df.columns:
                    randomized_df['Case Number'] = randomized_df['Original Case Number'] + case_increment
                
                # Process each row for this randomization
                for index, row in randomized_df.iterrows():
                    # Get the original input, ground truth, and transactions
                    original_input = str(row[input_column])
                    ground_truth_str = str(row[json_column])
                    original_transactions = str(row[transaction_column])
                    document_type = str(row['Type'])
                    
                    try:
                        # Extract JSON from markdown code blocks if present
                        json_content = ground_truth_str
                        if ground_truth_str.strip().startswith('```json'):
                            # Extract content between ``````
                            match = re.search(r'```json\s*(.*?)\s*```', ground_truth_str, re.DOTALL)
                            if match:
                                json_content = match.group(1).strip()
                            else:
                                raise ValueError("Could not extract JSON from markdown code block")
                        
                        # Parse the ground truth JSON
                        ground_truth_json = json.loads(json_content)
                        
                        # Track changes for this randomization
                        changes = []
                        global_mappings = {}
                        
                        # Randomize the JSON fields
                        randomized_json = randomize_json_fields(ground_truth_json, changes, document_type, global_mappings)
                        
                        # Apply changes to input text
                        randomized_input = apply_changes_to_input(original_input, changes, global_mappings, document_type)
                        
                        # Apply changes to transaction records
                        randomized_transactions = apply_changes_to_input(original_transactions, changes, global_mappings, document_type)
                        
                        # Convert randomized JSON back to string
                        randomized_ground_truth_str = json.dumps(randomized_json, indent=2, ensure_ascii=False)
                        
                        # Comprehensive diff formatting
                        diff_data = format_comprehensive_diff(changes, original_input, original_transactions, ground_truth_str)
                        
                        # Update the randomized DataFrame
                        randomized_df.at[index, input_column] = randomized_input
                        randomized_df.at[index, json_column] = randomized_ground_truth_str
                        randomized_df.at[index, transaction_column] = randomized_transactions
                        
                        # Add comprehensive diff columns
                        randomized_df.at[index, 'Changes_Summary'] = diff_data['Changes_Summary']
                        randomized_df.at[index, 'Complete_Mapping'] = diff_data['Complete_Mapping']
                        randomized_df.at[index, 'Phantom_Changes'] = diff_data['Phantom_Changes']
                        
                    except Exception as e:
                        print(f"Error processing row {index}, randomization {randomization_num}: {str(e)}")
                        # Set error values for all diff columns
                        randomized_df.at[index, 'Changes_Summary'] = f"Error: {str(e)}"
                        randomized_df.at[index, 'Complete_Mapping'] = ""
                        randomized_df.at[index, 'Phantom_Changes'] = ""

                all_dataframes.append(randomized_df)
    
    final_df = pd.concat(all_dataframes, ignore_index=True)
    
    columns_to_clean = ['Transactions', 'Input', 'Instruction', 'Ground Truth']
    for col in columns_to_clean:
        if col in final_df.columns:
            final_df[col] = final_df[col].fillna('')
    
    input_dir = os.path.dirname(csv_file_path)
    input_filename = os.path.basename(csv_file_path)
    input_name, input_ext = os.path.splitext(input_filename)
    
    output_filename = os.path.join(input_dir, f'{input_name}_RANDOMIZED_ROWS{input_ext}')
    
    final_df.to_csv(output_filename, index=False, encoding='utf-8-sig', na_rep='')
    
    print(f"Randomization complete! Saved to: {output_filename}")
    print(f"Total rows in output: {len(final_df)}")

if __name__ == "__main__":
    print("Enhanced CSV Data Randomizer with Mapping System")
    print("=" * 60)
    main()

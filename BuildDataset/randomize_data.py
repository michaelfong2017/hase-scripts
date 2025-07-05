import pandas as pd
import json
import random
import re
import os
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
from data_processor import (
    random_generation_functions, strict_normalization_functions,
    replace_in_dataframe, NORMALIZED_NAMES, save_json_utf8, load_json_utf8,
    randomize_masked_value, clean_html_artifacts
)
from io import StringIO

# Updated Configuration
RANDOMIZATION_COUNTS = {
    'ADCC': 6,
    'ODFT': 6,
    'Search Warrant': 3,
    'HSBC Referral': 4,
    'UAR': 6,
    'Police Letter': 3
}

# Global set number tracker
global_set_number = 0

def initialize_global_set_number(df):
    """Initialize global set number from existing data"""
    global global_set_number
    if 'Set Number' in df.columns:
        global_set_number = df['Set Number'].max()
    else:
        global_set_number = 0
    print(f"Initialized global set number to: {global_set_number}")

def get_next_set_number():
    """Get next sequential set number"""
    global global_set_number
    global_set_number += 1
    return global_set_number

def normalize_amount_thorough(value):
    """Thoroughly normalize amount handling all currency symbols, commas, decimals"""
    if not value:
        return value
    
    value_str = str(value).strip()
    
    # Remove currency symbols and letters (keep digits, commas, dots, and minus)
    value_str = re.sub(r'[^0-9.,-]', '', value_str)
    
    # Remove commas
    value_str = value_str.replace(',', '')
    
    # Convert to float and then to string without trailing .0 if possible
    try:
        amount_float = float(value_str)
        if amount_float.is_integer():
            return str(int(amount_float))
        else:
            return str(amount_float)
    except ValueError:
        return value_str

class JSONParser:
    """Parse and validate JSON strings"""
    
    def parse_json(self, json_str):
        """Parse JSON string with error handling"""
        if not json_str or pd.isna(json_str):
            return {}
        
        try:
            # Clean HTML artifacts first
            clean_json = clean_html_artifacts(str(json_str))
            return json.loads(clean_json)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"JSON parsing error: {e}")
            return {}

class FieldMapper:
    """Map and collect field values for randomization"""
    
    def __init__(self, document_type):
        self.document_type = document_type
        
    def collect_mappings(self, ground_truth_json):
        """Collect all field mappings with cancel_amount constraint - WAIT FOR ALL VALUES FIRST"""
        mappings = {}
        field_types = {}
        
        # Extract values from ground truth
        values = self.extract_values_from_ground_truth(ground_truth_json)
        
        # Find the smallest amount to constrain cancel_amount_requested
        smallest_amount = None
        if 'amount' in values and values['amount']:
            try:
                amounts = []
                for amount_val in values['amount']:
                    normalized_amount = normalize_amount_thorough(amount_val)
                    try:
                        amounts.append(float(normalized_amount))
                    except ValueError:
                        continue
                if amounts:
                    smallest_amount = min(amounts)
            except:
                pass
        
        # FIRST: Generate mappings for all NON-cancel_amount fields
        for field_type, field_values in values.items():
            # SKIP DATE RANDOMIZATION FOR HSBC REFERRAL, UAR, AND ODFT
            if field_type == 'date' and self.document_type in ['HSBC Referral', 'UAR', 'ODFT']:
                continue

            if field_type == 'cancel_amount_requested':
                continue  # Skip cancel_amount for now
                
            if field_type in random_generation_functions and field_values:
                generator = random_generation_functions[field_type]
                used_replacements = set(mappings.values())
                
                for value in field_values:
                    if value and str(value).strip():
                        # Generate replacement normally
                        max_attempts = 10
                        for attempt in range(max_attempts):
                            random_val = generator()
                            
                            # Apply normalization
                            if field_type in strict_normalization_functions:
                                normalizer = strict_normalization_functions[field_type]
                                normalized_original = normalizer(value)
                                normalized_random = normalizer(random_val)
                            else:
                                normalized_original = value
                                normalized_random = random_val
                            
                            # Special handling for amounts
                            if field_type in ['amount']:
                                normalized_original = normalize_amount_thorough(value)
                                normalized_random = normalize_amount_thorough(random_val)
                            
                            # Special handling for dates
                            if field_type == 'date':
                                normalized_random = self.normalize_date_to_iso(normalized_random)
                            
                            # Apply ■ randomization
                            final_random = randomize_masked_value(normalized_random)
                            
                            # Check if this replacement is already used
                            if (final_random not in used_replacements and 
                                final_random not in mappings and
                                final_random != str(normalized_original) and
                                final_random != str(value)):
                                
                                # Create all possible variations
                                self.create_field_variations(value, normalized_original, final_random, field_type, mappings, field_types)
                                used_replacements.add(final_random)
                                break
                        else:
                            # If we couldn't find a unique replacement, use the last one
                            self.create_field_variations(value, normalized_original, final_random, field_type, mappings, field_types)
        
        # SECOND: Now generate cancel_amount_requested mappings with constraint
        if 'cancel_amount_requested' in values and values['cancel_amount_requested']:
            generator = random_generation_functions['cancel_amount_requested']
            used_replacements = set(mappings.values())
            
            for value in values['cancel_amount_requested']:
                if value and str(value).strip():
                    max_attempts = 10
                    for attempt in range(max_attempts):
                        # Generate constrained cancel amount
                        if smallest_amount is not None:
                            max_cancel = int(smallest_amount)
                            if max_cancel <= 1000:
                                random_cancel = random.randint(1, max_cancel)
                            else:
                                random_cancel = random.randint(1, min(max_cancel, int(max_cancel * 0.8)))
                            random_val = str(random_cancel)
                        else:
                            random_val = generator()
                        
                        # Apply normalization
                        normalized_original = normalize_amount_thorough(value)
                        normalized_random = normalize_amount_thorough(random_val)
                        
                        # Apply ■ randomization
                        final_random = randomize_masked_value(normalized_random)
                        
                        # Check if this replacement is already used
                        if (final_random not in used_replacements and 
                            final_random not in mappings and
                            final_random != str(normalized_original) and
                            final_random != str(value)):
                            
                            # Create all possible variations
                            self.create_field_variations(value, normalized_original, final_random, 'cancel_amount_requested', mappings, field_types)
                            used_replacements.add(final_random)
                            break
                    else:
                        # If we couldn't find a unique replacement, use the last one
                        self.create_field_variations(value, normalized_original, final_random, 'cancel_amount_requested', mappings, field_types)
        
        return mappings, field_types
    
    def create_field_variations(self, original_value, normalized_value, replacement, field_type, mappings, field_types):
        """Create field variations without excessive quote duplicates"""
        original_str = str(original_value).strip()
        normalized_str = str(normalized_value).strip()
        
        variations = [
            original_str,                    # Original value
            normalized_str,                  # Normalized value
        ]
        
        # For names, add comma variations only
        if field_type == 'name':
            variations.extend([
                original_str.replace(' ', ', '),     # Space to comma
                normalized_str.replace(' ', ', '),   # Normalized with comma
                original_str.replace(', ', ' '),     # Comma to space
                normalized_str.replace(', ', ' '),   # Normalized without comma
            ])
        
        # For amounts, add comma-formatted versions only
        if field_type in ['amount', 'cancel_amount_requested']:
            try:
                amount_val = float(normalized_str)
                comma_formatted = f"{amount_val:,.0f}" if amount_val.is_integer() else f"{amount_val:,.2f}"
                variations.append(comma_formatted)
            except ValueError:
                pass
        
        # Map all variations to the same replacement (no quote duplicates)
        for variation in set(variations):  # Remove duplicates
            if variation and variation.strip() and variation not in mappings:
                mappings[variation] = replacement
                field_types[variation] = field_type
    
    def extract_values_from_ground_truth(self, ground_truth):
        """Extract values including names for all document types"""
        values = {field: set() for field in random_generation_functions.keys()}
        
        # Extract from alerted_transactions
        for transaction in ground_truth.get('alerted_transactions', []):
            # Date
            if 'date' in transaction and transaction['date'] is not None:
                date_val = str(transaction['date']).strip()
                if date_val:
                    values['date'].add(date_val)
            
            # Amount - use thorough normalization
            if 'amount' in transaction and transaction['amount'] is not None:
                amount_val = str(transaction['amount']).strip()
                if amount_val:
                    values['amount'].add(amount_val)
                    normalized_amount = normalize_amount_thorough(amount_val)
                    if normalized_amount != amount_val:
                        values['amount'].add(normalized_amount)
            
            # Names - extract for all document types
            for side in ['from', 'to']:
                if side in transaction and 'name' in transaction[side]:
                    name_val = transaction[side]['name']
                    if name_val is not None:
                        name_str = str(name_val).strip()
                        name_upper = name_str.upper()
                        # Exclude CASH variants and empty strings
                        if (name_str and 
                            not re.match(r'^CASH(\s+CASH|\s+DEPOSIT)?$', name_upper) and
                            len(name_str) > 1):
                            values['name'].add(name_str)
            
            # Account numbers (exclude CASH variants)
            for side in ['from', 'to']:
                if side in transaction and 'account_number' in transaction[side]:
                    acc_val = transaction[side]['account_number']
                    if acc_val is not None:
                        acc_str = str(acc_val).strip()
                        acc_upper = acc_str.upper()
                        if (acc_str and 
                            not re.match(r'^CASH(\s+CASH|\s+DEPOSIT)?$', acc_upper) and
                            acc_str.upper() != 'NIL' and
                            len(acc_str) > 1):
                            values['account_number'].add(acc_str)
            
            # Banks - only randomize from.bank and only for ADCC or Police Letter types
            if (self.document_type in ['ADCC', 'Police Letter'] and 
                'from' in transaction and 'bank' in transaction['from']):
                bank_val = transaction['from']['bank']
                if bank_val is not None:
                    bank_str = str(bank_val).strip()
                    bank_upper = bank_str.upper()
                    if (bank_str and 
                        not re.match(r'^CASH(\s+CASH|\s+DEPOSIT)?$', bank_upper) and
                        bank_str.upper() != 'NIL' and
                        len(bank_str) > 1):
                        values['bank'].add(bank_str)
            
            # Cancel amount - use thorough normalization
            if 'cancel_amount_requested' in transaction and transaction['cancel_amount_requested'] is not None:
                cancel_val = str(transaction['cancel_amount_requested']).strip()
                if cancel_val and cancel_val != '0':
                    values['cancel_amount_requested'].add(cancel_val)
                    normalized_cancel = normalize_amount_thorough(cancel_val)
                    if normalized_cancel != cancel_val:
                        values['cancel_amount_requested'].add(normalized_cancel)
        
        # Extract other fields from ground truth root
        for field in ['police_reference', 'writ_no', 'contact_person']:
            if field in ground_truth and ground_truth[field] is not None:
                field_val = str(ground_truth[field]).strip()
                if field_val and len(field_val) > 1:
                    values[field].add(field_val)
        
        # Convert sets back to lists and remove substrings
        result = {}
        for field, value_set in values.items():
            value_list = list(value_set)
            # Remove values that are substrings of other values
            filtered_values = []
            for val in sorted(value_list, key=len, reverse=True):
                if not any(val in other and val != other for other in filtered_values):
                    filtered_values.append(val)
            result[field] = filtered_values
        
        return result
    
    def normalize_date_to_iso(self, date_str):
        """Normalize date to YYYY-MM-DD format, avoiding ambiguous formats"""
        if not date_str:
            return date_str
        
        # If already in YYYY-MM-DD format, return as-is
        if re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)):
            return str(date_str)
        
        # Try to parse and convert to YYYY-MM-DD (removed ambiguous formats)
        date_formats = [
            '%Y-%m-%d %H:%M:%S',  # 2024-08-24 00:00:00
            '%d %b %Y',           # 24 Aug 2024
            '%Y/%m/%d',           # 2024/08/24 (year first, unambiguous)
            '%d%b%Y',             # 24AUG2024
            '%d%b%y',             # 07AUG24
            '%Y%m%d',             # 20240824
            '%d-%m-%Y',           # 24-08-2024
            '%d.%m.%Y',           # 24.08.2024
            '%d%b',               # 05JAN (no year)
            '%d %b',              # 05 Jan (no year)
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(str(date_str), fmt)
                # If year is missing or 1900, assume current year (2024/2025)
                if parsed_date.year == 1900:
                    parsed_date = parsed_date.replace(year=2024)  # Default to 2024
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Handle Chinese date format (8月7日)
        chinese_date_match = re.match(r'(\d{1,2})月(\d{1,2})日', str(date_str))
        if chinese_date_match:
            month, day = chinese_date_match.groups()
            try:
                parsed_date = datetime(2024, int(month), int(day))  # Default to 2024
                return parsed_date.strftime('%Y-%m-%d')
            except ValueError:
                pass
        
        # If all formats fail, return original string
        return str(date_str)

class TextReplacer:
    """Replace text values using mappings - NO CASCADING + Remove Involved Parties + CSV Quote Handling"""
    
    def __init__(self, mappings, document_type=None):
        self.mappings = mappings
        self.document_type = document_type
        # Create a set of replacement values to avoid cascading
        self.replacement_values = set(str(v) for v in mappings.values())
    
    def remove_involved_parties_section(self, text):
        """Remove Involved Parties section from text"""
        if not text or pd.isna(text):
            return text
        
        text_str = str(text)
        
        # Find and remove everything from "Involved Parties" onwards
        pattern = r'Involved Parties\s*\n\s*Individual Information:.*'
        cleaned_text = re.sub(pattern, '', text_str, flags=re.DOTALL | re.IGNORECASE)
        
        return cleaned_text.strip()
    
    def replace_in_text(self, text):
        """Replace values including CSV-quoted variations and remove involved parties"""
        if not text or pd.isna(text):
            return text
        
        # First remove involved parties section
        result = self.remove_involved_parties_section(text)
        
        # Sort mappings by length (longest first) to avoid partial replacements
        sorted_mappings = sorted(self.mappings.items(), key=lambda x: len(str(x[0])), reverse=True)
        
        replaced_positions = set()
        
        for original, replacement in sorted_mappings:
            original_str = str(original)
            replacement_str = str(replacement)
            
            # Skip if original is already a replacement value (prevent cascading)
            if original_str in self.replacement_values:
                continue
            
            # Find all occurrences (including quoted versions)
            start = 0
            while True:
                pos = result.find(original_str, start)
                if pos == -1:
                    break
                
                end_pos = pos + len(original_str)
                
                # Check if this position overlaps with already replaced text
                if not any(p in replaced_positions for p in range(pos, end_pos)):
                    # Perform replacement
                    result = result[:pos] + replacement_str + result[end_pos:]
                    
                    # Mark these positions as replaced
                    new_end = pos + len(replacement_str)
                    replaced_positions.update(range(pos, new_end))
                    
                    start = new_end
                else:
                    start = pos + 1
        
        return result
    
    def replace_in_json(self, json_obj):
        """Replace values in JSON object recursively"""
        return self.apply_mappings_recursive_enhanced(json_obj, self.mappings)
    
    def apply_mappings_recursive_enhanced(self, obj, mappings):
        """Apply mappings with anti-cascading protection"""
        if isinstance(obj, dict):
            new_obj = {}
            for k, v in obj.items():
                if k in ['amount', 'cancel_amount_requested'] and v is not None:
                    # Handle amount fields - use thorough normalization
                    str_value = str(v)
                    
                    # Skip if this value is already a replacement (prevent cascading)
                    if str_value in self.replacement_values:
                        new_obj[k] = v
                        continue
                    
                    normalized_amount = normalize_amount_thorough(str_value)
                    
                    # Try normalized value first
                    if normalized_amount in mappings and normalized_amount not in self.replacement_values:
                        try:
                            new_obj[k] = float(mappings[normalized_amount]) if '.' in mappings[normalized_amount] else int(mappings[normalized_amount])
                        except ValueError:
                            new_obj[k] = mappings[normalized_amount]
                    # Fallback to original value
                    elif str_value in mappings and str_value not in self.replacement_values:
                        try:
                            new_obj[k] = float(mappings[str_value]) if '.' in mappings[str_value] else int(mappings[str_value])
                        except ValueError:
                            new_obj[k] = mappings[str_value]
                    else:
                        new_obj[k] = v
                elif k == 'date' and v is not None:
                    # Handle date fields - always normalize to YYYY-MM-DD
                    str_value = str(v)
                    
                    # Skip if this value is already a replacement (prevent cascading)
                    if str_value in self.replacement_values:
                        new_obj[k] = v
                        continue
                    
                    if str_value in mappings:
                        # Ensure replacement is in YYYY-MM-DD format
                        replacement = mappings[str_value]
                        field_mapper = FieldMapper(self.document_type)
                        normalized_date = field_mapper.normalize_date_to_iso(replacement)
                        new_obj[k] = normalized_date
                    else:
                        # Normalize original date
                        field_mapper = FieldMapper(self.document_type)
                        new_obj[k] = field_mapper.normalize_date_to_iso(str_value)
                elif k == 'bank' and v is not None:
                    # Handle bank fields - use normalized values, exclude CASH
                    str_value = str(v).strip().upper()
                    
                    # Skip if this value is already a replacement (prevent cascading)
                    if str_value in self.replacement_values:
                        new_obj[k] = v
                        continue
                    
                    if not re.match(r'^CASH(\s+CASH|\s+DEPOSIT)?$', str_value):
                        normalized_bank = strict_normalization_functions['bank'](str_value)
                        if normalized_bank in mappings and normalized_bank not in self.replacement_values:
                            new_obj[k] = mappings[normalized_bank]
                        elif str_value in mappings and str_value not in self.replacement_values:
                            new_obj[k] = mappings[str_value]
                        else:
                            new_obj[k] = v
                    else:
                        new_obj[k] = v  # Keep CASH as-is
                else:
                    new_obj[k] = self.apply_mappings_recursive_enhanced(v, mappings)
            return new_obj
        elif isinstance(obj, list):
            return [self.apply_mappings_recursive_enhanced(item, mappings) for item in obj]
        elif isinstance(obj, str):
            return self.apply_single_mapping_normalized(obj, mappings)
        elif isinstance(obj, (int, float)) and obj is not None:
            # Handle numeric values with thorough normalization
            str_value = str(obj)
            
            # Skip if this value is already a replacement (prevent cascading)
            if str_value in self.replacement_values:
                return obj
            
            normalized_amount = normalize_amount_thorough(str_value)
            
            if normalized_amount in mappings and normalized_amount not in self.replacement_values:
                try:
                    return float(mappings[normalized_amount]) if '.' in mappings[normalized_amount] else int(mappings[normalized_amount])
                except ValueError:
                    return mappings[normalized_amount]
            elif str_value in mappings and str_value not in self.replacement_values:
                try:
                    return float(mappings[str_value]) if '.' in mappings[str_value] else int(mappings[str_value])
                except ValueError:
                    return mappings[str_value]
            return obj
        else:
            return obj
    
    def apply_single_mapping_normalized(self, value, mappings):
        """Apply mappings with normalization priority and anti-cascading"""
        str_value = str(value)
        
        # Skip CASH variants
        if re.match(r'^CASH(\s+CASH|\s+DEPOSIT)?$', str_value.upper()):
            return str_value
        
        # Skip if this value is already a replacement (prevent cascading)
        if str_value in self.replacement_values:
            return str_value
        
        # Try direct mapping first
        if str_value in mappings:
            return randomize_masked_value(mappings[str_value])
        
        # Try normalized value for amounts
        normalized_amount = normalize_amount_thorough(str_value)
        if (normalized_amount in mappings and 
            normalized_amount != str_value and 
            normalized_amount not in self.replacement_values):
            return randomize_masked_value(mappings[normalized_amount])
        
        # Apply partial replacements with anti-cascading
        result = str_value
        replaced_positions = set()
        
        # Sort by length (longest first)
        sorted_mappings = sorted(mappings.items(), key=lambda x: len(str(x[0])), reverse=True)
        
        for original, replacement in sorted_mappings:
            original_str = str(original)
            replacement_str = str(replacement)
            
            # Skip if original is already a replacement value
            if original_str in self.replacement_values:
                continue
            
            # Find and replace without cascading
            start = 0
            while True:
                pos = result.find(original_str, start)
                if pos == -1:
                    break
                
                end_pos = pos + len(original_str)
                
                # Check if this position overlaps with already replaced text
                if not any(p in replaced_positions for p in range(pos, end_pos)):
                    # Perform replacement
                    final_replacement = randomize_masked_value(replacement_str)
                    result = result[:pos] + final_replacement + result[end_pos:]
                    
                    # Mark these positions as replaced
                    new_end = pos + len(final_replacement)
                    replaced_positions.update(range(pos, new_end))
                    
                    # Adjust start position
                    start = new_end
                else:
                    start = pos + 1
        
        return result
    
    def apply_mappings_to_transactions(self, transactions_csv):
        """Apply value mappings to transactions CSV string with quote handling"""
        if not transactions_csv or pd.isna(transactions_csv):
            return transactions_csv
        
        try:
            # Step 1: Parse and replace in structured data
            trans_df = pd.read_csv(StringIO(transactions_csv))
            
            for col in trans_df.columns:
                trans_df[col] = trans_df[col].apply(
                    lambda x: self.mappings.get(str(x), x) if pd.notna(x) else x
                )
            
            result_csv = trans_df.to_csv(index=False)
            
            # Step 2: Also apply direct text replacements for quoted variations
            for original, replacement in self.mappings.items():
                # Skip if original is already a replacement value (prevent cascading)
                if str(original) in self.replacement_values:
                    continue
                
                # Handle quoted versions
                quoted_original = f'"{original}"'
                quoted_replacement = f'"{replacement}"'
                result_csv = result_csv.replace(quoted_original, quoted_replacement)
                
                # Handle unquoted versions that might still exist
                result_csv = result_csv.replace(str(original), str(replacement))
            
            return result_csv
            
        except Exception as e:
            print(f"Error processing transactions: {e}")
            return transactions_csv

class DiffReporter:
    """Generate reports and alerts for randomization changes"""
    
    def __init__(self, mappings, field_types):
        self.mappings = mappings
        self.field_types = field_types
    
    def get_original_values(self):
        """Get newline-separated original values"""
        return '\n'.join([str(k) for k in self.mappings.keys() if str(k).strip()])
    
    def get_replacement_values(self):
        """Get newline-separated replacement values"""
        return '\n'.join([str(v) for v in self.mappings.values() if str(v).strip()])
    
    def generate_replacement_summary(self, original_input, original_transactions, ground_truth_str):
        """Generate summary of all replacements"""
        summary_lines = []
        
        for original, replacement in self.mappings.items():
            field_type = self.field_types.get(str(original), 'unknown')
            summary_lines.append(f"{field_type}: '{original}' → '{replacement}'")
        
        return '\n'.join(summary_lines)
    
    def generate_alerts(self, original_input, original_transactions, ground_truth_str, document_type):
        """Generate general alerts"""
        alerts = []
        
        # Count replacements by type
        type_counts = {}
        for original in self.mappings.keys():
            field_type = self.field_types.get(str(original), 'unknown')
            type_counts[field_type] = type_counts.get(field_type, 0) + 1
        
        for field_type, count in type_counts.items():
            alerts.append(f"Replaced {count} {field_type}(s)")
        
        return '\n'.join(alerts)
    
    def generate_field_specific_alerts(self, original_input, original_transactions, ground_truth_str, document_type):
        """Generate field-specific alert columns"""
        field_alerts = {
            'Alert_Dates': [],
            'Alert_Amounts': [],
            'Alert_Names': [],
            'Alert_Account_Numbers': [],
            'Alert_Banks': [],
            'Alert_Police_References': [],
            'Alert_Contact_Persons': [],
            'Alert_Writ_Numbers': [],
            'Alert_Cancel_Amount_Requested': []
        }
        
        field_mapping = {
            'date': 'Alert_Dates',
            'amount': 'Alert_Amounts',
            'name': 'Alert_Names',
            'account_number': 'Alert_Account_Numbers',
            'bank': 'Alert_Banks',
            'police_reference': 'Alert_Police_References',
            'contact_person': 'Alert_Contact_Persons',
            'writ_no': 'Alert_Writ_Numbers',
            'cancel_amount_requested': 'Alert_Cancel_Amount_Requested'
        }
        
        for original, replacement in self.mappings.items():
            field_type = self.field_types.get(str(original), 'unknown')
            if field_type in field_mapping:
                alert_key = field_mapping[field_type]
                field_alerts[alert_key].append(f"'{original}' → '{replacement}'")
        
        # Convert lists to strings
        result = {}
        for key, alerts in field_alerts.items():
            result[key] = '\n'.join(alerts)
        
        return result

def save_csv_with_indented_json(df, output_file, json_columns=['Ground Truth']):
    """Save CSV with properly indented JSON in specified columns"""
    df_copy = df.copy()
    
    def indent_json_str(json_str):
        try:
            if pd.isna(json_str) or json_str == '':
                return json_str
            obj = json.loads(json_str)
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except Exception:
            return json_str
    
    for col in json_columns:
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(indent_json_str)
    
    df_copy.to_csv(output_file, index=False, encoding='utf-8-sig')
    return df_copy

def main():
    """Enhanced main function with CSV quote handling"""
    random.seed(42)
    
    csv_file_path = input("Enter CSV file path (or press Enter for default): ").strip()
    if not csv_file_path:
        csv_file_path = 'Dataset_Source_v6_updated_with_groundtruth.csv'
    
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig', na_filter=False)
        print(f"Loaded dataset with {len(df)} rows")
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
    
    # Initialize new columns
    if 'Randomization Set' not in df.columns:
        df['Randomization Set'] = 0
    if 'Variant Number' not in df.columns:
        df['Variant Number'] = 1
    if 'Original Case Number' not in df.columns and 'Case Number' in df.columns:
        df['Original Case Number'] = df['Case Number']
    
    all_dataframes = [df.copy()]
    
    # Process each type and variant
    for type_name in df['Type'].unique():
        for variant_num in df[df['Type'] == type_name]['Variant Number'].unique():
            type_variant_rows = df[(df['Type'] == type_name) & (df['Variant Number'] == variant_num)].copy()
            
            # Use exact match for randomization count
            randomization_count = RANDOMIZATION_COUNTS[type_name]
            
            print(f"Creating {randomization_count} randomized sets for Type: {type_name}, Variant: {variant_num}")
            
            for randomization_num in range(1, randomization_count + 1):
                print(f"  Processing randomization set {randomization_num}...")
                
                randomized_df = type_variant_rows.copy()
                randomized_df['Randomization Set'] = randomization_num
                
                current_set_number = get_next_set_number()
                randomized_df['Set Number'] = current_set_number
                
                # Update case numbers
                case_increment = current_set_number * 50
                if 'Case Number' in randomized_df.columns:
                    randomized_df['Case Number'] = randomized_df['Original Case Number'] + case_increment
                
                # Process each row for this randomization
                for index, row in randomized_df.iterrows():
                    original_input = str(row[input_column])
                    ground_truth_str = str(row[json_column])
                    original_transactions = str(row[transaction_column])
                    document_type = str(row['Type'])
                    
                    try:
                        # Step 1: Parse Ground Truth JSON
                        parser = JSONParser()
                        ground_truth_json = parser.parse_json(ground_truth_str)
                        
                        # Step 2: Collect all mappings needed (with document type)
                        mapper = FieldMapper(document_type)
                        mappings, field_types = mapper.collect_mappings(ground_truth_json)
                        
                        # Step 3: Apply replacements to all texts (with document type)
                        replacer = TextReplacer(mappings, document_type)
                        
                        # Replace in JSON
                        randomized_json = replacer.replace_in_json(ground_truth_json)
                        
                        # Replace in Input and Transactions
                        randomized_input = replacer.replace_in_text(original_input)
                        randomized_transactions = replacer.apply_mappings_to_transactions(original_transactions)
                        
                        # Convert JSON back to string
                        randomized_ground_truth_str = json.dumps(randomized_json, indent=2, ensure_ascii=False)
                        
                        # Step 4: Generate reports
                        reporter = DiffReporter(mappings, field_types)
                        
                        # Generate all reports
                        original_values = reporter.get_original_values()
                        replacement_values = reporter.get_replacement_values()
                        replacement_summary = reporter.generate_replacement_summary(original_input, original_transactions, ground_truth_str)
                        replacement_alerts = reporter.generate_alerts(original_input, original_transactions, ground_truth_str, document_type)
                        field_specific_alerts = reporter.generate_field_specific_alerts(original_input, original_transactions, ground_truth_str, document_type)
                        
                        # Update the DataFrame with all columns
                        randomized_df.at[index, input_column] = randomized_input
                        randomized_df.at[index, json_column] = randomized_ground_truth_str
                        randomized_df.at[index, transaction_column] = randomized_transactions
                        randomized_df.at[index, 'Original_Values'] = original_values
                        randomized_df.at[index, 'Replacement_Values'] = replacement_values
                        randomized_df.at[index, 'Replacement_Summary'] = replacement_summary
                        randomized_df.at[index, 'Replacement_Alerts'] = replacement_alerts
                        
                        # Add field-specific alert columns
                        for field_name, alert_content in field_specific_alerts.items():
                            randomized_df.at[index, field_name] = alert_content
                        
                    except Exception as e:
                        print(f"Error processing row {index}, randomization {randomization_num}: {str(e)}")
                        randomized_df.at[index, 'Original_Values'] = f"Error: {str(e)}"
                        randomized_df.at[index, 'Replacement_Values'] = ""
                        randomized_df.at[index, 'Replacement_Summary'] = f"Error: {str(e)}"
                        randomized_df.at[index, 'Replacement_Alerts'] = ""
                        
                        # Set all field alert columns to empty on error
                        field_alert_columns = ['Alert_Dates', 'Alert_Amounts', 'Alert_Names', 'Alert_Account_Numbers', 
                                            'Alert_Banks', 'Alert_Police_References', 'Alert_Contact_Persons', 
                                            'Alert_Writ_Numbers', 'Alert_Cancel_Amount_Requested']
                        for col in field_alert_columns:
                            randomized_df.at[index, col] = ""
                
                all_dataframes.append(randomized_df)
    
    # Combine all dataframes
    final_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Clean up columns
    columns_to_clean = ['Transactions', 'Input', 'Instruction', 'Ground Truth']
    for col in columns_to_clean:
        if col in final_df.columns:
            final_df[col] = final_df[col].fillna('')
    
    # Generate output filename
    input_dir = os.path.dirname(csv_file_path)
    input_filename = os.path.basename(csv_file_path)
    input_name, input_ext = os.path.splitext(input_filename)
    
    output_filename = os.path.join(input_dir, f'{input_name}_RANDOMIZED_ROWS{input_ext}')
    
    # Save with proper JSON indentation
    save_csv_with_indented_json(final_df, output_filename, ['Ground Truth'])
    
    print(f"Randomization complete! Saved to: {output_filename}")
    print(f"Total rows in output: {len(final_df)}")
    
    # Save processing info
    processing_info = {
        'original_rows': len(df),
        'final_rows': len(final_df),
        'randomization_sets_created': len(all_dataframes) - 1,
        'timestamp': pd.Timestamp.now().isoformat(),
        'randomization_counts': RANDOMIZATION_COUNTS
    }
    save_json_utf8(processing_info, 'randomization_processing_info.json')
    print(f"Processing info saved to 'randomization_processing_info.json'")

if __name__ == "__main__":
    print("Enhanced CSV Data Randomizer - Complete Version with CSV Quote Handling")
    print("=" * 60)
    main()

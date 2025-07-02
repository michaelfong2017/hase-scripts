import random
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Set, Tuple
from pattern import *

class FieldMapper:
    def __init__(self, document_type: str):
        self.document_type = document_type
        self.mappings = {}
        self.field_types = {}
        self.name_variants = {}
        
    def collect_mappings(self, json_data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Collect all unique values that need mapping and generate their replacements"""
        # Step 1: Collect all unique values by field type
        unique_values = self._collect_unique_values(json_data)
        
        # Step 2: Generate consistent mappings for each field type
        self._generate_mappings(unique_values)
        
        return self.mappings, self.field_types
    
    def _normalize_name(self, name_str: str) -> str:
        """Normalize name to standard format for consistent mapping"""
        if not name_str:
            return ""
        
        # Convert to uppercase for consistency
        normalized = name_str.upper().strip()
        
        # Remove titles and prefixes
        normalized = re.sub(r'\b(MR\.?|MRS\.?|MS\.?|MISS|DR\.?|PROF\.?)\s*', '', normalized)
        
        # Remove suffixes like "AND OTHERS"
        normalized = re.sub(r'\s+(AND\s+OTHERS?|& OTHERS?|ET AL\.?).*$', '', normalized)
        
        # Remove extra whitespace and normalize spacing
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove commas and normalize spacing around them
        normalized = re.sub(r'\s*,\s*', ' ', normalized)
        
        # Handle initials - convert single letters to full format
        # e.g., "CHAN T M" -> "CHAN TAI MAN" (if we have a mapping)
        parts = normalized.split()
        if len(parts) >= 2:
            # If last parts are single letters, they might be initials
            if len(parts) >= 3 and all(len(part) == 1 for part in parts[1:]):
                # This looks like "SURNAME INITIAL INITIAL" format
                # We'll keep it as is for now, but mark it for potential expansion
                pass
        
        return normalized

    def _find_matching_replacement_name(self, normalized_name: str) -> str:
        """Find best matching replacement name from available options"""
        # First, try exact match
        for replacement_name in REPLACEMENT_OPTIONS['names']:
            if normalized_name == replacement_name:
                continue  # Don't replace with same name
            return replacement_name
        
        # If no exact match, try pattern matching
        name_parts = normalized_name.split()
        if len(name_parts) >= 2:
            surname = name_parts[0]
            
            # Look for replacement names with different surname
            for replacement_name in REPLACEMENT_OPTIONS['names']:
                replacement_parts = replacement_name.split()
                if len(replacement_parts) >= 2 and replacement_parts[0] != surname:
                    return replacement_name
        
        # Fallback to random selection
        available_names = [name for name in REPLACEMENT_OPTIONS['names'] if name != normalized_name]
        return random.choice(available_names) if available_names else REPLACEMENT_OPTIONS['names'][0]
    
    def _collect_unique_values(self, obj: Any, parent_key: str = "") -> Dict[str, Set[Any]]:
        """Recursively collect all unique values by field type"""
        unique_values = {
            'dates': set(),
            'amounts': set(),
            'cancel_amount_requested': set(),
            'names': set(),
            'account_numbers': set(),
            'banks': set(),
            'police_references': set(),
            'writ_numbers': set(),
            'contact_persons': set()
        }
        
        # Track normalized names to their original variants
        self.name_variants = {}  # normalized_name -> [original_variant1, original_variant2, ...]
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in EXCLUDED_FIELDS or value is None:
                    continue
                
                # Record field type when collecting values
                if key == "date" and isinstance(value, str):
                    unique_values['dates'].add(value)
                    self.field_types[value] = 'dates'
                    
                elif key == "amount" and isinstance(value, (str, int, float)):
                    unique_values['amounts'].add(str(value))
                    self.field_types[str(value)] = 'amounts'
                    
                elif key == "cancel_amount_requested" and isinstance(value, (str, int, float)):
                    unique_values['cancel_amount_requested'].add(str(value))
                    self.field_types[str(value)] = 'cancel_amount_requested'
                    
                elif key == "name" and isinstance(value, str):
                    # Normalize the name for consistent mapping
                    normalized_name = self._normalize_name(value)
                    
                    # Track all variants of this normalized name
                    if normalized_name not in self.name_variants:
                        self.name_variants[normalized_name] = []
                    self.name_variants[normalized_name].append(value)
                    
                    # Only add the normalized name to unique_values (not the original)
                    unique_values['names'].add(normalized_name)
                    
                    # Map ALL variants to the same field type
                    self.field_types[value] = 'names'
                    
                elif key == "account_number" and isinstance(value, str):
                    unique_values['account_numbers'].add(value)
                    self.field_types[value] = 'account_numbers'
                    
                elif key == "bank" and isinstance(value, str):
                    # Only collect bank names for ADCC and Police Letter document types
                    if self.document_type in ['ADCC', 'Police Letter']:
                        # Only collect from "from" section for these document types
                        if parent_key == "from":
                            unique_values['banks'].add(value)
                            self.field_types[value] = 'banks'
                    # For other document types, completely skip bank collection
                        
                elif key == "police_reference" and value:
                    unique_values['police_references'].add(str(value))
                    self.field_types[str(value)] = 'police_references'
                    
                elif key == "writ_no" and value:
                    unique_values['writ_numbers'].add(str(value))
                    self.field_types[str(value)] = 'writ_numbers'
                    
                elif key == "contact_person" and value:
                    unique_values['contact_persons'].add(str(value))
                    self.field_types[str(value)] = 'contact_persons'
                    
                elif isinstance(value, (dict, list)):
                    nested_values = self._collect_unique_values(value, key)
                    for field_type, values in nested_values.items():
                        unique_values[field_type].update(values)
                        
        elif isinstance(obj, list):
            for item in obj:
                nested_values = self._collect_unique_values(item, parent_key)
                for field_type, values in nested_values.items():
                    unique_values[field_type].update(values)
        
        return unique_values
    
    def _generate_mappings(self, unique_values: Dict[str, Set[Any]]):
        """Generate consistent mappings for each field type"""
        
        # Generate date mappings (always YYYY-MM-DD format)
        for date_str in unique_values['dates']:
            self.mappings[date_str] = self._randomize_date(date_str)
        
        # Generate amount mappings (numeric format without currency)
        for amount_str in unique_values['amounts']:
            self.mappings[amount_str] = self._randomize_amount(amount_str)
        
        # Generate cancel_amount_requested mappings with constraints
        all_amounts = []
        for amount_str in unique_values['amounts']:
            try:
                numeric_value = float(amount_str.replace(',', ''))
                all_amounts.append(numeric_value)
            except:
                pass
        
        for amount_str in unique_values['cancel_amount_requested']:
            self.mappings[amount_str] = self._randomize_cancel_amount(amount_str, all_amounts)
        
        # Generate name mappings - handle variants consistently
        for normalized_name in unique_values['names']:
            replacement_name = self._randomize_name(normalized_name)
            
            # Map ALL variants of this normalized name to the same replacement
            if normalized_name in self.name_variants:
                for variant in self.name_variants[normalized_name]:
                    self.mappings[variant] = replacement_name
        
        # Generate account number mappings
        for account in unique_values['account_numbers']:
            self.mappings[account] = self._randomize_account_number(account)
        
        # Generate bank mappings
        for bank in unique_values['banks']:
            if self.document_type in BANK_RANDOMIZATION_TYPES:
                self.mappings[bank] = self._randomize_bank(bank)
            else:
                self.mappings[bank] = bank  # No change
        
        # Generate police reference mappings
        for ref in unique_values['police_references']:
            self.mappings[ref] = self._randomize_police_reference(ref)
        
        # Generate writ number mappings
        for writ in unique_values['writ_numbers']:
            self.mappings[writ] = self._randomize_writ_no(writ)
        
        # Generate contact person mappings
        for contact in unique_values['contact_persons']:
            self.mappings[contact] = self._randomize_contact_person(contact)
    
    def _randomize_date(self, date_str: str) -> str:
        """Randomize date to YYYY-MM-DD format"""
        try:
            # Parse date in various formats
            parsed_date = None
            for pattern, fmt in DATE_FORMAT_PATTERNS:
                match = re.search(pattern, date_str, re.IGNORECASE)
                if match:
                    try:
                        # Handle different capture group structures
                        if '月' in fmt:  # Chinese format
                            month, day = match.groups()
                            parsed_date = datetime(2024, int(month), int(day))  # Use current year as default
                        elif '%Y' in fmt and fmt.startswith('%Y'):  # YYYY first
                            year, month, day = match.groups()
                            parsed_date = datetime(int(year), int(month), int(day))
                        elif '%Y' in fmt and fmt.endswith('%Y'):  # YYYY last
                            if '%b' in fmt or '%B' in fmt:  # Month name formats
                                if len(match.groups()) == 3:
                                    day, month_name, year = match.groups()
                                    # Convert month name to number
                                    month_abbr = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                                'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                                    month_num = month_abbr.get(month_name.lower()[:3], 1)
                                    parsed_date = datetime(int(year), month_num, int(day))
                            else:  # Numeric formats
                                parts = match.groups()
                                if len(parts) == 3:
                                    if fmt.startswith('%m'):  # MM-DD-YYYY
                                        month, day, year = parts
                                    else:  # DD-MM-YYYY
                                        day, month, year = parts
                                    parsed_date = datetime(int(year), int(month), int(day))
                        
                        if parsed_date:
                            break
                    except (ValueError, TypeError):
                        continue
            
            if not parsed_date:
                return date_str
            
            # Generate random offset
            random_offset = random.randint(-365, 365)
            new_date = parsed_date + timedelta(days=random_offset)
            
            # Always return YYYY-MM-DD format
            return new_date.strftime('%Y-%m-%d')
            
        except:
            return date_str
    
    def _randomize_amount(self, amount_str: str) -> str:
        """Randomize amount to numeric format without currency, preserving decimal format"""
        try:
            # Remove commas and parse numeric value
            clean_str = amount_str.replace(',', '')
            numeric_value = float(clean_str)
            
            # Generate new value (50% to 150% of original)
            variation = random.uniform(0.5, 1.5)
            new_value = numeric_value * variation
            
            # Check if original was integer or float format
            if '.' in clean_str:
                # Original was float, preserve decimal format
                return str(round(new_value, 2))
            else:
                # Original was integer, return as integer
                return str(int(new_value))
                
        except:
            # Fallback to random number
            random_value = random.uniform(1000, 100000)
            return str(round(random_value, 2))

    def _randomize_cancel_amount(self, amount_str: str, all_amounts: List[float]) -> str:
        """Randomize cancel_amount_requested with constraints, preserving decimal format"""
        try:
            # Parse the original cancel amount
            clean_str = amount_str.replace(',', '')
            original_value = float(clean_str)
            
            # Find the reference amount (lowest amount for safety)
            if all_amounts:
                reference_amount = min(all_amounts)
            else:
                # Fallback if no amounts available
                reference_amount = original_value if original_value > 0 else 1000
            
            # Ensure reference amount is positive
            if reference_amount <= 0:
                reference_amount = 1000
            
            # With at least 50% chance, keep the same if valid
            if original_value > 0 and original_value <= reference_amount and random.random() < 0.5:
                new_value = original_value
            else:
                # Generate new value between 0.01 and reference_amount
                new_value = random.uniform(0.01, reference_amount)
            
            # Check if original was integer or float format
            if '.' in clean_str:
                # Original was float, preserve decimal format
                return str(round(new_value, 2))
            else:
                # Original was integer, return as integer if new value is whole
                if new_value.is_integer():
                    return str(int(new_value))
                else:
                    return str(round(new_value, 2))
                
        except:
            # Fallback to a reasonable default
            fallback_amount = min(all_amounts) if all_amounts else 1000
            random_value = random.uniform(0.01, fallback_amount)
            return str(round(random_value, 2))
    
    def _randomize_name(self, name: str) -> str:
        """Randomize name with pattern matching and normalization"""
        if not name or not isinstance(name, str):
            return name
        
        # Normalize the name
        normalized_name = self._normalize_name(name)
        
        # Basic validation - skip if contains special characters
        if not re.match(r'^[A-Za-z0-9\s,\.&\-\']+$', name):
            return name
        
        # Find appropriate replacement
        replacement_name = self._find_matching_replacement_name(normalized_name)
        
        return replacement_name
    
    def _randomize_account_number(self, account: str) -> str:
        """Randomize account number preserving format"""
        try:
            if re.match(r'\d{3}-\d{6}-\d{3}', account):
                return f"{random.randint(100, 999)}-{random.randint(100000, 999999)}-{random.randint(100, 999)}"
            elif re.match(r'\d{10,16}', account):
                length = len(account)
                return ''.join([str(random.randint(0, 9)) for _ in range(length)])
            elif re.match(r'[A-Z]{2}\d+', account):
                bank_code = account[:2]
                digit_part = account[2:]
                new_digits = ''.join([str(random.randint(0, 9)) for _ in range(len(digit_part))])
                return f"{bank_code}{new_digits}"
            else:
                return re.sub(r'\d', lambda x: str(random.randint(0, 9)), account)
        except:
            return f"{random.randint(100, 999)}-{random.randint(100000, 999999)}-{random.randint(100, 999)}"
    
    def _randomize_bank(self, bank: str) -> str:
        """Randomize bank using mapping system"""
        original_root = find_bank_root(bank)
        new_root = get_random_bank_root(exclude_root=original_root)
        
        if new_root and new_root in BANK_ROOT_TO_FULL_NAME:
            return BANK_ROOT_TO_FULL_NAME[new_root]
        
        return random.choice(list(BANK_ROOT_TO_FULL_NAME.values()))
    
    def _randomize_police_reference(self, ref: str) -> str:
        """Randomize police reference"""
        template = random.choice(REPLACEMENT_OPTIONS['police_references'])
        return self._replace_placeholders(template)
    
    def _randomize_writ_no(self, writ: str) -> str:
        """Randomize writ number"""
        template = random.choice(REPLACEMENT_OPTIONS['writ_numbers'])
        return self._replace_placeholders(template)
    
    def _randomize_contact_person(self, contact: str) -> str:
        """Randomize contact person"""
        template = random.choice(REPLACEMENT_OPTIONS['contact_persons'])
        return self._replace_placeholders(template)
    
    def _replace_placeholders(self, template: str) -> str:
        """Replace placeholders in templates"""
        result = template
        for placeholder, func in PLACEHOLDER_FUNCTIONS.items():
            result = result.replace(placeholder, func())
        return result

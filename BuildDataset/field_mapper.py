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
        """Normalize name using regex patterns for consistent mapping"""
        if not name_str:
            return ""
        
        # Convert to uppercase for consistency and strip
        normalized = name_str.upper().strip()
        
        # Step 1: Remove titles and prefixes (more explicit pattern)
        normalized = re.sub(r'^(MR\.?|MRS\.?|MS\.?|MISS|DR\.?|PROF\.?)\s+', '', normalized, flags=re.IGNORECASE)
        
        # Step 2: Remove suffixes like "AND OTHERS"
        normalized = re.sub(r'\s+(AND\s+OTHERS?|& OTHERS?|ET AL\.?).*$', '', normalized, flags=re.IGNORECASE)
        
        # Step 3: Remove commas and normalize spacing around them
        normalized = re.sub(r'\s*,\s*', ' ', normalized)
        
        # Step 4: Normalize multiple spaces to single space
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Step 5: Handle concatenated names - check if we have surname + long concatenated name
        parts = normalized.split()
        if len(parts) == 2:
            surname = parts[0]
            given_names = parts[1]
            
            # If given names are concatenated (6+ chars, no spaces), try to split
            if len(given_names) >= 6:
                # Apply splitting patterns
                for split_pattern, split_replacement in NAME_SPLIT_PATTERNS:
                    new_given = re.sub(split_pattern, split_replacement, given_names)
                    if new_given != given_names:
                        given_names = new_given
                        break
                
                normalized = f"{surname} {given_names}"
        
        # Final cleanup
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized

    def _find_matching_replacement_name(self, normalized_name: str) -> str:
        """Find best matching replacement name from available options"""
        # Get all available replacement names
        available_names = [name for name in REPLACEMENT_OPTIONS['names'] if name != normalized_name]
        
        if not available_names:
            return REPLACEMENT_OPTIONS['names'][0]
        
        # Try to find a replacement with different surname
        name_parts = normalized_name.split()
        if len(name_parts) >= 2:
            surname = name_parts[0]
            
            # Get all names with different surnames
            different_surname_names = []
            for replacement_name in available_names:
                replacement_parts = replacement_name.split()
                if len(replacement_parts) >= 2 and replacement_parts[0] != surname:
                    different_surname_names.append(replacement_name)
            
            if different_surname_names:
                # FIXED: Return a random choice instead of the first one
                return random.choice(different_surname_names)
        
        # Fallback to random selection from all available names
        return random.choice(available_names)
    
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
                    # Skip date randomization for specific document types
                    if self.document_type not in ['UAR', 'ODFT', 'HSBC Referral']:
                        unique_values['dates'].add(value)
                        self.field_types[value] = 'dates'
                    
                elif key == "amount" and isinstance(value, (str, int, float)):
                    # Clean and normalize the amount string for collection
                    amount_str = str(value).strip()
                    
                    # Remove currency prefixes and clean formatting
                    clean_amount = re.sub(r'^(HKD|USD|CNY|SGD)\s*', '', amount_str, flags=re.IGNORECASE)
                    clean_amount = clean_amount.replace(',', '').strip()
                    
                    # Store the original format for mapping
                    unique_values['amounts'].add(amount_str)
                    self.field_types[amount_str] = 'amounts'
                    
                elif key == "cancel_amount_requested" and isinstance(value, (str, int, float)):
                    # Clean and normalize the cancel amount string for collection
                    amount_str = str(value).strip()
                    
                    # Remove currency prefixes and clean formatting for processing
                    clean_amount = re.sub(r'^(HKD|USD|CNY|SGD)\s*', '', amount_str, flags=re.IGNORECASE)
                    clean_amount = clean_amount.replace(',', '').strip()
                    
                    # Store the original format for mapping
                    unique_values['cancel_amount_requested'].add(amount_str)
                    self.field_types[amount_str] = 'cancel_amount_requested'
                    
                elif key == "name" and isinstance(value, str):
                    normalized_name = self._normalize_name(value)
                    
                    # Initialize variants list if not exists
                    if normalized_name not in self.name_variants:
                        self.name_variants[normalized_name] = []
                    
                    # Add the original value as a variant
                    if value not in self.name_variants[normalized_name]:
                        self.name_variants[normalized_name].append(value)
                    
                    # CRITICAL: Also add the normalized name itself as a variant if different
                    if normalized_name != value and normalized_name not in self.name_variants[normalized_name]:
                        self.name_variants[normalized_name].append(normalized_name)
                    
                    # Only add the normalized name to unique_values
                    unique_values['names'].add(normalized_name)
                    
                    # Map ALL variants to the same field type
                    self.field_types[value] = 'names'
                    if normalized_name != value:
                        self.field_types[normalized_name] = 'names'
                    
                elif key == "account_number" and isinstance(value, str):
                    unique_values['account_numbers'].add(value)
                    self.field_types[value] = 'account_numbers'
                    
                elif key == "bank" and isinstance(value, str):
                    # DISABLED: Bank randomization turned off
                    pass
                    # Only collect bank names for ADCC and Police Letter document types
                    # if self.document_type in ['ADCC', 'Police Letter']:
                    #     # Only collect from "from" section for these document types
                    #     if parent_key == "from":
                    #         unique_values['banks'].add(value)
                    #         self.field_types[value] = 'banks'
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
            
            # Map the normalized name
            self.mappings[normalized_name] = replacement_name
            
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
            parsed_date = None
            for pattern, fmt in DATE_FORMAT_PATTERNS:
                match = re.search(pattern, date_str, re.IGNORECASE)
                if match:
                    try:
                        groups = match.groups()
                        
                        if '月' in fmt:  # Chinese format
                            month, day = groups
                            parsed_date = datetime(2024, int(month), int(day))
                        elif '%Y%m%d' in fmt:  # 8-digit format like 20241227
                            date_string = groups[0]
                            parsed_date = datetime.strptime(date_string, '%Y%m%d')
                        elif '%d %b %Y' in fmt:  # Day Month Year format like "05 Jan 2025"
                            day, month_name, year = groups
                            month_abbr = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                            month_num = month_abbr.get(month_name.lower(), 1)
                            parsed_date = datetime(int(year), month_num, int(day))
                        elif '%d%b%Y' in fmt:  # Day+Month+Year concatenated like "12NOV2024"
                            day, month_name, year = groups
                            month_abbr = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                            month_num = month_abbr.get(month_name.lower(), 1)
                            parsed_date = datetime(int(year), month_num, int(day))
                        elif '%d%b' in fmt:  # Day+Month without year like "07AUG"
                            day, month_name = groups
                            month_abbr = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
                            month_num = month_abbr.get(month_name.lower(), 1)
                            parsed_date = datetime(2024, month_num, int(day))  # Use default year
                        elif '%Y' in fmt and fmt.startswith('%Y'):  # YYYY first
                            year, month, day = groups
                            parsed_date = datetime(int(year), int(month), int(day))
                        elif '%Y' in fmt and fmt.endswith('%Y'):  # YYYY last
                            if len(groups) == 3:
                                if fmt.startswith('%m'):  # MM-DD-YYYY
                                    month, day, year = groups
                                else:  # DD-MM-YYYY
                                    day, month, year = groups
                                parsed_date = datetime(int(year), int(month), int(day))
                        
                        if parsed_date:
                            break
                    except (ValueError, TypeError):
                        continue
            
            if not parsed_date:
                return date_str
            
            random_offset = random.randint(-365, 365)
            new_date = parsed_date + timedelta(days=random_offset)
            
            return new_date.strftime('%Y-%m-%d')
            
        except:
            return date_str
    
    def _randomize_amount(self, amount_str: str) -> str:
        """Randomize amount preserving format"""
        try:
            currency_prefix = ""
            clean_str = amount_str.strip()
            
            currency_match = re.match(r'^(HKD|USD|CNY|SGD)\s*', clean_str, re.IGNORECASE)
            if currency_match:
                currency_prefix = currency_match.group(1).upper() + " "
                clean_str = clean_str[len(currency_match.group(0)):]
            
            clean_str = clean_str.replace(',', '')
            numeric_value = float(clean_str)
            
            variation = random.uniform(0.5, 1.5)
            new_value = numeric_value * variation
            
            # Format based on original decimal presence
            if '.' in clean_str:
                formatted_amount = f"{new_value:.2f}"
            else:
                formatted_amount = str(int(round(new_value)))
            
            # FIXED: Proper comma formatting that preserves decimals
            if ',' in amount_str:
                if '.' in formatted_amount:
                    # Split into integer and decimal parts
                    integer_part, decimal_part = formatted_amount.split('.')
                    # Add commas to integer part only
                    integer_with_commas = f"{int(integer_part):,}"
                    formatted_amount = f"{integer_with_commas}.{decimal_part}"
                else:
                    # No decimals, just add commas to the whole number
                    formatted_amount = f"{int(formatted_amount):,}"
            
            return currency_prefix + formatted_amount
            
        except:
            random_value = random.uniform(1000, 100000)
            if 'HKD' in amount_str.upper():
                return f"HKD {random_value:,.2f}"
            else:
                return f"{random_value:.2f}"

    def _randomize_cancel_amount(self, amount_str: str, all_amounts: List[float]) -> str:
        """Randomize cancel_amount_requested with constraints"""
        try:
            currency_prefix = ""
            clean_str = amount_str.strip()
            
            currency_match = re.match(r'^(HKD|USD|CNY|SGD)\s*', clean_str, re.IGNORECASE)
            if currency_match:
                currency_prefix = currency_match.group(1).upper() + " "
                clean_str = clean_str[len(currency_match.group(0)):]
            
            clean_str = clean_str.replace(',', '')
            original_value = float(clean_str)
            
            if all_amounts:
                reference_amount = min(all_amounts)
            else:
                reference_amount = original_value if original_value > 0 else 1000
            
            if reference_amount <= 0:
                reference_amount = 1000
            
            if original_value > 0 and original_value <= reference_amount and random.random() < 0.5:
                new_value = original_value
            else:
                new_value = random.uniform(0.01, reference_amount)
            
            # Format based on original decimal presence
            if '.' in clean_str:
                formatted_amount = f"{new_value:.2f}"
            else:
                if new_value.is_integer():
                    formatted_amount = str(int(new_value))
                else:
                    formatted_amount = f"{new_value:.2f}"
            
            # FIXED: Proper comma formatting that preserves decimals
            if ',' in amount_str:
                if '.' in formatted_amount:
                    # Split into integer and decimal parts
                    integer_part, decimal_part = formatted_amount.split('.')
                    # Add commas to integer part only
                    integer_with_commas = f"{int(integer_part):,}"
                    formatted_amount = f"{integer_with_commas}.{decimal_part}"
                else:
                    # No decimals, just add commas to the whole number
                    formatted_amount = f"{int(formatted_amount):,}"
            
            return currency_prefix + formatted_amount
            
        except:
            fallback_amount = min(all_amounts) if all_amounts else 1000
            random_value = random.uniform(0.01, fallback_amount)
            
            if 'HKD' in amount_str.upper():
                return f"HKD {random_value:,.2f}"
            else:
                return f"{random_value:.2f}"
    
    def _randomize_name(self, name: str) -> str:
        """Randomize name with pattern matching and normalization"""
        if not name or not isinstance(name, str):
            return name
        
        # Normalize the name
        normalized_name = self._normalize_name(name)
        
        # Basic validation - skip if contains special characters
        if not re.match(NAME_VALIDATION_PATTERN, name):
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

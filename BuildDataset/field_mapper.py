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
        
    def collect_mappings(self, json_data: Dict[str, Any]) -> Tuple[Dict[str, str], Dict[str, str]]:
        """Collect all unique values that need mapping and generate their replacements"""
        # Step 1: Collect all unique values by field type
        unique_values = self._collect_unique_values(json_data)
        
        # Step 2: Generate consistent mappings for each field type
        self._generate_mappings(unique_values)
        
        return self.mappings, self.field_types
    
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
                    unique_values['names'].add(value)
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
                    
                # REMOVED: police_team is not randomized
                    
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
        
        # Generate amount mappings (always HKD format)
        for amount_str in unique_values['amounts']:
            self.mappings[amount_str] = self._randomize_amount(amount_str)
        
        # Generate cancel_amount_requested mappings
        for amount_str in unique_values['cancel_amount_requested']:
            self.mappings[amount_str] = self._randomize_amount(amount_str)
        
        # Generate name mappings
        for name in unique_values['names']:
            self.mappings[name] = self._randomize_name(name)
        
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
        
        # REMOVED: police_team mappings
        
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
                if re.match(pattern, date_str):
                    parsed_date = datetime.strptime(date_str, fmt)
                    break
            
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
        """Randomize amount to HKD format"""
        try:
            # Extract numeric value
            numeric_value = float(re.sub(r'[^\d.]', '', amount_str))
            
            # Generate new value (50% to 150% of original)
            variation = random.uniform(0.5, 1.5)
            new_value = numeric_value * variation
            
            # Always return HKD format
            return f"HKD{new_value:.2f}"
            
        except:
            return f"HKD{random.uniform(1000, 100000):.2f}"
    
    def _randomize_name(self, name: str) -> str:
        """Randomize name"""
        if not re.match(NAME_VALIDATION_PATTERN, name):
            return name
        return random.choice(REPLACEMENT_OPTIONS['names'])
    
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

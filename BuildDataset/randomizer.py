import pandas as pd
import json
import random
import re
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

# Global set number tracker
global_set_number = 0

def initialize_global_set_number(df):
    """Initialize global set number based on existing data"""
    global global_set_number
    if 'Set Number' in df.columns:
        global_set_number = df['Set Number'].max()
    else:
        global_set_number = 0
    print(f"Initialized global set number to: {global_set_number}")

def get_next_set_number():
    """Get the next global set number"""
    global global_set_number
    global_set_number += 1
    return global_set_number

def randomize_date(original_date: str) -> str:
    """Randomize a date string in YYYY-MM-DD format"""
    try:
        # Parse the original date
        date_obj = datetime.strptime(original_date, "%Y-%m-%d")
        
        # Generate a random offset between -365 and +365 days
        random_offset = random.randint(-365, 365)
        new_date = date_obj + timedelta(days=random_offset)
        
        return new_date.strftime("%Y-%m-%d")
    except:
        # If parsing fails, generate a random date in the past 2 years
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2025, 12, 31)
        random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
        return random_date.strftime("%Y-%m-%d")

def randomize_amount(original_amount: str) -> str:
    """Randomize an amount string like 'HKD40,000.00'"""
    try:
        # Extract currency and numeric part
        match = re.match(r'([A-Z]{3})([0-9,]+\.?\d*)', original_amount)
        if match:
            currency = match.group(1)
            amount_str = match.group(2).replace(',', '')
            
            # Convert to float and randomize (±50% of original)
            original_value = float(amount_str)
            variation = random.uniform(0.5, 1.5)  # 50% to 150% of original
            new_value = original_value * variation
            
            # Format back without commas
            formatted_amount = f"{new_value:.2f}"
            
            return f"{currency}{formatted_amount}"
        else:
            # If parsing fails, generate a random amount
            random_amount = random.uniform(1000, 100000)
            return f"HKD{random_amount:.2f}"
    except:
        # Fallback to random amount
        random_amount = random.uniform(1000, 100000)
        return f"HKD{random_amount:.2f}"

def randomize_amount_with_limit(original_amount: str, upper_limit: float) -> str:
    """Randomize an amount string with an upper limit constraint"""
    try:
        # Extract currency and numeric part
        match = re.match(r'([A-Z]{3})([0-9,]+\.?\d*)', original_amount)
        if match:
            currency = match.group(1)
            amount_str = match.group(2).replace(',', '')
            
            # Convert to float
            original_value = float(amount_str)
            
            # Calculate randomization range with upper limit constraint
            min_value = original_value * 0.5  # 50% of original as minimum
            max_value = min(original_value * 1.5, upper_limit - 0.01)  # Ensure it's less than upper_limit
            
            # If the min_value is already >= upper_limit, use a smaller range
            if min_value >= upper_limit:
                min_value = upper_limit * 0.1  # 10% of upper limit as minimum
                max_value = upper_limit - 0.01
            
            # Ensure max_value is greater than min_value
            if max_value <= min_value:
                max_value = min_value + 1
            
            # Generate new value within the constrained range
            new_value = random.uniform(min_value, max_value)
            
            # Format back without commas
            formatted_amount = f"{new_value:.2f}"
            
            return f"{currency}{formatted_amount}"
        else:
            # If parsing fails, generate a random amount under the limit
            random_amount = random.uniform(1000, min(100000, upper_limit - 0.01))
            return f"HKD{random_amount:.2f}"
    except:
        # Fallback to random amount under the limit
        random_amount = random.uniform(1000, min(100000, upper_limit - 0.01))
        return f"HKD{random_amount:.2f}"

def randomize_account_number(original_account: str) -> str:
    """Randomize an account number in format XXX-XXXXXX-XXX"""
    try:
        # Check if it matches the expected format
        if re.match(r'\d{3}-\d{6}-\d{3}', original_account):
            # Generate new random digits for each part
            part1 = f"{random.randint(100, 999)}"
            part2 = f"{random.randint(100000, 999999)}"
            part3 = f"{random.randint(100, 999)}"
            return f"{part1}-{part2}-{part3}"
        else:
            # For other formats, try to maintain the structure
            # Replace digits with random digits
            return re.sub(r'\d', lambda x: str(random.randint(0, 9)), original_account)
    except:
        # Fallback to standard format
        return f"{random.randint(100, 999)}-{random.randint(100000, 999999)}-{random.randint(100, 999)}"

def randomize_police_reference(original_ref: Any) -> Any:
    """Randomize police reference by selecting from predefined list and randomizing numbers"""
    if original_ref is None:
        return None
    
    # List of possible police reference values
    police_ref_options = [
        "police_reference",
        "POLICEREF2",
        "ESPS ■■■■/2024 and ERC24100■■■■■■■ (E-HUB-■■■)",
        "ESPS ■■■■■/2024 and TY RN ■■■■■■■ (DIT 4 ■■■■■■■)",
        "ESPS 7■■■■■■ and WCHDIV 25■■■■■ (DIT7-■■■■■)",
        "Policeref2",
        "POLICEREF5",
        "Policeref1",
        "NP RN 001",
        "STRN240■■■■",
        "ESPS ■■■■■/2024 and TY RN ■■■■■■■",
        "ESPS 1■■■■■■ and TMDIV 24■■■■■ (DIT3-■■■■■)",
        "YMT RN 2500■■■■■■■",
        "MK RN 2500■■■■■■■",
        "POLICEREF1",
        "POLICEREF3",
        "C RN 250■■■■■■■",
        "ESPS ■■/2025 and KT RN ■■■■■■■■ (DIT 2 ■■■■■■)",
        "YMT RN 2500",
        "ESPS ■■■/2025 and TYDIV ■■■■■■■ (DIT 7-■■■■■■■)",
        "ESPS ■■■/2025 and TSTDIV ■■■■■■■■ (DIT 3 ■■■■■■)",
        "DIT2-■■■■■",
        "DIT 7-■■■■■■■",
        "DIT3-■■■■■",
        "DIT8-■■■■■",
        "ESPS ■■■/2025 and MKDIST ■■■■■■■ (DIT 1 ■■■■■■)",
        "NTK RN 2500",
        "ESPS ■■■■/2024 and WTSDIST ■■■■■■■■ (DIT 5-■■■■■■■)",
        "SSRN250■■■■",
        "ESPS ■■■■/2025 and e-Hub ■■■■■■■■ (DIT 5-■■■■■)",
        "45663",
        "TSW RN 240■■■■■■■",
        "ESPS ■■■■/2024 and WCHDIV ■■■■■■■■ (DIT 7-■■■■■■■)",
        "YLRN 250■■■■",
        "WCH RN 2500■■■■■■■",
        "KTRN230■■■■",
        "TM 001",
        "ESPS ■■/2025 and KT RN ■■■■■■■■",
        "HH RN 250■■■■",
        "TSWRN240■■■■",
        "ESPS ■■■/2025 and WTSDIST ■■■■■■■■ (DIT 2 ■■■■■■■)",
        "KCRN240■■■■",
        "TYRN240■■■■",
        "NTK RN 2500■■■■■■■",
        "DIT7-■■■■■",
        "TY RN 240■■■■■■■",
        "ESPS ■■/2025 and e-Hub ■■■■■■■■ (E-HUB-■■■)",
        "ESPS  ■■■■/2024 and WTSDIST ■■■■■■■■ (DIT 5-■■■■■■■)",
        "ESPS 7■■■■■■ and NTKDIV 24■■■■■ (DIT2-■■■■■)",
        "TM RN 002"
    ]
    
    # Randomly select a police reference
    selected_ref = random.choice(police_ref_options)
    
    # Replace any existing numbers with random numbers (preserve number of digits)
    def replace_number(match):
        num_str = match.group(0)
        num_length = len(num_str)
        # Generate a random number with the same number of digits
        if num_length == 1:
            return str(random.randint(0, 9))
        else:
            min_val = 10**(num_length-1)
            max_val = 10**num_length - 1
            return str(random.randint(min_val, max_val))
    
    # Replace numbers in the selected reference
    randomized_ref = re.sub(r'\d+', replace_number, selected_ref)
    
    # Replace the ■ symbol with random single digits
    def replace_symbol(match):
        return str(random.randint(0, 9))
    
    # Replace ■ symbols with random digits
    randomized_ref = re.sub(r'■', replace_symbol, randomized_ref)
    
    return randomized_ref

def randomize_writ_no(original_writ: Any) -> Any:
    """Randomize writ number by selecting from predefined list and randomizing numbers"""
    if original_writ is None:
        return None
    
    # List of possible writ number values
    writ_no_options = [
        "67■■",
        "TM ■■■■",
        "3■■■/2025",
        "01■■■",
        "3■■■",
        "1■■■",
        "17■■■■",
        "001■■■",
        "TM12■■■/2024",
        "5■■■",
        "00■■■",
        "TM19■■ /2025",
        "12■■■",
        "011■■■",
        "TM■■■",
        "5■■/2025",
        "8■■■"
    ]
    
    # Randomly select a writ number
    selected_writ = random.choice(writ_no_options)
    
    # Replace any existing numbers with random numbers (preserve number of digits)
    def replace_number(match):
        num_str = match.group(0)
        num_length = len(num_str)
        # Generate a random number with the same number of digits
        if num_length == 1:
            return str(random.randint(0, 9))
        else:
            min_val = 10**(num_length-1)
            max_val = 10**num_length - 1
            return str(random.randint(min_val, max_val))
    
    # Replace numbers in the selected writ number
    randomized_writ = re.sub(r'\d+', replace_number, selected_writ)
    
    # Replace the ■ symbol with random single digits
    def replace_symbol(match):
        return str(random.randint(0, 9))
    
    # Replace ■ symbols with random digits
    randomized_writ = re.sub(r'■', replace_symbol, randomized_writ)
    
    return randomized_writ

def randomize_contact_person(original_contact: Any) -> Any:
    """Randomize contact person by selecting from predefined list and randomizing numbers"""
    if original_contact is None:
        return None
    
    # List of possible contact person values
    contact_person_options = [
        "PC 2■■■■",
        "PC■■■■■",
        "PC ■■■■■",
        "PC 6■■■■",
        "SGT 5■■■■",
        "PC 1■■■■",
        "SGT 2■■■■"
    ]
    
    # Randomly select a contact person
    selected_contact = random.choice(contact_person_options)
    
    # Replace any existing numbers with random numbers (preserve number of digits)
    def replace_number(match):
        num_str = match.group(0)
        num_length = len(num_str)
        # Generate a random number with the same number of digits
        if num_length == 1:
            return str(random.randint(0, 9))
        else:
            min_val = 10**(num_length-1)
            max_val = 10**num_length - 1
            return str(random.randint(min_val, max_val))
    
    # Replace numbers in the selected contact person
    randomized_contact = re.sub(r'\d+', replace_number, selected_contact)
    
    # Replace the ■ symbol with random single digits
    def replace_symbol(match):
        return str(random.randint(0, 9))
    
    # Replace ■ symbols with random digits
    randomized_contact = re.sub(r'■', replace_symbol, randomized_contact)
    
    return randomized_contact

# Bank name variations and their standardized codes
bank_mapping = {
    # Bank of China variations
    "boc": "boc",
    "bank of china": "boc",
    "bank of china limited": "boc",
    "bank of china ltd": "boc",
    "bank of china ltd.": "boc",
    "中国银行": "boc",
    "中國銀行": "boc",
    "china bank": "boc",
    
    # China Construction Bank variations
    "ccb": "ccb",
    "china construction bank": "ccb",
    "china construction bank corporation": "ccb",
    "china construction bank corp": "ccb",
    "china construction bank corp.": "ccb",
    "construction bank of china": "ccb",
    "中国建设银行": "ccb",
    "中國建設銀行": "ccb",
    
    # DBS Bank variations
    "dbs": "dbs",
    "dbs bank": "dbs",
    "dbs bank ltd": "dbs",
    "dbs bank ltd.": "dbs",
    "dbs bank limited": "dbs",
    "development bank of singapore": "dbs",
    "星展银行": "dbs",
    "星展銀行": "dbs",
    
    # Hang Seng Bank variations
    "hase": "hase",
    "hang seng": "hase",
    "hang seng bank": "hase",
    "hang seng bank ltd": "hase",
    "hang seng bank ltd.": "hase",
    "hang seng bank limited": "hase",
    "hang seng bank, limited": "hase",
    "heng sang bank": "hase",
    "hang sang bank": "hase",
    "hangseng bank": "hase",
    "hang seng bank (china)": "hase",
    "恒生": "hase",
    "恒生银行": "hase",
    "恆生銀行": "hase",
    "hsb": "hase",
    
    # HSBC variations
    "hsbc": "hsbc",
    "hongkong and shanghai banking corporation": "hsbc",
    "hongkong and shanghai banking corp": "hsbc",
    "hongkong and shanghai banking corp.": "hsbc",
    "the hongkong and shanghai banking corporation": "hsbc",
    "the hongkong and shanghai banking corporation limited": "hsbc",
    "the hongkong and shanghai banking corporation ltd": "hsbc",
    "the hongkong and shanghai banking corporation ltd.": "hsbc",
    "the hongkong and shanghai banking corporation limited (hsbc)": "hsbc",
    "hsbc bank": "hsbc",
    "hsbc bank plc": "hsbc",
    "汇丰银行": "hsbc",
    "匯豐銀行": "hsbc",
    
    # OCBC Bank variations
    "ocbc": "ocbc",
    "ocbc bank": "ocbc",
    "oversea-chinese banking corporation": "ocbc",
    "oversea-chinese banking corporation limited": "ocbc",
    "oversea chinese banking corporation": "ocbc",
    "oversea chinese banking corp": "ocbc",
    "oversea chinese banking corp.": "ocbc",
    "华侨银行": "ocbc",
    "華僑銀行": "ocbc",
    
    # Standard Chartered variations
    "scb": "scb",
    "standard chartered": "scb",
    "standard chartered bank": "scb",
    "standard chartered bank limited": "scb",
    "standard chartered bank ltd": "scb",
    "standard chartered bank ltd.": "scb",
    "渣打银行": "scb",
    "渣打銀行": "scb",
    
    # UOB variations
    "uob": "uob",
    "united overseas bank": "uob",
    "united overseas bank limited": "uob",
    "united overseas bank ltd": "uob",
    "united overseas bank ltd.": "uob",
    "大华银行": "uob",
    "大華銀行": "uob",
    
    # ICBC variations
    "icbc": "icbc",
    "industrial and commercial bank of china": "icbc",
    "industrial and commercial bank of china limited": "icbc",
    "industrial and commercial bank of china ltd": "icbc",
    "industrial and commercial bank of china ltd.": "icbc",
    "industrial & commercial bank of china": "icbc",
    "中国工商银行": "icbc",
    "中國工商銀行": "icbc",
    
    # Bank of Communications variations
    "bocom": "bocom",
    "bank of communications": "bocom",
    "bank of communications co., ltd": "bocom",
    "bank of communications co., ltd.": "bocom",
    "bank of communications co. ltd": "bocom",
    "bank of communications co. ltd.": "bocom",
    "交通银行": "bocom",
    "交通銀行": "bocom",
    
    # Agricultural Bank of China variations
    "abc": "abc",
    "agricultural bank of china": "abc",
    "agricultural bank of china limited": "abc",
    "agricultural bank of china ltd": "abc",
    "agricultural bank of china ltd.": "abc",
    "中国农业银行": "abc",
    "中國農業銀行": "abc",
    
    # Citibank variations
    "citi": "citi",
    "citibank": "citi",
    "citigroup": "citi",
    "citibank n.a.": "citi",
    "citibank na": "citi",
    "花旗银行": "citi",
    "花旗銀行": "citi",
}

# Map from bank codes to full names for randomization
bank_code_to_full_name = {
    "boc": "Bank of China (Hong Kong) Limited",
    "hsbc": "The Hongkong and Shanghai Banking Corporation Limited",
    "hase": "Hang Seng Bank Ltd.",
    "scb": "Standard Chartered Bank (Hong Kong) Limited",
    "ccb": "China Construction Bank (Asia) Corporation Limited",
    "dbs": "DBS Bank (Hong Kong) Limited",
    "citi": "Citibank (Hong Kong) Limited",
    "ocbc": "OCBC Wing Hang Bank Limited",
    "icbc": "Industrial and Commercial Bank of China (Asia) Limited",
    "bocom": "Bank of Communications (Hong Kong) Limited",
    "abc": "Agricultural Bank of China (Hong Kong) Limited",
    "uob": "United Overseas Bank (Hong Kong) Limited"
}

# Additional banks for randomization that don't have abbreviations
additional_banks = [
    "Bank of East Asia, Limited",
    "Shanghai Commercial Bank Limited",
    "Dah Sing Bank, Limited",
    "Chong Hing Bank Limited",
    "China CITIC Bank International Limited",
    "Public Bank (Hong Kong) Limited",
    "Nanyang Commercial Bank, Limited",
    "Tai Yau Bank, Limited",
    "Chiyu Banking Corporation Limited",
    "Fubon Bank (Hong Kong) Limited"
]

def get_bank_variations(bank_name_or_code: str) -> List[str]:
    """
    Get all variations of a bank name based on the bank_mapping dictionary.
    
    Args:
        bank_name_or_code: A bank name or code
        
    Returns:
        A list of all possible variations of the bank name
    """
    # Normalize the input to lowercase for case-insensitive matching
    normalized_input = bank_name_or_code.lower()
    
    # If the input is a bank code, find all variations that map to this code
    if normalized_input in bank_code_to_full_name:
        code = normalized_input
        variations = [k for k, v in bank_mapping.items() if v == code]
        variations.append(bank_code_to_full_name[code])  # Add the full name
        return variations
    
    # If the input is a bank name, find its code and then all variations
    for name, code in bank_mapping.items():
        if normalized_input == name.lower():
            variations = [k for k, v in bank_mapping.items() if v == code]
            variations.append(bank_code_to_full_name[code])  # Add the full name
            return variations
    
    # If the input is not in the mapping, return just the input
    return [bank_name_or_code]

def randomize_bank(original_bank: Any) -> Tuple[Any, str]:
    """
    Randomize bank name by selecting from a predefined list.
    If the bank is None or an empty string, it is not randomized.
    Returns the new bank name and its code for tracking variations.
    """
    if original_bank is None or original_bank == "":
        return original_bank, None
    
    # Combine bank codes and additional banks for randomization
    all_bank_options = list(bank_code_to_full_name.values()) + additional_banks
    
    # Randomly select a bank
    selected_bank = random.choice(all_bank_options)
    
    # Find the code for the selected bank (if it has one)
    selected_bank_code = None
    for code, full_name in bank_code_to_full_name.items():
        if selected_bank == full_name:
            selected_bank_code = code
            break
    
    return selected_bank, selected_bank_code

def randomize_name(original_name: Any) -> Tuple[Any, List[Tuple[str, str]], bool]:
    """
    Randomize name by selecting from a predefined list.
    If the name contains special characters (non-alphanumeric, non-space), it is skipped.
    Returns the new name, a list of part-by-part changes, and a boolean indicating if it was randomized.
    """
    if original_name is None:
        return None, [], True  # Consider None as "clean" and successfully processed

    # Check for any characters that are not letters, numbers, or spaces.
    # This will skip names with commas, pipes, or other symbols.
    if not re.match(r'^[A-Za-z0-9\s]+$', str(original_name)):
        return original_name, [], False  # Contains special characters, skip randomization

    name_options = [
        "CHAN TAI MAN", "WONG SIU MING", "LEE KA WAI", "LAM HOI SHAN", "CHEN WEI HONG",
        "LIU MING FUNG", "NG HOK YIN", "TANG SIU KWAN", "YEUNG KAI CHUNG", "HO WING KEI",
        "MA CHI KEUNG", "TSANG MEI LIN", "CHENG HO YAN", "LAU SIN YEE", "SIU WAI MING",
        "FUNG KAM LING", "LEUNG CHI FAI", "KWOK HOI KWAN", "POON SIU FONG", "YIP MING WAH",
        "CHOW KA YAN", "LO HOI NING", "TONG SIU WAI", "CHEUNG TAK SHING", "WU MEI LING",
        "KAN CHI WING", "SO SIU YAN", "AU HOI LAAM", "MUI KA MING", "YAU SIN WAI",
        "HUNG CHI HO", "CHIU MEI FONG", "KO HOI CHING", "TSE KA LEI", "SIT SIU MING",
        "YUEN CHI KEUNG", "MOK HOI YAN", "TAM SIU KUEN", "LUNG KA WAI", "CHU HOI SHAN"
    ]
    
    selected_name = random.choice(name_options)
    
    # Split names into parts
    original_parts = str(original_name).split()
    new_parts = selected_name.split()
    
    # Create a list of changes for each part of the name
    part_changes = []
    for i in range(min(len(original_parts), len(new_parts))):
        part_changes.append((original_parts[i], new_parts[i]))
        
    return selected_name, part_changes, True

def randomize_json_fields(json_data: Dict, changes: List[Tuple[str, str]]) -> Dict:
    """Recursively randomize specific fields in JSON data and track changes"""
    if isinstance(json_data, dict):
        new_data = {}
        for key, value in json_data.items():
            if key == "date" and isinstance(value, str):
                new_value = randomize_date(value)
                if new_value != value:
                    changes.append((value, new_value))
                new_data[key] = new_value
            elif key == "amount" and isinstance(value, (str, int, float)):
                # Check if there's a cancel_amount_requested in the same transaction
                cancel_amount_limit = None
                if "cancel_amount_requested" in json_data and json_data["cancel_amount_requested"] is not None:
                    try:
                        cancel_amount_limit = float(json_data["cancel_amount_requested"])
                    except (ValueError, TypeError):
                        cancel_amount_limit = None
                
                # Handle both string and numeric amounts
                original_str = str(value)
                if isinstance(value, (int, float)):
                    # For numeric amounts, create a currency string
                    if cancel_amount_limit is not None:
                        # Use constrained randomization with upper limit
                        new_value_str = randomize_amount_with_limit(f"HKD{value}", cancel_amount_limit)
                    else:
                        new_value_str = randomize_amount(f"HKD{value}")
                    
                    # Extract the numeric part (formatted) and the float value
                    amount_match = re.search(r'[A-Z]{3}([0-9,]+\.?\d*)', new_value_str)
                    if amount_match:
                        formatted_new_amount = amount_match.group(1)
                        new_numeric_value = float(formatted_new_amount.replace(',', ''))
                        
                        if abs(new_numeric_value - value) > 1e-9:
                            # Store the original unformatted value and the new formatted value for replacement
                            changes.append((original_str, formatted_new_amount))
                        
                        new_data[key] = new_numeric_value
                    else:
                        new_data[key] = value # Fallback
                else:
                    if cancel_amount_limit is not None:
                        # Use constrained randomization with upper limit
                        new_value = randomize_amount_with_limit(value, cancel_amount_limit)
                    else:
                        new_value = randomize_amount(value)
                    
                    if new_value != value:
                        changes.append((value, new_value))
                    new_data[key] = new_value
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
                new_value, bank_code = randomize_bank(value)
                if new_value != value:
                    # Store the original bank and the new bank for replacement
                    changes.append(("BANK:" + str(value), str(new_value)))
                new_data[key] = new_value
            elif key == "name" and isinstance(value, (str, type(None))):
                # Handle name fields, checking for special characters
                new_value, part_changes, was_randomized = randomize_name(value)
                if was_randomized:
                    if new_value != value:
                        # Add granular changes for individual name parts
                        changes.extend(part_changes)
                else:
                    # Name was not randomized, so add a note to the diff
                    changes.append((f"Name not randomized due to special characters: '{value}'", "SKIPPED"))
                new_data[key] = new_value
            elif key in ["from", "to"] and isinstance(value, dict):
                # Handle from/to objects that contain name fields
                new_value = randomize_json_fields(value, changes)
                new_data[key] = new_value
            else:
                new_data[key] = randomize_json_fields(value, changes)
        return new_data
    elif isinstance(json_data, list):
        return [randomize_json_fields(item, changes) for item in json_data]
    else:
        return json_data

def apply_changes_to_input(input_text: str, changes: List[Tuple[str, str]]) -> str:
    """Apply all the changes to the input text sequentially."""
    modified_input = input_text
    
    for old_value, new_value in changes:
        if new_value == "SKIPPED":
            continue
        
        # Check if this is a bank replacement (marked with "BANK:" prefix)
        if old_value.startswith("BANK:"):
            original_bank = old_value[5:]  # Remove the "BANK:" prefix
            
            # Skip empty banks
            if not original_bank or original_bank.lower() == "none":
                continue
                
            # Get all variations of the original bank
            original_variations = get_bank_variations(original_bank)
            
            # Add common variations with different capitalizations and suffixes
            extended_variations = []
            for var in original_variations:
                if not var:  # Skip empty variations
                    continue
                # Add original variation
                extended_variations.append(var)
                # Add variations with different capitalizations
                extended_variations.append(var.upper())
                extended_variations.append(var.lower())
                extended_variations.append(var.title())
                # Add variations with common suffixes
                extended_variations.append(f"{var} HK")
                extended_variations.append(f"{var} (HK)")
            
            # Remove duplicates and sort by length (longest first)
            extended_variations = sorted(set(extended_variations), key=len, reverse=True)
            
            # Replace all variations in the text
            for variation in extended_variations:
                # Simple string replacement (case-sensitive)
                if variation in modified_input:
                    modified_input = modified_input.replace(variation, new_value)
                
                # Case-insensitive replacement
                try:
                    pattern = re.compile(re.escape(variation), re.IGNORECASE)
                    modified_input = pattern.sub(new_value, modified_input)
                except re.error:
                    # Fallback for regex errors
                    pass
            
            continue  # Skip the rest of the loop for bank replacements
            
        old_value_str = str(old_value)
        
        # Try to convert to float. If it works, it's a numeric change from the JSON (e.g., 40000.0)
        old_float = None
        try:
            old_float = float(old_value_str)
        except (ValueError, TypeError):
            pass

        if old_float is not None:
            # This is a numeric value. It needs to find variations in the text (e.g., 40,000 or 40000 or 40000.00)
            old_int = int(old_float)
            search_variations = [
                f"{old_int:,}.00",
                f"{old_int}.00",
                f"{old_int:,}",
                str(old_int),
                str(old_float)
            ]
            if '.' in old_value_str:
                 search_variations.append(f"{old_int:,}.{old_value_str.split('.')[1]}")

            search_variations = sorted(list(set(search_variations)), key=len, reverse=True)
            
            replaced = False
            for var in search_variations:
                # For variations with commas, a simple string search is often safe enough.
                if ',' in var:
                    if var in modified_input:
                        modified_input = modified_input.replace(var, str(new_value), 1)
                        replaced = True
                        break
                else:
                    # For variations without commas, use word boundaries to avoid replacing "5000" in "15000".
                    pattern = re.compile(r'\b' + re.escape(var) + r'\b')
                    if pattern.search(modified_input):
                        modified_input = pattern.sub(str(new_value), modified_input, count=1)
                        replaced = True
                        break
            
            if not replaced:
                # A final fallback for this numeric case if no variations were found
                modified_input = modified_input.replace(old_value_str, str(new_value), 1)

        elif re.match(r'^[A-Z]{3}', old_value_str):
            # This handles full currency strings like "HKD40,000.00".
            # A simple replacement is best here, without word boundaries.
            modified_input = modified_input.replace(old_value_str, str(new_value), 1)

        else:
            # This handles non-numeric name parts like "CHAN".
            # Use strict word boundaries to prevent replacing substrings in other words.
            try:
                pattern = re.compile(r'\b' + re.escape(old_value_str) + r'\b', re.IGNORECASE)
                if pattern.search(modified_input):
                    modified_input = pattern.sub(str(new_value), modified_input, count=1)
            except re.error:
                # Fallback for regex errors
                modified_input = modified_input.replace(old_value_str, str(new_value), 1)
                
    return modified_input

def format_diff(changes: List[Tuple[str, str]]) -> str:
    """Format the changes as a diff string"""
    if not changes:
        return "No changes"
    
    diff_lines = []
    for old_value, new_value in changes:
        diff_lines.append(f"{old_value} --> {new_value}")
    
    return "\n".join(diff_lines)

def get_randomization_count(type_name):
    """Get number of additional randomized sets based on type"""
    if type_name in ['ADCC', 'ODFT']:
        return 6
    elif type_name == 'Search Warrant':
        return 4
    else:  # HSBC Referral, UAR, Police Letter
        return 3

def main():
    """
    Main function to process the CSV file with type-specific randomizations
    Appends randomized rows instead of creating new columns
    Maintains global set numbering and case number increments
    """
    # Set random seed for reproducibility (optional)
    random.seed(42)
    
    # Get CSV file path from user
    csv_file_path = input("Enter the path to your CSV file (or press Enter to use default): ").strip()
    if not csv_file_path:
        csv_file_path = 'Dataset_Source_v5_updated_with_groundtruth.csv'  # Default to your output file
    
    # Read the CSV file
    print(f"Loading CSV file: {csv_file_path}...")
    try:
        df = pd.read_csv(csv_file_path, na_filter=False)
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")
        return
    
    # Initialize global set number based on existing data
    initialize_global_set_number(df)
    
    # Display available columns
    print("\nAvailable columns in the CSV file:")
    for i, col in enumerate(df.columns, 1):
        print(f"{i}. {col}")
    
    # Prompt user for column names
    print("\nPlease specify which columns to use:")
    
    # Get original input column
    while True:
        try:
            input_choice = input("Enter the number or name of the column containing the original input text (default: Input): ").strip()
            if not input_choice:
                input_column = 'Input'
                if input_column in df.columns:
                    break
                else:
                    print(f"Default column '{input_column}' not found.")
                    continue
            elif input_choice.isdigit():
                input_col_index = int(input_choice) - 1
                if 0 <= input_col_index < len(df.columns):
                    input_column = df.columns[input_col_index]
                    break
                else:
                    print(f"Invalid number. Please enter a number between 1 and {len(df.columns)}")
            elif input_choice in df.columns:
                input_column = input_choice
                break
            else:
                print(f"Column '{input_choice}' not found. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or column name.")
    
    # Get ground truth JSON column
    while True:
        try:
            json_choice = input("Enter the number or name of the column containing the ground truth JSON (default: Ground Truth): ").strip()
            if not json_choice:
                json_column = 'Ground Truth'
                if json_column in df.columns:
                    break
                else:
                    print(f"Default column '{json_column}' not found.")
                    continue
            elif json_choice.isdigit():
                json_col_index = int(json_choice) - 1
                if 0 <= json_col_index < len(df.columns):
                    json_column = df.columns[json_col_index]
                    break
                else:
                    print(f"Invalid number. Please enter a number between 1 and {len(df.columns)}")
            elif json_choice in df.columns:
                json_column = json_choice
                break
            else:
                print(f"Column '{json_choice}' not found. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or column name.")
    
    # Get transaction records column
    while True:
        try:
            transaction_choice = input("Enter the number or name of the column containing the transaction records (default: Transactions): ").strip()
            if not transaction_choice:
                transaction_column = 'Transactions'
                if transaction_column in df.columns:
                    break
                else:
                    print(f"Default column '{transaction_column}' not found.")
                    continue
            elif transaction_choice.isdigit():
                transaction_col_index = int(transaction_choice) - 1
                if 0 <= transaction_col_index < len(df.columns):
                    transaction_column = df.columns[transaction_col_index]
                    break
                else:
                    print(f"Invalid number. Please enter a number between 1 and {len(df.columns)}")
            elif transaction_choice in df.columns:
                transaction_column = transaction_choice
                break
            else:
                print(f"Column '{transaction_choice}' not found. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or column name.")
    
    print(f"\nUsing columns:")
    print(f"- Original input: '{input_column}'")
    print(f"- Ground truth JSON: '{json_column}'")
    print(f"- Transaction records: '{transaction_column}'")
    print()
    
    # Add Randomization Set column to original data if it doesn't exist
    if 'Randomization Set' not in df.columns:
        df['Randomization Set'] = 0  # 0 for original
    
    # Add Diff column to original data (empty for original)
    if 'Diff' not in df.columns:
        df['Diff'] = "No changes"
    
    # List to store all DataFrames (original + randomized versions)
    all_dataframes = [df.copy()]  # Start with original DataFrame
    
    # Group by Type and create randomized sets
    for type_name in df['Type'].unique():
        type_rows = df[df['Type'] == type_name].copy()
        randomization_count = get_randomization_count(type_name)
        
        print(f"Creating {randomization_count} randomized sets for Type: {type_name}")
        
        for randomization_num in range(1, randomization_count + 1):
            print(f"  Processing randomization set {randomization_num} for {type_name}...")
            
            # Create a copy of the type-specific rows
            randomized_df = type_rows.copy()
            randomized_df['Randomization Set'] = randomization_num
            
            # Get the next global set number and update Set Number column
            current_set_number = get_next_set_number()
            randomized_df['Set Number'] = current_set_number
            
            # Calculate case number increment based on set number
            case_increment = current_set_number * 50
            if 'Case Number' in randomized_df.columns:
                randomized_df['Case Number'] = randomized_df['Original Case Number'] + case_increment
            
            # Process each row for this randomization
            diff_list = []
            for index, row in randomized_df.iterrows():
                # Get the original input, ground truth, and transactions
                original_input = str(row[input_column])
                ground_truth_str = str(row[json_column])
                original_transactions = str(row[transaction_column])
                
                try:
                    # Extract JSON from markdown code blocks if present
                    json_content = ground_truth_str
                    if ground_truth_str.strip().startswith('```json'):
                        # Extract content between ```json and ```
                        match = re.search(r'```json\s*(.*?)\s*```', ground_truth_str, re.DOTALL)
                        if match:
                            json_content = match.group(1).strip()
                        else:
                            raise ValueError("Could not extract JSON from markdown code block")
                    
                    # Parse the ground truth JSON
                    ground_truth_json = json.loads(json_content)
                    
                    # Track changes for this randomization
                    changes = []
                    
                    # Randomize the JSON fields
                    randomized_json = randomize_json_fields(ground_truth_json, changes)
                    
                    # Apply changes to input text
                    randomized_input = apply_changes_to_input(original_input, changes)
                    
                    # Apply changes to transaction records
                    randomized_transactions = apply_changes_to_input(original_transactions, changes)
                    
                    # Convert randomized JSON back to string
                    randomized_ground_truth_str = json.dumps(randomized_json, indent=2, ensure_ascii=False)
                    
                    # Format the diff
                    diff_str = format_diff(changes)
                    
                    # Update the randomized DataFrame with the new values
                    randomized_df.at[index, input_column] = randomized_input
                    randomized_df.at[index, json_column] = randomized_ground_truth_str
                    randomized_df.at[index, transaction_column] = randomized_transactions
                    diff_list.append(diff_str)
                    
                except Exception as e:
                    print(f"Error processing row {index}, randomization {randomization_num}: {str(e)}")
                    # Keep original values in case of error
                    diff_list.append(f"Error: {str(e)}")
            
            # Add the diff column
            randomized_df['Diff'] = diff_list
            
            # Add this randomized DataFrame to our list
            all_dataframes.append(randomized_df)
    
    # Concatenate all DataFrames (original + all randomized versions)
    final_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Before saving, ensure all NaN values are replaced with empty strings for specific columns
    columns_to_clean = ['Transactions', 'Input', 'Instruction', 'Ground Truth']
    for col in columns_to_clean:
        if col in final_df.columns:
            final_df[col] = final_df[col].fillna('')
    
    # Save to new CSV file
    input_dir = os.path.dirname(csv_file_path)
    input_filename = os.path.basename(csv_file_path)
    input_name, input_ext = os.path.splitext(input_filename)
    
    output_filename = os.path.join(input_dir, f'{input_name}_RANDOMIZED_ROWS{input_ext}')
    
    final_df.to_csv(output_filename, index=False, encoding='utf-8-sig', na_rep='')
    
    print(f"Randomization complete! Saved to: {output_filename}")
    print(f"Original rows: {len(df)}")
    print(f"Final global set number: {global_set_number}")
    
    # Print breakdown by type
    total_randomized = 0
    for type_name in df['Type'].unique():
        original_count = len(df[df['Type'] == type_name])
        randomization_count = get_randomization_count(type_name)
        total_for_type = original_count * randomization_count
        total_randomized += total_for_type
        print(f"  {type_name}: {original_count} original × {randomization_count} randomizations = {total_for_type} randomized rows")
    
    print(f"Total rows in output: {len(final_df)} (Original: {len(df)} + Randomized: {total_randomized})")

if __name__ == "__main__":
    print("CSV Data Randomizer - Type-Specific Row Appender Version")
    print("======================================================")
    print("Randomization counts by Type:")
    print("- ADCC & ODFT: 6 additional sets")
    print("- Search Warrant: 4 additional sets") 
    print("- Other types (HSBC Referral, UAR, Police Letter): 3 additional sets")
    print()
    
    main()
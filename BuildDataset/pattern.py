import random
import re
from typing import List, Tuple

# Document type specific randomization counts
RANDOMIZATION_COUNTS = {
    'ADCC': 6,
    'ODFT': 6,
    'Search Warrant': 4,
    'HSBC Referral': 3,
    'UAR': 3,
    'Police Letter': 3,
}

# Document types that should have bank names randomized
BANK_RANDOMIZATION_TYPES = ['ADCC', 'Police Letter', 'Search Warrant']

# Document types that have cancel_amount_requested
UAR_TYPES = ['UAR']

# Fields that should NOT be randomized
EXCLUDED_FIELDS = ['currency', 'channel', 'can_be_located', 'transaction_references']

# Bank mapping: variants -> root bank
BANK_VARIANT_TO_ROOT = {
    # Bank of China variations
    "BOC": "boc",
    "boc": "boc",
    "bank of china": "boc",
    "bank of china limited": "boc",
    "bank of china ltd": "boc",
    "bank of china ltd.": "boc",
    "bank of china (hong kong) limited": "boc",
    "中国银行": "boc",
    "中國銀行": "boc",
    
    # China Construction Bank variations
    "CCB": "ccb",
    "CCBA": "ccb",
    "ccb": "ccb",
    "ccba": "ccb",
    "china construction bank": "ccb",
    "china construction bank corporation": "ccb",
    "china construction bank (asia) corporation limited": "ccb",
    "china construction bank asia": "ccb",
    "中国建设银行": "ccb",
    "中國建設銀行": "ccb",
    
    # DBS Bank variations
    "DBS": "dbs",
    "dbs": "dbs",
    "dbs bank": "dbs",
    "dbs bank ltd": "dbs",
    "dbs bank ltd.": "dbs",
    "dbs bank limited": "dbs",
    "dbs bank (hong kong) limited": "dbs",
    "development bank of singapore": "dbs",
    "星展银行": "dbs",
    "星展銀行": "dbs",
    
    # Hang Seng Bank variations
    "HASE": "hangseng",
    "HSB": "hangseng",
    "hase": "hangseng",
    "hsb": "hangseng",
    "hang seng": "hangseng",
    "hang seng bank": "hangseng",
    "hang seng bank ltd": "hangseng",
    "hang seng bank ltd.": "hangseng",
    "hang seng bank limited": "hangseng",
    "恒生银行": "hangseng",
    "恆生銀行": "hangseng",
    
    # HSBC variations
    "HSBC": "hsbc",
    "hsbc": "hsbc",
    "hongkong and shanghai banking corporation": "hsbc",
    "the hongkong and shanghai banking corporation": "hsbc",
    "the hongkong and shanghai banking corporation limited": "hsbc",
    "hsbc bank": "hsbc",
    "hsbc hong kong": "hsbc",
    "汇丰银行": "hsbc",
    "滙豐銀行": "hsbc",
    
    # Standard Chartered variations
    "SCB": "scb",
    "scb": "scb",
    "standard chartered": "scb",
    "standard chartered bank": "scb",
    "standard chartered bank (hong kong) limited": "scb",
    "渣打银行": "scb",
    "渣打銀行": "scb",
    
    # OCBC variations
    "OCBC": "ocbc",
    "ocbc": "ocbc",
    "ocbc bank": "ocbc",
    "ocbc wing hang": "ocbc",
    "ocbc wing hang bank": "ocbc",
    "ocbc wing hang bank limited": "ocbc",
    "wing hang bank": "ocbc",
    "华侨银行": "ocbc",
    "華僑銀行": "ocbc",
    
    # Citibank variations
    "CITI": "citi",
    "citi": "citi",
    "citibank": "citi",
    "citibank hong kong": "citi",
    "citibank (hong kong) limited": "citi",
    "花旗银行": "citi",
    "花旗銀行": "citi",
    
    # Bank of Communications variations
    "BOCOM": "bocom",
    "bocom": "bocom",
    "bank of communications": "bocom",
    "bank of com": "bocom",
    "bank of communications (hong kong) limited": "bocom",
    "交通银行": "bocom",
    "交通銀行": "bocom",
    
    # Industrial and Commercial Bank of China variations
    "ICBC": "icbc",
    "icbc": "icbc",
    "industrial and commercial bank of china": "icbc",
    "icbc (asia) limited": "icbc",
    "industrial and commercial bank of china (asia) limited": "icbc",
    "工商银行": "icbc",
    "工商銀行": "icbc",
}

# Root bank to full name mapping (for replacement)
BANK_ROOT_TO_FULL_NAME = {
    "boc": "Bank of China (Hong Kong) Limited",
    "ccb": "China Construction Bank (Asia) Corporation Limited", 
    "dbs": "DBS Bank (Hong Kong) Limited",
    "hangseng": "Hang Seng Bank Ltd.",
    "hsbc": "The Hongkong and Shanghai Banking Corporation Limited",
    "scb": "Standard Chartered Bank (Hong Kong) Limited",
    "ocbc": "OCBC Wing Hang Bank Limited",
    "citi": "Citibank (Hong Kong) Limited",
    "bocom": "Bank of Communications (Hong Kong) Limited",
    "icbc": "Industrial and Commercial Bank of China (Asia) Limited",
}

# Date format patterns for parsing and preserving format
DATE_FORMAT_PATTERNS = [
    (r'\b(\d{4})-(\d{2})-(\d{2})\b', '%Y-%m-%d'),  # YYYY-MM-DD
    (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', '%m/%d/%Y'),  # MM/DD/YYYY
    (r'\b(\d{1,2})-(\d{1,2})-(\d{4})\b', '%m-%d-%Y'),  # MM-DD-YYYY
]

# Amount format patterns for parsing and preserving format
AMOUNT_FORMAT_PATTERNS = [
    (r'\b([A-Z]{3})([\d,]+\.?\d*)\b', 'currency_prefix'),  # HKD40,000.00
    (r'\b(\$)([\d,]+\.?\d*)\b', 'dollar_prefix'),  # $40,000.00
    (r'\b([\d,]+\.?\d*)\s*([A-Z]{3})\b', 'currency_suffix'),  # 40,000.00 HKD
    (r'\b([\d,]+\.?\d*)\b(?=\s|$)', 'number_only'),  # Standalone numbers
]

# Name validation pattern
NAME_VALIDATION_PATTERN = r'^[A-Za-z0-9\s]+$'

# Replacement options - using template randomization with {num}, {code}, {digit}
REPLACEMENT_OPTIONS = {
    'police_references': [
        "ESPS {num}/2024 and ERC24100{num}",
        "ESPS {num}/2024 and TY RN {num}",
        "ESPS {digit}{num} and WCHDIV {num}",
        "ESPS {num}/2025 and MKDIST {num}",
        "ESPS {num}/2024 and WTSDIST {num}",
        "TSW RN {num}",
        "YMT RN {num}",
        "MK RN {num}",
        "C RN {num}",
        "NTK RN {num}",
        "HH RN {num}",
        "STRN{num}",
        "SSRN{num}",
        "YLRN {num}",
        "WCH RN {num}",
        "KTRN{num}",
        "TSWRN{num}",
        "KCRN{num}",
        "TYRN{num}",
        "TM RN {num}",
        "POLICEREF{num}",
        "Policeref{num}"
    ],
    
    'writ_numbers': [
        "67{num}",
        "TM {num}",
        "3{num}/2025",
        "01{num}",
        "3{num}",
        "1{num}",
        "17{num}",
        "001{num}",
        "TM12{num}/2024",
        "5{num}",
        "00{num}",
        "TM19{num} /2025",
        "12{num}",
        "011{num}",
        "TM{num}",
        "5{num}/2025",
        "8{num}"
    ],
    
    'contact_persons': [
        "PC 2{num}",
        "PC{num}",
        "PC {num}",
        "PC 6{num}",
        "SGT 5{num}",
        "PC 1{num}",
        "SGT 2{num}",
        "WSGT {num}",
        "SSGT {num}",
        "CSGT {num}"
    ],
    
    'police_teams': [
        "DIT {digit} {num}",
        "DIT {digit}-{num}",
        "DIT{digit}-{num}",
        "DIT {digit} KWTDIST",
        "DIT {digit} KCDIST",
        "DTFCS {digit} YLDIST",
        "E-HUB-{num}",
        "District Crime Squad One, Tuen Mun Police District",
        "District Crime Squad Team {digit} of Western District",
        "District Investigation Team {digit}, Shatin District, Shatin Police Station",
        "District Investigation Team {digit}, Eastern District, North Point Police Station",
        "District Investigation Team {digit}, Kwai Tsing District, Kwai Chung Police Station",
        "District Investigation Team {digit}, Tai Po District, Tai Po Police Station",
        "District Investigation Team {digit}, Kowloon City District, Hung Hom Police Station",
        "District Investigation Team {digit}, Shamshuipo District, Sham Shui Po Police Station",
        "District Investigation Team {digit}, Tuen Mun District, Tuen Mun Police Station",
        "District Investigation Team {digit}, Yuen Long District",
        "District Investigation Team {digit} of Western District",
        "District Investigation Team {digit}, Mong Kok District, Mong Kok Police Station",
        "District Investigation Team {digit}, Sau Mau Ping District, Sau Mau Ping Police Station",
        "District Investigation Team {digit}, Tuen Mun District, New Territories North",
        "District Investigation Team {digit}, Western District, Aberdeen Police Station",
        "District Investigation Team {digit}, Central District, Central Police Station",
        "District Investigation Team {digit}, Lantau District",
        "District Investigation Team {digit}, Kowloon City Police District",
        "District Investigation Team {digit}, Kwun Tong District, Kwun Tong Police Station",
        "District Investigation Team {digit}, Sha Tin District, Hong Kong POLICE",
        "District Investigation Team {digit}, Wan Chai District, Wan Chai Police Station",
        "District Investigation Team {digit}, Yau Tsim District, Tsim Sha Tsui Police Station",
        "District Technology & Financial Crime Unit, Tuen Mun District",
        "District Technology & Financial Crime Unit, Tuen Mun, Tuen Mun District, Tuen Mun Police Station",
        "District Technology and Financial Crime Squad {digit} of Yuen Long District",
        "District Technology and Financial Crime Squad Yuen Long District, Hong Kong Police Force",
        "District Technology and Financial Crime Squad of Tai Po Police District",
        "District Technology and Financial Crime Squad, Kwun Tong District, Hong Kong Police Force",
        "District investigation Team {digit} Western District",
        "Miscellaneous Enquiries Sub Unit of Kwai Chung Division"
    ],
    
    'names': [
        "CHAN TAI MAN", "WONG SIU MING", "LEE KA WAI", "LAM HOI SHAN",
        "CHEN WEI HONG", "LIU MING FUNG", "NG HOK YIN", "TANG SIU KWAN",
        "YEUNG KAI CHUNG", "HO WING KEI", "MA CHI KEUNG", "TSANG MEI LIN",
    ]
}

# Special ADCC patterns that appear in actual text (with real numbers)
ADCC_SPECIAL_PATTERNS = {
    'police_team_patterns': [
        r'\bE-HUB-\d+\b',  # E-HUB-123
        r'\bDIT\s*\d+\s*-\s*\d+\b',  # DIT 7-1234567, DIT7-12345
        r'\bDIT\s+\d+\s+\d+\b',  # DIT 4 1234567
        r'\bDIT\d+-\d+\b',  # DIT2-12345, DIT3-12345, DIT8-12345
    ],
    
    'police_reference_patterns': [
        r'\bESPS\s+\d+/\d{4}\s+and\s+[A-Z]+\d+\s*\([^)]+\)\b',  # ESPS 1234/2024 and ERC241001234567 (E-HUB-123)
        r'\bESPS\s+\d+\s+and\s+[A-Z]+\s+\d+\s*\([^)]+\)\b',  # ESPS 71234 and WCHDIV 251234 (DIT7-12345)
    ]
}

# ADCC replacement templates for special patterns
ADCC_REPLACEMENT_TEMPLATES = {
    'police_teams': [
        "E-HUB-{code}",
        "DIT {digit}-{num}",
        "DIT{digit}-{num}",
        "DIT {digit} {num}",
    ],
    
    'police_references': [
        "ESPS {num}/2024 and ERC24100{num}",
        "ESPS {num}/2024 and TY RN {num}",
        "ESPS {digit}{num} and WCHDIV {num}",
        "ESPS {num}/2025 and MKDIST {num}",
        "ESPS {num}/2024 and WTSDIST {num}",
    ]
}

def replace_symbol_with_digit(match):
    """Replace ■ symbol with random digit"""
    return str(random.randint(0, 9))

def process_adcc_special_patterns(text: str, document_type: str) -> List[Tuple[str, str]]:
    """Process special ADCC patterns that appear in actual text"""
    changes = []
    
    if document_type != 'ADCC':
        return changes
    
    # Process police team patterns
    for pattern in ADCC_SPECIAL_PATTERNS['police_team_patterns']:
        matches = re.finditer(pattern, text)
        for match in matches:
            original_value = match.group(0)
            
            # Generate replacement
            template = random.choice(ADCC_REPLACEMENT_TEMPLATES['police_teams'])
            new_value = replace_placeholders(template)
            
            changes.append((original_value, new_value))
    
    # Process police reference patterns  
    for pattern in ADCC_SPECIAL_PATTERNS['police_reference_patterns']:
        matches = re.finditer(pattern, text)
        for match in matches:
            original_value = match.group(0)
            
            # Generate replacement
            template = random.choice(ADCC_REPLACEMENT_TEMPLATES['police_references'])
            new_value = replace_placeholders(template)
            
            changes.append((original_value, new_value))
    
    return changes

def apply_adcc_special_replacements(text: str, changes: List[Tuple[str, str]]) -> str:
    """Apply ADCC special pattern replacements"""
    modified_text = text
    
    for old_value, new_value in changes:
        if old_value in modified_text:
            modified_text = modified_text.replace(old_value, new_value)
    
    return modified_text

def replace_placeholders(template: str) -> str:
    """Replace placeholders like {num}, {code}, {digit} with random values"""
    result = template
    for placeholder, func in PLACEHOLDER_FUNCTIONS.items():
        result = result.replace(placeholder, func())
    return result

# Placeholder replacement functions
def get_random_num():
    return str(random.randint(1000, 9999))

def get_random_digit():
    return str(random.randint(1, 9))

def get_random_code():
    return random.choice(["NP", "YMT", "MK", "TM", "HH", "C"])

PLACEHOLDER_FUNCTIONS = {
    '{num}': get_random_num,
    '{digit}': get_random_digit,
    '{code}': get_random_code,
}

# Helper functions for bank mapping system only
def find_bank_root(bank_variant):
    """Find the root bank for any variant"""
    if not bank_variant:
        return None
    
    bank_lower = str(bank_variant).lower()
    return BANK_VARIANT_TO_ROOT.get(bank_lower)

def get_random_bank_root(exclude_root=None):
    """Get a random bank root, optionally excluding one"""
    available_roots = list(BANK_ROOT_TO_FULL_NAME.keys())
    if exclude_root and exclude_root in available_roots:
        available_roots.remove(exclude_root)
    
    if available_roots:
        return random.choice(available_roots)
    return None

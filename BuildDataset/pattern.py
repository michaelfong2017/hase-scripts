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
    # Numeric formats with different separators
    (r'\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b', '%Y-%m-%d'),  # YYYY-MM-DD or YYYY/MM/DD
    (r'\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b', '%m-%d-%Y'),  # MM-DD-YYYY or MM/DD/YYYY
    (r'\b(\d{1,2})/(\d{1,2})/(\d{4})\b', '%m/%d/%Y'),  # MM/DD/YYYY
    
    # English month names (abbreviated, case insensitive)
    (r'\b(\d{1,2})\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{4})\b', '%d %b %Y'),  # 8 Jan 2024
    (r'\b(\d{1,2})\s*(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s*(\d{4})\b', '%d %b %Y'),  # 8 JAN 2024
    
    # English month names (full, case insensitive)
    (r'\b(\d{1,2})\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{4})\b', '%d %B %Y'),  # 8 January 2024
    (r'\b(\d{1,2})\s*(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{4})\b', '%d %B %Y'),  # 8 january 2024
    
    # Chinese date format
    (r'\b(\d{1,2})月(\d{1,2})日\b', '%m月%d日'),  # 8月7日
    
    # Other common variations with hyphens and slashes
    (r'\b(\d{1,2})-(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-?(\d{2,4})\b', '%d-%b-%Y'),  # 8-Jan-24 or 8-Jan-2024
    (r'\b(\d{1,2})/(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)/?(\d{2,4})\b', '%d/%b/%Y'),  # 8/Jan/24 or 8/Jan/2024
    
    # Additional common formats
    (r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{1,2}),?\s*(\d{4})\b', '%b %d %Y'),  # Jan 8, 2024 or Jan 8 2024
    (r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{1,2}),?\s*(\d{4})\b', '%B %d %Y'),  # January 8, 2024
    
    # ISO format variations
    (r'\b(\d{4})\.(\d{1,2})\.(\d{1,2})\b', '%Y.%m.%d'),  # YYYY.MM.DD
    (r'\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b', '%d.%m.%Y'),  # DD.MM.YYYY
]

# Enhanced name validation pattern to handle more cases
NAME_VALIDATION_PATTERN = r'^[A-Za-z0-9\s,\.&\-\']+$'

# Add these regex patterns to pattern.py
NAME_NORMALIZATION_PATTERNS = [
    # Remove titles and prefixes (case insensitive, flexible spacing)
    (r'\b(MR\.?|MRS\.?|MS\.?|MISS|DR\.?|PROF\.?)\s+', ''),
    
    # Remove suffixes like "AND OTHERS" (case insensitive)
    (r'\s+(AND\s+OTHERS?|& OTHERS?|ET AL\.?).*$', ''),
    
    # Normalize multiple spaces to single space
    (r'\s+', ' '),
    
    # Remove commas and spaces around them
    (r'\s*,\s*', ' '),
    
    # Handle concatenated names - split likely concatenated given names
    # This pattern looks for surname followed by concatenated names (6+ chars, no spaces)
    (r'^([A-Z]+)\s+([A-Z]{6,})$', r'\1 \2_SPLIT'),
]

# Common name splitting patterns for concatenated names
NAME_SPLIT_PATTERNS = [
    # Split at consonant-vowel boundaries for likely name breaks
    (r'([A-Z][AEIOU]*[BCDFGHJKLMNPQRSTVWXYZ])([A-Z][AEIOU])', r'\1 \2'),
    
    # Split common Chinese name patterns
    (r'(TAI)(MAN|MING|WAI|KEUNG)', r'\1 \2'),
    (r'(SIU)(MING|MAN|WAI|KEUNG)', r'\1 \2'),
    (r'(KA)(WAI|MAN|MING)', r'\1 \2'),
    (r'(HOI)(SHAN|MAN)', r'\1 \2'),
    (r'(WEI)(HONG|MING)', r'\1 \2'),
    (r'(MING)(FUNG)', r'\1 \2'),
    (r'(HOK)(YIN)', r'\1 \2'),
    (r'(KAI)(CHUNG)', r'\1 \2'),
    (r'(WING)(KEI)', r'\1 \2'),
    (r'(CHI)(KEUNG)', r'\1 \2'),
    (r'(MEI)(LIN)', r'\1 \2'),
]

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
    
    'names': [
        "CHAN TAI MAN", "WONG SIU MING", "LEE KA WAI", "LAM HOI SHAN",
        "CHEN WEI HONG", "LIU MING FUNG", "NG HOK YIN", "TANG SIU KWAN",
        "YEUNG KAI CHUNG", "HO WING KEI", "MA CHI KEUNG", "TSANG MEI LIN",
    ]
}

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

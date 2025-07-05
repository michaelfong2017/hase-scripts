import pandas as pd
import json
from collections import defaultdict
import re
import random
import string
from io import StringIO
from datetime import datetime, timedelta

# Enhanced sample data from the JSON
SAMPLE_DATES = [
    "2024-01-03", "2024-05-22", "2024-06-29", "2024-07-10", "2024-07-15",
    "2024-07-16", "2024-07-17", "2024-07-24", "2024-07-25", "2024-07-26",
    "2024-07-27", "2024-07-28", "2024-08-06", "2024-08-07", "2024-08-10",
    "2024-08-11", "2024-08-15", "2024-08-21", "2024-08-24", "2024-08-25",
    "2024-08-28", "2024-08-29", "2024-08-30", "2024-09-30", "2024-10-06",
    "2024-10-07", "2024-11-08", "2024-11-11", "2024-11-12", "2024-11-24",
    "2024-11-29", "2024-12-01", "2024-12-03", "2024-12-08", "2024-12-09",
    "2024-12-10", "2024-12-11", "2024-12-23", "2024-12-25", "2024-12-27",
    "2024-12-29", "2024-12-30", "2024-12-31", "2025-01-01", "2025-01-02",
    "2025-01-03", "2025-01-04", "2025-01-05", "2025-01-06", "2025-01-16",
    "2025-01-17", "2025-01-18", "2025-01-19", "2025-01-20", "2025-01-24",
    "2025-02-04", "2025-02-05", "2025-02-24",
    # Additional date formats from JSON
    "07 Aug 2024", "11 Aug 2024", "24 Aug 2024", "02 Jan 2025", "05 Jan 2025",
    "07AUG24", "10DEC", "11NOV24", "12NOV24", "29NOV24", "03DEC24", "05FEB2025",
    "20240710", "20240807", "20241227", "20250103", "20250204",
    "8月7日", "8月11日", "8月29日", "8月30日", "11月29日"
]

SAMPLE_AMOUNTS = [
    "1", "200", "300", "500", "1244", "1248", "1500", "1612", "2000", "2010", 
    "2200", "2320", "2430", "2460", "2600", "2997", "3000", "3060", "3258",
    "4000", "5000", "5001", "6100", "6180", "6225", "7001", "7999", "8000",
    "9000", "10000", "10001", "10003", "10169", "10575", "10900", "12200",
    "12300", "12778", "16500", "17000", "18000", "19990", "20000", "22000",
    "24150", "25381", "25500", "25900", "29998", "29999", "30000", "31000",
    "32300", "35000", "39000", "40000", "40012", "40200", "40500", "42000",
    "44855", "45500", "46000", "49553", "49833", "49986", "50000", "50001",
    "52460", "55100", "56000", "60000", "64348", "66120", "70000", "77000",
    "78123", "80000", "89967", "90000", "93000", "98001", "100000", "110555",
    "113504", "116523", "129890", "130000", "135524", "144123", "145886",
    "147585", "150000", "150600", "158890", "164024", "192500", "198500",
    "200000", "336000",
    # Additional amounts with decimals
    "116523.87", "147585.59", "10575.19"
]

NORMALIZED_NAMES = [
    "CHAN TAI MAN", "YEUNG KAI", "CHEUNG TAK SHING", "CHIU YAN", "CHONG MAN",
    "CHUNG SIU", "TSANG SIU MING", "XIE PANGAN", "YAN MEI MEI", "PANG YA SHI",
    "TAN FUNG", "ABC1 Limited",
    # Additional names from JSON
    "DING SUISUI", "FU SIUSAN", "LUI SAN SAN", "LIAO BOBO", "YAN XINXIN", 
    "ZHAO SUIMEN", "FONG LAI", "TANG WING"
    # Removed "CASH CASH" from normalized names
]

SAMPLE_ACCOUNT_NUMBERS = [
    "111-111111-101", "111-111111-102", "111-111111-103", "111-111111-104",
    "222-222222-101", "222-222222-102", "222-222222-103", "333-333333-101",
    "333-333333-102", "444-4444444-101", "444-4444444-102", "444-4444444-103",
    "444-4444444-104", "555-555555-101", "666-66666-601", "666-66666-602",
    "666-66666-603", "666-666666-101", "66666666601", "66666666602", "122222221",
    # Additional account patterns from JSON
    "000402■■■■■■■", "01211■■■■■■■", "024N2501■■■■■■■■■■■", "113■■■■■■■",
    "FPS:122222221", "FPS 122222221", "FPS: 122222221", "NIL", "Nil"
    # Removed all Cash-related patterns from account numbers
]

BANK_MAPPING = {
    "HSBC": ["HSBC", "004", "HSBC HK", "HSBC Hong Kong", 
             "The Hongkong and Shanghai Banking Corporation Limited",
             "THE HONGKONG AND SHANGHAI BANKING CORPORATION LIMITED (HSBC)", 
             "滙豐", "BBAN 4", "004 BBAN", "HSBCHKHH", "HSBCHKHHXXXX"],
    "HASE": ["HASE", "024", "024 BBAN", "HSB", "Hang Seng Bank", "Hang Seng Bank Ltd.", 
             "HANG SENG BANK LTD.", "HASEHKHH", "HASEHK■■■■■", "HASEH■■■■■■",
             "恆生銀行", "恆生"],
    "BOC": ["BOC", "Bank of China (Hong Kong) Limited", "中國建設銀行貴陽河濱支行"],
    "STANDARD CHARTERED": ["SCB", "STANDARD CHARTERED BANK (HONG KONG) LIMITED",
                          "STANDARD CHARTERED BANK HK LTD", "渣打银行", "003", "003 BBAN"],
    "CCB": ["CCB", "CCBA", "CHINA CONSTRUCTION BANK", 
            "China Construction Bank (Asia) Corporation Limited", "009", "009 BBAN",
            "PCBCCN■■■■", "PCBCC■■■■■■", "PCBCH■■■"],
    "ICBC": ["INDUSTRIAL AND COMMERCIAL BANK OF CHINA",
             "INDUSTRIAL AND COMMERCIAL BANK OF CHINA (ASIA) LIMITED",
             "ICBKCNB■■■■", "ICBKC■■■■■", "UBHK■■■■", "中国工商银行"],
    "DBS": ["DBS", "DBS BANK", "DBS Bank (Hong Kong) Ltd.", "016", "016 BBAN"],
    "ZA BANK": ["ZA Bank", "ZA Bank Limited", "387", "387 BBAN"],
    "BOCOM": ["Bank of Com", "Bank of Communications (Hong Kong) Ltd."]
    # Removed CASH mapping completely
}

# Enhanced pattern definitions
POLICE_REFERENCE_PATTERNS = [
    "TYRN240{digits}", "KCRN240{digits}", "KTRN230{digits}", "TMRN240{digits}",
    "TSWRN240{digits}", "STRN240{digits}", "SSRN250{digits}", "YLRN 250{digits}",
    "C RN 250{digits}", "HH RN 250{digits}", "MK RN 2500{digits}", "NTK RN 2500{digits}",
    "WCH RN 2500{digits}", "YMT RN 2500{digits}", "TM RN 240{digits}", "TST RN 240{digits}",
    "TSW RN 240{digits}", "TY RN 240{digits}", "W RN 240{digits}",
    "ESPS {digits}/2024 and {location} {digits}", "ESPS {digits}/2025 and {location} {digits}",
    "POLICEREF{digit}", "Policeref{digit}", "MOSRN{digits}", "TSRN{digits}",
    "LTN RN {digits}", "NP RN {digits}"
]

WRIT_NO_PATTERNS = [
    "01{digits}", "00{digits}", "1{digits}", "3{digits}", "5{digits}", "6{digits}",
    "8{digits}", "12{digits}", "17{digits}", "67{digits}", "TM{digits}",
    "TM12{digits}/2024", "TM19{digits}/2025", "TM86{digits}/2024", "{digits}/{year}",
    "TM ■■■■", "000■■■", "001■■■"
]

CONTACT_PERSON_PATTERNS = [
    "PC {digits}", "SGT {digits}", "PC{digits}", "SGT A{digits}", "WPC {digits}",
    "WSGT {digits}", "SPC {digits}", "ASGT {digits}", "DPC{digits}"
]

# Utility functions
def save_json_utf8(data, filename):
    """Save JSON data with proper UTF-8 encoding"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json_utf8(filename):
    """Load JSON data with proper UTF-8 encoding"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def randomize_masked_value(value):
    """Replace ■ characters with random digits/letters during randomization"""
    if not value or '■' not in str(value):
        return value
    
    result = str(value)
    while '■' in result:
        if any(char.isdigit() for char in result):
            result = result.replace('■', str(random.randint(0, 9)), 1)
        else:
            result = result.replace('■', random.choice(string.ascii_uppercase), 1)
    return result

def clean_html_artifacts(text):
    """Remove HTML artifacts from extracted text"""
    if not text:
        return text
    
    # Remove HTML tags and entities
    text = re.sub(r'<[^>]+>', '', str(text))
    text = re.sub(r'&[a-zA-Z]+;', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# Enhanced extraction function
def extract_unique_values(csv_file_path):
    """Extract all unique values from target fields with enhanced patterns"""
    df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
    unique_values = defaultdict(set)
    
    # Enhanced pattern definitions for extraction
    patterns = {
        'date': [
            r'\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?',  # 2024-08-24, 2024-08-24 00:00:00
            r'\d{1,2}\s+\w{3}\s+\d{4}',  # 24 Aug 2024, 11 Aug 2024
            r'\d{1,2}/\d{1,2}/\d{4}',  # 24/08/2024
            r'\d{4}/\d{1,2}/\d{1,2}',  # 2024/12/27
            r'\d{1,2}\w{3}\d{2,4}',  # 24AUG2024, 07AUG24
            r'\d{1,2}\w{3}',  # 07AUG, 10DEC
            r'\d{1,2}月\d{1,2}日',  # 8月7日 (Chinese format)
            r'\d{6,8}',  # 241210, 20240824
            r'\d{1,2}/\d{1,2}',  # 12/27
            r'00 VAL \d{4}'  # 00 VAL 2024
        ],
        'name': [
            r'(?:MR\.?\s*|MISS\s+|MS\.?\s*|DR\.?\s*|PROF\.?\s*|SIR\s*|MADAM\s*)?[A-Z][A-Z\s,■]+(?:\s+AND\s+OTHERS)?',
            r'"[A-Z\s,]+"',  # "CHAN, TAI MAN"
            r'\d+/[A-Z\s]+',  # 1/CHAN TAI MAN
            r'[A-Z]+\d*\s+Limited',  # ABC1 Limited
            r'NIL?',
            r'[A-Z]+\s+[A-Z]+(?:\s+[A-Z]+)*'  # General name pattern
            # Removed "CASH\s*CASH" and standalone "Cash" patterns from name patterns
        ],
        'account_number': [
            r'\d{3}-\d{6,7}-\d{3}',  # 111-111111-101
            r'\d{8,11}',  # 66666666601
            r'FPS:?\s*\d+',  # FPS:122222221
            r'\d+■+',  # 000402■■■■■■■
            r'024N\d*■*',  # 024N2501■■■■■■■■■■■
            r'0\d+■+',  # 01211■■■■■■■
            r'NIL',
            r'\d{4,12}'  # General numeric account
            # Removed all Cash-related patterns from account patterns
        ],
        'bank': [
            r'The Hongkong and Shanghai Banking Corporation Limited\s*',
            r'THE HONGKONG AND SHANGHAI BANKING CORPORATION LIMITED.*',
            r'STANDARD CHARTERED BANK.*',
            r'Bank of China.*',
            r'Hang Seng Bank.*',
            r'HANG SENG BANK.*',
            r'CHINA CONSTRUCTION BANK.*',
            r'China Construction Bank.*',
            r'INDUSTRIAL AND COMMERCIAL BANK OF CHINA.*',
            r'DBS.*',
            r'The Bank of East Asia.*',
            r'Bank of Communications.*',
            r'ZA Bank.*',
            r'HSBC|HASE|HSB|BOC|CCB|CCBA|DBS|SCB',
            r'\d{3}\s+BBAN',  # 004 BBAN
            r'BBAN\s+\d+',  # BBAN 4
            r'[A-Z]{3,8}■+',  # ICBKCNB■■■■
            r'滙豐|渣打银行|恆生銀行|恆生|中國建設銀行.*'  # Chinese bank names
            # Removed all CASH patterns
        ],
            'police_reference': [
                r'[A-Z]+RN\d*■*',  # TYRN240■■■■
                r'[A-Z]+\s+RN\s+\d*■*',  # C RN 250■■■■
                r'ESPS\s+■*\d*/\d{4}\s+and\s+\w+\s+■*\d*',  # ESPS patterns
                r'POLICEREF\d+',
                r'Policeref\d+',
                r'TM\s+\d+',
                r'TM\s+RN\s+\d+',
                r'MOSRN\d+',
                r'TSRN\d+'
            ],
            'writ_no': [
                r'\d+■*',  # 01■■■
                r'TM\d*■*',  # TM■■■
                r'TM\d*■*/\d{4}',  # TM86■■/2024
                r'\d+■*/\d{4}',  # 3■■■/2025
                r'TM\s+■*\d*'  # TM ■■■■
            ],
            'contact_person': [
                r'PC\s+\d*■*',  # PC 2■■■■
                r'PC\d*■*',  # PC■■■■■
                r'SGT\s+[A-Z]?\d*■*',  # SGT A■■■
                r'WPC\s+\d*■*',  # WPC patterns
                r'SPC\s+\d*■*',  # SPC patterns
                r'ASGT\s+\d*■*'  # ASGT patterns
            ]
        }
    
    def extract_patterns(text, field_patterns):
        matches = []
        if text and pd.notna(text):
            # Clean HTML artifacts first
            clean_text = clean_html_artifacts(str(text))
            for pattern in field_patterns:
                matches.extend(re.findall(pattern, clean_text, re.IGNORECASE))
        return matches
    
    for idx, row in df.iterrows():
        # Extract from Input and Transactions columns
        for col in ['Input', 'Transactions']:
            if pd.notna(row.get(col)):
                text = str(row[col])
                for field, field_patterns in patterns.items():
                    unique_values[field].update(extract_patterns(text, field_patterns))
        
        # Extract from Ground Truth JSON
        try:
            ground_truth = json.loads(row.get('Ground Truth', '{}')) if pd.notna(row.get('Ground Truth')) else {}
            
            for transaction in ground_truth.get('alerted_transactions', []):
                for field in ['date', 'amount']:
                    if field in transaction and transaction[field]:
                        unique_values[field].add(str(transaction[field]))
                
                for side in ['from', 'to']:
                    if side in transaction:
                        for field in ['name', 'account_number', 'bank']:
                            if field in transaction[side] and transaction[side][field]:
                                unique_values[field].add(str(transaction[side][field]))
                
                if 'cancel_amount_requested' in transaction and transaction['cancel_amount_requested']:
                    unique_values['cancel_amount_requested'].add(str(transaction['cancel_amount_requested']))
            
            for field in ['police_reference', 'writ_no', 'contact_person']:
                if field in ground_truth and ground_truth[field]:
                    unique_values[field].add(str(ground_truth[field]))
                    
        except (json.JSONDecodeError, TypeError):
            continue
    
    return {key: sorted(list(values)) for key, values in unique_values.items()}

# Random generation functions (keep existing ones and add enhanced versions)
def generate_random_date():
    """Generate random date from sample dates, avoiding ambiguous formats"""
    # Use the actual dates from your sample data
    valid_dates = [
        "2024-01-03", "2024-05-22", "2024-06-29", "2024-07-10", "2024-07-15",
        "2024-07-16", "2024-07-17", "2024-07-24", "2024-07-25", "2024-07-26",
        "2024-07-27", "2024-07-28", "2024-08-06", "2024-08-07", "2024-08-10",
        "2024-08-11", "2024-08-15", "2024-08-21", "2024-08-24", "2024-08-25",
        "2024-08-28", "2024-08-29", "2024-08-30", "2024-09-30", "2024-10-06",
        "2024-10-07", "2024-11-08", "2024-11-11", "2024-11-12", "2024-11-24",
        "2024-11-29", "2024-12-01", "2024-12-03", "2024-12-08", "2024-12-09",
        "2024-12-10", "2024-12-11", "2024-12-23", "2024-12-25", "2024-12-27",
        "2024-12-29", "2024-12-30", "2024-12-31", "2025-01-01", "2025-01-02",
        "2025-01-03", "2025-01-04", "2025-01-05", "2025-01-06", "2025-01-16",
        "2025-01-17", "2025-01-18", "2025-01-19", "2025-01-20", "2025-01-24",
        "2025-02-04", "2025-02-05", "2025-02-24"
    ]
    
    # Pick a random valid date
    base_date = random.choice(valid_dates)
    
    # Convert to different formats but avoid ambiguous day/month formats
    try:
        dt = datetime.strptime(base_date, '%Y-%m-%d')
        
        formats = [
            dt.strftime('%Y-%m-%d'),           # 2024-08-24
            dt.strftime('%Y-%m-%d %H:%M:%S'),  # 2024-08-24 00:00:00
            dt.strftime('%d %b %Y'),           # 24 Aug 2024
            dt.strftime('%Y%m%d'),             # 20240824
            dt.strftime('%d%b%Y').upper(),     # 24AUG2024
            dt.strftime('%d-%m-%Y'),           # 24-08-2024
            dt.strftime('%Y/%m/%d'),           # 2024/08/24 (year first, unambiguous)
        ]
        
        return random.choice(formats)
    except:
        # Fallback to original date if parsing fails
        return base_date

def generate_random_amount():
    """Generate random amount with decimal variations"""
    amount = random.choice(SAMPLE_AMOUNTS)
    
    # Sometimes add .0 or other decimal variations
    variations = [
        lambda a: a,  # 50000
        lambda a: a + ".0",  # 50000.0
        lambda a: a + "." + str(random.randint(10, 99)),  # 50000.87
    ]
    
    return random.choice(variations)(amount)

def generate_random_account_number():
    """Generate random account number"""
    patterns = [
        lambda: f"{random.randint(111, 999)}-{random.randint(111111, 999999)}-{random.randint(101, 999)}",
        lambda: f"{random.randint(111, 999)}-{random.randint(1111111, 9999999)}-{random.randint(101, 999)}",
        lambda: ''.join([str(random.randint(0, 9)) for _ in range(11)]),
        lambda: str(random.randint(100000000, 999999999))
    ]
    return random.choice(patterns)()

def generate_pattern_value(patterns, replacements):
    """Generate value from pattern with replacements"""
    pattern = random.choice(patterns)
    result = pattern
    for placeholder, generator in replacements.items():
        result = result.replace(placeholder, generator())
    return result

def generate_random_police_reference():
    """Generate random police reference"""
    replacements = {
        '{digits}': lambda: ''.join([str(random.randint(0, 9)) for _ in range(4)]),
        '{digit}': lambda: str(random.randint(1, 9)),
        '{location}': lambda: random.choice(['WTSDIST', 'TMDIV', 'NTKDIV', 'WCHDIV', 'SSDIV', 'MKDIST', 'TSTDIV', 'TYDIV']),
        '{year}': lambda: str(random.choice([2024, 2025]))
    }
    return generate_pattern_value(POLICE_REFERENCE_PATTERNS, replacements)

def generate_random_writ_no():
    """Generate random writ number"""
    replacements = {
        '{digits}': lambda: ''.join([str(random.randint(0, 9)) for _ in range(random.randint(2, 4))]),
        '{year}': lambda: str(random.choice([2024, 2025]))
    }
    return generate_pattern_value(WRIT_NO_PATTERNS, replacements)

def generate_random_contact_person():
    """Generate random contact person"""
    replacements = {
        '{digits}': lambda: ''.join([str(random.randint(0, 9)) for _ in range(4)])
    }
    return generate_pattern_value(CONTACT_PERSON_PATTERNS, replacements)

# Normalization functions
def normalize_name_strict(value):
    """Normalize name - KEEP ■ AS-IS"""
    if not value:
        return value
    
    value = str(value).strip().upper()
    if value in ['NIL', 'Nil']:
        return 'NIL'
    
    value = re.sub(r'[^\w\s,■]', ' ', value)
    value = re.sub(r'\s+', ' ', value)
    
    prefixes = ['MR', 'MRS', 'MS', 'DR', 'PROF', 'SIR', 'MADAM', 'MISS']
    suffixes = ['JR', 'SR', 'III', 'IV', 'AND', 'OTHERS', 'LIMITED']
    
    words = [word.replace(',', '').strip() for word in value.split() 
             if word.replace(',', '').strip() not in prefixes + suffixes]
    
    return ' '.join(words)

def normalize_amount_strict(value):
    """Normalize amount - KEEP ■ AS-IS"""
    if not value or '■' in str(value):
        return value
    
    value = re.sub(r'[^\d.]', '', str(value).strip())
    try:
        return str(int(float(value)))
    except ValueError:
        return value

def normalize_account_number_strict(value):
    """Normalize account number - preserve FPS info and ■"""
    if not value or '■' in str(value):
        return value
    
    value = str(value).strip()
    if value.upper().startswith('FPS'):
        return value if ':' in value else f"FPS:{value.split()[1]}" if ' ' in value else value
    
    return re.sub(r'[^0-9\-]', '', value)

def normalize_bank(value):
    """Normalize bank names using trusted mapping"""
    if not value or '■' in str(value):
        return value
    
    value = str(value).strip()
    
    # Direct mapping lookup
    bank_mapping = {
        "BOC": "BOC", "Bank of China (Hong Kong) Limited": "BOC",
        "024": "HASE", "HANG SENG BANK": "HASE", "HANG SENG BANK LTD": "HASE",
        "HANG SENG BANK LTD.": "HASE", "HASE": "HASE", "HASEHK": "HASE", "HSB": "HASE",
        "Hang Seng Bank": "HASE", "Hang Seng Bank Ltd": "HASE", "Hang Seng Bank Ltd.": "HASE",
        "004": "HSBC", "HSBC": "HSBC", "HSBC HK": "HSBC", "HSBC Hong Kong": "HSBC",
        "THE HONGKONG AND SHANGHAI BANKING CORPORATION LIMITED": "HSBC",
        "The Hongkong and Shanghai Banking Corporation Limited": "HSBC",
        "SCB": "STANDARD CHARTERED BANK (HONG KONG) LIMITED",
        "STANDARD CHARTERED BANK (HONG KONG) LIMITED": "STANDARD CHARTERED BANK (HONG KONG) LIMITED"
    }
    
    # Try exact match first
    if value in bank_mapping:
        return bank_mapping[value]
    
    # Try case-insensitive match
    for key, mapped_value in bank_mapping.items():
        if key.upper() == value.upper():
            return mapped_value
    
    return value

def normalize_field_with_mask(value):
    """Normalize police/writ/contact fields - KEEP ■ AS-IS"""
    if not value:
        return value
    return re.sub(r'\s+', ' ', str(value).strip().upper())

# Pattern matching and replacement functions
def generate_name_variation_pattern(normalized_name):
    """Generate enhanced regex pattern for name variations including multiple spaces"""
    words = normalized_name.split()
    word_patterns = [re.escape(word) + r'[,]?\s*' for word in words]
    core_pattern = r'\s*'.join(word_patterns)
    
    prefix_pattern = r'(?:MR\.?\s+|MRS\.?\s+|MS\.?\s+|MISS\s+|DR\.?\s+|PROF\.?\s+|SIR\s+|MADAM\s+)?'
    suffix_pattern = r'(?:\s*JR\.?|\s*SR\.?|\s*III|\s*IV|\s*AND\s+OTHERS)?'
    quote_pattern = r'["\']?'
    slash_pattern = r'(?:\d+/)?'
    
    full_pattern = f'{quote_pattern}{slash_pattern}{prefix_pattern}{core_pattern}{suffix_pattern}{quote_pattern}'
    return re.compile(full_pattern, re.IGNORECASE)

def find_variations(text, normalized_value):
    """Find all variations of a normalized value in text"""
    if not text or not normalized_value:
        return []
    
    pattern = generate_name_variation_pattern(normalized_value)
    matches = pattern.findall(text)
    return list(set([re.sub(r'\s+', ' ', match.strip()) for match in matches]))

def replace_variations(text, normalized_value):
    """Replace all variations with normalized value"""
    if not text or not normalized_value:
        return text
    
    pattern = generate_name_variation_pattern(normalized_value)
    return pattern.sub(normalized_value, text)

def replace_in_dataframe(df, normalized_value, target_field='name'):
    """Apply replacement across all three columns"""
    df = df.copy()
    
    # Replace in Input column
    df['Input'] = df['Input'].apply(lambda x: replace_variations(x, normalized_value) if pd.notna(x) else x)
    
    # Replace in Transactions column
    def replace_in_transactions(transactions_csv):
        if not transactions_csv or pd.isna(transactions_csv):
            return transactions_csv
        try:
            trans_df = pd.read_csv(StringIO(transactions_csv))
            for col in ['from.name', 'to.name']:
                if col in trans_df.columns:
                    trans_df[col] = trans_df[col].apply(
                        lambda x: replace_variations(str(x), normalized_value) if pd.notna(x) else x
                    )
            return trans_df.to_csv(index=False)
        except Exception:
            return transactions_csv
    
    df['Transactions'] = df['Transactions'].apply(replace_in_transactions)
    
    # Replace in Ground Truth column
    def replace_in_ground_truth(json_str):
        if not json_str or pd.isna(json_str):
            return json_str
        try:
            ground_truth = json.loads(json_str)
            for transaction in ground_truth.get('alerted_transactions', []):
                for side in ['from', 'to']:
                    if side in transaction and 'name' in transaction[side] and transaction[side]['name']:
                        transaction[side]['name'] = replace_variations(transaction[side]['name'], normalized_value)
            return json.dumps(ground_truth, ensure_ascii=False)
        except Exception:
            return json_str
    
    df['Ground Truth'] = df['Ground Truth'].apply(replace_in_ground_truth)
    return df

# Function dictionaries
strict_normalization_functions = {
    'date': lambda x: x,
    'amount': normalize_amount_strict,
    'name': normalize_name_strict,
    'account_number': normalize_account_number_strict,
    'bank': normalize_bank,
    'cancel_amount_requested': normalize_amount_strict,
    'police_reference': normalize_field_with_mask,
    'writ_no': normalize_field_with_mask,
    'contact_person': normalize_field_with_mask
}

random_generation_functions = {
    'date': generate_random_date,
    'name': lambda: random.choice(NORMALIZED_NAMES),
    'amount': generate_random_amount,
    'account_number': generate_random_account_number,
    'bank': lambda: random.choice(list(BANK_MAPPING.keys())),
    'cancel_amount_requested': generate_random_amount,
    'police_reference': generate_random_police_reference,
    'writ_no': generate_random_writ_no,
    'contact_person': generate_random_contact_person
}
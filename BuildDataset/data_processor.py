import pandas as pd
import json
from collections import defaultdict
import re
import random
import string
from io import StringIO
from datetime import datetime, timedelta

# Updated with your actual sample data
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
    "2025-02-04", "2025-02-05", "2025-02-24"
]

SAMPLE_AMOUNTS = [
    "1", "10000", "100000", "10001", "10003", "10169", "10575", "10900",
    "110555", "113504", "116523", "12200", "12300", "1244", "1248", "12778",
    "129890", "130000", "135524", "144123", "145886", "147585", "1500",
    "150000", "150600", "158890", "1612", "164024", "16500", "17000",
    "18000", "192500", "198500", "19990", "200", "2000", "20000", "200000",
    "2010", "2200", "22000", "2320", "24150", "2430", "2460", "25500",
    "25900", "2600", "2997", "29998", "29999", "300", "3000", "30000",
    "3060", "31000", "32300", "3258", "336000", "35000", "39000", "4000",
    "40000", "40012", "40200", "40500", "42000", "44855", "45500", "46000",
    "49553", "49833", "500", "5000", "50000", "50001", "5001", "52460",
    "55100", "56000", "60000", "6100", "6180", "6225", "64348", "66120",
    "70000", "7001", "77000", "78123", "7999", "8000", "80000", "89967",
    "9000", "90000", "93000", "98001"
]

NORMALIZED_NAMES = [
    "CHAN TAI MAN", "YEUNG KAI", "CHEUNG TAK SHING", "CHIU YAN", "CHONG MAN",
    "CHUNG SIU", "TSANG SIU MING", "XIE PANGAN", "YAN MEI MEI", "PANG YA SHI",
    "TAN FUNG"
]

SAMPLE_ACCOUNT_NUMBERS = [
    "111-111111-101", "111-111111-102", "111-111111-103", "111-111111-104",
    "222-222222-101", "222-222222-102", "222-222222-103", "333-333333-101",
    "333-333333-102", "444-4444444-101", "444-4444444-102", "444-4444444-103",
    "444-4444444-104", "555-555555-101", "666-66666-601", "666-66666-602",
    "666-66666-603", "666-666666-101", "66666666601", "66666666602", "122222221"
]

BANK_MAPPING = {
    "HSBC": ["HSBC", "HASE", "HSBC HK", "HSBC Hong Kong", 
             "The Hongkong and Shanghai Banking Corporation Limited",
             "THE HONGKONG AND SHANGHAI BANKING CORPORATION LIMITED (HSBC)", "滙豐"],
    "STANDARD CHARTERED": ["SCB", "STANDARD CHARTERED BANK (HONG KONG) LIMITED",
                          "STANDARD CHARTERED BANK HK LTD", "渣打银行"],
    "BOC": ["BOC", "Bank of China (Hong Kong) Limited"],
    "HANG SENG": ["HSB", "Hang Seng Bank", "Hang Seng Bank Ltd."],
    "CCB": ["CCB", "CCBA", "CHINA CONSTRUCTION BANK", 
            "China Construction Bank (Asia) Corporation Limited", "中國建設銀行貴陽河濱支行"],
    "ICBC": ["INDUSTRIAL AND COMMERCIAL BANK OF CHINA",
             "INDUSTRIAL AND COMMERCIAL BANK OF CHINA (ASIA) LIMITED"],
    "DBS": ["DBS", "DBS BANK", "DBS Bank (Hong Kong) Ltd."],
    "BEA": ["The Bank of East Asia, Limited"],
    "BOCOM": ["Bank of Com", "Bank of Communications (Hong Kong) Ltd."],
    "ZA BANK": ["ZA Bank", "ZA Bank Limited"]
}

POLICE_REFERENCE_PATTERNS = [
    "TYRN240{digits}",
    "KCRN240{digits}",
    "KTRN230{digits}",
    "TMRN240{digits}",
    "TSWRN240{digits}",
    "STRN240{digits}",
    "SSRN250{digits}",
    "YLRN 250{digits}",
    "C RN 250{digits}",
    "HH RN 250{digits}",
    "MK RN 2500{digits}",
    "NTK RN 2500{digits}",
    "WCH RN 2500{digits}",
    "YMT RN 2500{digits}",
    "TM RN 240{digits}",
    "TST RN 240{digits}",
    "TSW RN 240{digits}",
    "TY RN 240{digits}",
    "W RN 240{digits}",
    "ESPS {digits}/2024 and {location} {digits}",
    "ESPS {digits}/2025 and {location} {digits}",
    "POLICEREF{digit}",
    "Policeref{digit}"
]

WRIT_NO_PATTERNS = [
    "01{digits}",
    "00{digits}",
    "1{digits}",
    "3{digits}",
    "5{digits}",
    "6{digits}",
    "8{digits}",
    "12{digits}",
    "17{digits}",
    "67{digits}",
    "TM{digits}",
    "TM12{digits}/2024",
    "TM19{digits}/2025",
    "TM86{digits}/2024",
    "{digits}/{year}"
]

CONTACT_PERSON_PATTERNS = [
    "PC {digits}",
    "SGT {digits}",
    "PC{digits}"
]

def save_json_utf8(data, filename):
    """Save JSON data with proper UTF-8 encoding"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_json_utf8(filename):
    """Load JSON data with proper UTF-8 encoding"""
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_unique_values(csv_file_path):
    """Extract all unique values from target fields across the dataset."""
    df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
    unique_values = defaultdict(set)
    
    for idx, row in df.iterrows():
        ground_truth_str = row['Ground Truth']
        try:
            ground_truth = json.loads(ground_truth_str) if isinstance(ground_truth_str, str) else {}
        except (json.JSONDecodeError, TypeError):
            ground_truth = {}
        
        alerted_transactions = ground_truth.get('alerted_transactions', [])
        for transaction in alerted_transactions:
            if 'date' in transaction and transaction['date']:
                unique_values['date'].add(str(transaction['date']))
            if 'amount' in transaction and transaction['amount'] is not None:
                unique_values['amount'].add(str(transaction['amount']))
            if 'from' in transaction and 'name' in transaction['from'] and transaction['from']['name']:
                unique_values['name'].add(str(transaction['from']['name']))
            if 'to' in transaction and 'name' in transaction['to'] and transaction['to']['name']:
                unique_values['name'].add(str(transaction['to']['name']))
            if 'from' in transaction and 'account_number' in transaction['from'] and transaction['from']['account_number']:
                unique_values['account_number'].add(str(transaction['from']['account_number']))
            if 'to' in transaction and 'account_number' in transaction['to'] and transaction['to']['account_number']:
                unique_values['account_number'].add(str(transaction['to']['account_number']))
            if 'from' in transaction and 'bank' in transaction['from'] and transaction['from']['bank']:
                unique_values['bank'].add(str(transaction['from']['bank']))
            if 'to' in transaction and 'bank' in transaction['to'] and transaction['to']['bank']:
                unique_values['bank'].add(str(transaction['to']['bank']))
            if 'cancel_amount_requested' in transaction and transaction['cancel_amount_requested'] is not None:
                unique_values['cancel_amount_requested'].add(str(transaction['cancel_amount_requested']))
        
        if 'police_reference' in ground_truth and ground_truth['police_reference']:
            unique_values['police_reference'].add(str(ground_truth['police_reference']))
        if 'writ_no' in ground_truth and ground_truth['writ_no']:
            unique_values['writ_no'].add(str(ground_truth['writ_no']))
        if 'contact_person' in ground_truth and ground_truth['contact_person']:
            unique_values['contact_person'].add(str(ground_truth['contact_person']))
    
    result = {}
    for key in unique_values:
        result[key] = sorted(list(unique_values[key]))
    
    return result

def generate_random_date():
    """Generate random date from sample dates or create similar pattern"""
    if random.choice([True, False]):
        return random.choice(SAMPLE_DATES)
    else:
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2025, 12, 31)
        random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
        return random_date.strftime("%Y-%m-%d")

def generate_random_amount():
    """Generate random amount from sample amounts or create similar pattern"""
    if random.choice([True, False]):
        return random.choice(SAMPLE_AMOUNTS)
    else:
        patterns = [
            lambda: str(random.randint(1, 9) * 1000),
            lambda: str(random.randint(10, 99) * 1000),
            lambda: str(random.randint(100, 999) * 1000),
            lambda: str(random.randint(1000, 9999)),
            lambda: str(random.randint(10000, 99999)),
        ]
        return random.choice(patterns)()

def generate_random_account_number():
    """Generate random account number from sample patterns"""
    patterns = [
        lambda: f"{random.randint(111, 999)}-{random.randint(111111, 999999)}-{random.randint(101, 999)}",
        lambda: f"{random.randint(111, 999)}-{random.randint(1111111, 9999999)}-{random.randint(101, 999)}",
        lambda: f"{random.randint(111, 999)}-{random.randint(11111, 99999)}-{random.randint(601, 999)}",
        lambda: ''.join([str(random.randint(0, 9)) for _ in range(11)]),
        lambda: str(random.randint(100000000, 999999999)),
    ]
    return random.choice(patterns)()

def generate_random_police_reference():
    """Generate random police reference from actual patterns"""
    pattern = random.choice(POLICE_REFERENCE_PATTERNS)
    
    result = pattern
    result = result.replace('{digits}', ''.join([str(random.randint(0, 9)) for _ in range(4)]))
    result = result.replace('{digit}', str(random.randint(1, 9)))
    result = result.replace('{location}', random.choice(['WTSDIST', 'TMDIV', 'NTKDIV', 'WCHDIV', 'SSDIV', 'MKDIST', 'TSTDIV', 'TYDIV']))
    result = result.replace('{year}', str(random.choice([2024, 2025])))
    
    return result

def generate_random_writ_no():
    """Generate random writ number from actual patterns"""
    pattern = random.choice(WRIT_NO_PATTERNS)
    
    result = pattern
    result = result.replace('{digits}', ''.join([str(random.randint(0, 9)) for _ in range(random.randint(2, 4))]))
    result = result.replace('{year}', str(random.choice([2024, 2025])))
    
    return result

def generate_random_contact_person():
    """Generate random contact person from actual patterns"""
    pattern = random.choice(CONTACT_PERSON_PATTERNS)
    
    result = pattern
    result = result.replace('{digits}', ''.join([str(random.randint(0, 9)) for _ in range(4)]))
    
    return result

def normalize_name_strict(value):
    """Normalize name to match your actual data patterns - KEEP ■ AS-IS"""
    if not value:
        return value
    
    value = str(value).strip()
    
    if value.upper() in ['NIL', 'Nil']:
        return 'NIL'
    
    # Remove extra whitespace and punctuation except commas and ■
    value = re.sub(r'[^\w\s,■]', ' ', value)
    value = re.sub(r'\s+', ' ', value)
    value = value.upper()
    
    prefixes = ['MR', 'MRS', 'MS', 'DR', 'PROF', 'SIR', 'MADAM', 'MISS']
    suffixes = ['JR', 'SR', 'III', 'IV', 'AND', 'OTHERS', 'LIMITED']
    
    words = value.split()
    filtered_words = []
    
    for word in words:
        clean_word = word.replace(',', '').strip()
        if clean_word not in prefixes and clean_word not in suffixes:
            filtered_words.append(clean_word)
    
    return ' '.join(filtered_words)

def normalize_amount_strict(value):
    """Normalize amount to match your data (remove decimals) - KEEP ■ AS-IS"""
    if not value:
        return value
    
    value = str(value).strip()
    
    # If contains ■, keep as-is
    if '■' in value:
        return value
    
    value = re.sub(r'[^\d.]', '', value)
    
    try:
        amount_float = float(value)
        amount_int = int(amount_float)
        return str(amount_int)
    except ValueError:
        return value

def normalize_account_number_strict(value):
    """Normalize account number to match your data patterns - KEEP ■ AS-IS"""
    if not value:
        return value
    
    value = str(value).strip()
    
    # If contains ■, keep as-is
    if '■' in value:
        return value
    
    if value.upper().startswith('FPS'):
        number_part = re.sub(r'[^0-9]', '', value)
        return number_part
    
    value = re.sub(r'[^0-9\-]', '', value)
    return value

def normalize_bank(value):
    """Normalize bank names by standardizing common variations - KEEP ■ AS-IS"""
    if not value:
        return value
    
    value = str(value).strip().upper()
    
    # If contains ■, keep as-is
    if '■' in value:
        return value
    
    value = re.sub(r'\s+', ' ', value)
    
    bank_mappings = {
        r'THE HONGKONG AND SHANGHAI BANKING CORPORATION LIMITED': 'HSBC',
        r'HONGKONG AND SHANGHAI BANKING CORPORATION': 'HSBC',
        r'HSBC.*': 'HSBC',
        r'HASE': 'HSBC',
        r'滙豐': 'HSBC',
        r'STANDARD CHARTERED BANK.*': 'STANDARD CHARTERED',
        r'渣打银行': 'STANDARD CHARTERED',
        r'BANK OF CHINA.*': 'BOC',
        r'HANG SENG BANK.*': 'HANG SENG',
        r'中國建設銀行.*': 'CCB',
        r'CHINA CONSTRUCTION BANK.*': 'CCB',
    }
    
    for pattern, replacement in bank_mappings.items():
        if re.match(pattern, value):
            return replacement
    
    return value

def normalize_police_reference_strict(value):
    """Normalize police reference to match your data patterns - KEEP ■ AS-IS"""
    if not value:
        return value
    
    value = str(value).strip().upper()
    
    # Keep ■ as-is during normalization
    value = re.sub(r'\s+', ' ', value)
    
    return value

def normalize_writ_no_strict(value):
    """Normalize writ number to match your data patterns - KEEP ■ AS-IS"""
    if not value:
        return value
    
    value = str(value).strip().upper()
    
    # Keep ■ as-is during normalization
    value = re.sub(r'\s+', ' ', value)
    
    return value

def normalize_contact_person_strict(value):
    """Normalize contact person to match your data patterns - KEEP ■ AS-IS"""
    if not value:
        return value
    
    value = str(value).strip().upper()
    
    # Keep ■ as-is during normalization
    value = re.sub(r'\s+', ' ', value)
    
    return value

def randomize_masked_value(value):
    """Replace ■ characters with random digits/letters during randomization"""
    if not value or '■' not in str(value):
        return value
    
    result = str(value)
    
    # Replace ■ with random digits or letters based on context
    while '■' in result:
        # For most cases, use digits
        if any(char.isdigit() for char in result):
            result = result.replace('■', str(random.randint(0, 9)), 1)
        else:
            # For cases that might need letters
            result = result.replace('■', random.choice(string.ascii_uppercase), 1)
    
    return result

def generate_name_variation_pattern(normalized_name):
    """Generate regex pattern to find variations of a normalized name"""
    escaped_name = re.escape(normalized_name)
    words = normalized_name.split()
    pattern_words = [re.escape(word) + r'[ ,]*' for word in words]
    pattern_core = ''.join(pattern_words).rstrip('[ ,]*')
    
    prefix_pattern = r'(?:MR|MRS|MS|DR|PROF|MISS)?[ ]*'
    suffix_pattern = r'(?:JR|SR|III|IV)?'
    additional_words_pattern = r'(?:\s+AND\s+OTHERS)?'
    
    full_pattern = f'{prefix_pattern}{pattern_core}{suffix_pattern}{additional_words_pattern}'
    regex = re.compile(full_pattern, re.IGNORECASE)
    return regex

def find_variations(text, normalized_value):
    """Find all variations of a normalized value in a text"""
    if not text or not normalized_value:
        return []
    
    pattern = generate_name_variation_pattern(normalized_value)
    matches = pattern.findall(text)
    unique_matches = list(set([re.sub(r'\s+', ' ', match.strip()) for match in matches]))
    return unique_matches

def replace_variations(text, normalized_value):
    """Replace all variations of a normalized value with the normalized value in text"""
    if not text or not normalized_value:
        return text
    
    pattern = generate_name_variation_pattern(normalized_value)
    replaced_text = pattern.sub(normalized_value, text)
    return replaced_text

def replace_in_dataframe(df, normalized_value, target_field='name'):
    """Apply replacement across all three columns in the dataframe"""
    df = df.copy()
    
    df['Input'] = df['Input'].apply(lambda x: replace_variations(x, normalized_value) if pd.notna(x) else x)
    
    def replace_in_transactions(transactions_csv):
        if not transactions_csv or pd.isna(transactions_csv):
            return transactions_csv
        try:
            trans_df = pd.read_csv(StringIO(transactions_csv))
            
            if 'from.name' in trans_df.columns:
                trans_df['from.name'] = trans_df['from.name'].apply(
                    lambda x: replace_variations(str(x), normalized_value) if pd.notna(x) else x
                )
            if 'to.name' in trans_df.columns:
                trans_df['to.name'] = trans_df['to.name'].apply(
                    lambda x: replace_variations(str(x), normalized_value) if pd.notna(x) else x
                )
            
            return trans_df.to_csv(index=False)
        except Exception as e:
            print(f"Error processing transactions CSV: {e}")
            return transactions_csv
    
    df['Transactions'] = df['Transactions'].apply(replace_in_transactions)
    
    def replace_in_ground_truth(json_str):
        if not json_str or pd.isna(json_str):
            return json_str
        try:
            ground_truth = json.loads(json_str)
            alerted_transactions = ground_truth.get('alerted_transactions', [])
            for transaction in alerted_transactions:
                if 'from' in transaction and 'name' in transaction['from'] and transaction['from']['name']:
                    transaction['from']['name'] = replace_variations(transaction['from']['name'], normalized_value)
                if 'to' in transaction and 'name' in transaction['to'] and transaction['to']['name']:
                    transaction['to']['name'] = replace_variations(transaction['to']['name'], normalized_value)
            
            return json.dumps(ground_truth, ensure_ascii=False)
        except Exception as e:
            print(f"Error processing ground truth JSON: {e}")
            return json_str
    
    df['Ground Truth'] = df['Ground Truth'].apply(replace_in_ground_truth)
    
    return df

# Random generation functions dictionary
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

# Normalization functions dictionary
strict_normalization_functions = {
    'date': lambda x: x,
    'amount': normalize_amount_strict,
    'name': normalize_name_strict,
    'account_number': normalize_account_number_strict,
    'bank': normalize_bank,
    'cancel_amount_requested': normalize_amount_strict,
    'police_reference': normalize_police_reference_strict,
    'writ_no': normalize_writ_no_strict,
    'contact_person': normalize_contact_person_strict
}

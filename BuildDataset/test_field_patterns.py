import unittest
import re
from data_processor import (
    normalize_name_strict, normalize_account_number_strict,
    normalize_bank, generate_random_date, generate_random_amount,
    generate_random_account_number, generate_random_police_reference,
    generate_random_writ_no, generate_random_contact_person,
    strict_normalization_functions
)

class TestFieldPatterns(unittest.TestCase):
    
    def test_date_patterns(self):
        """Test all date format patterns from your CSV data"""
        date_samples = [
            "2024-08-24", "2024-08-24 00:00:00", "24 Aug 2024", "11 Aug 2024", 
            "24/08/2024", "24AUG2024", "07AUG24", "07AUG", "10DEC", "8月7日", 
            "241210", "20240824", "12/27", "2024/12/27", "29/11/2024",
            "03/01/2025", "1/18/2025", "05 Jan 2025", "3 Jan 2025"
        ]
        
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?',
            r'\d{1,2}\s+\w{3}\s+\d{4}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{4}/\d{1,2}/\d{1,2}',
            r'\d{1,2}\w{3}\d{2,4}',
            r'\d{1,2}\w{3}',
            r'\d{1,2}月\d{1,2}日',
            r'\d{6,8}',
            r'\d{1,2}/\d{1,2}'
        ]
        
        for sample in date_samples:
            matched = any(re.search(pat, sample, re.IGNORECASE) for pat in date_patterns)
            self.assertTrue(matched, f"Date sample '{sample}' did not match any pattern")
    
    def test_name_patterns(self):
        """Test all name format patterns from your CSV data"""
        name_samples = [
            "MR CHAN TAI MAN", "MISS YEUNG KAI", "MS. WONG SIU MING", "DR LEE KA WAI",
            "CHAN TAI MAN AND OTHERS", '"CHAN, TAI MAN"', "1/CHAN TAI MAN",
            "CHAN, TAI MAN", "CHAN TAIMAN", "MR CHAN, TAIMAN", "CHEUNG TAK SHING ",
            "MR          CHAN TAI MAN", "Mr CHAN TAI MAN AND OTHERS", "ABC1 Limited",
            "NIL", "Nil", "YAN, MEI MEI", "TAN, FUNG"
        ]
        
        name_patterns = [
            r'(?:MR\.?\s*|MISS\s+|MS\.?\s*|DR\.?\s*)?[A-Z][A-Z\s,■]+(?:\s+AND\s+OTHERS)?',
            r'"[A-Z\s,]+"',
            r'\d+/[A-Z\s]+',
            r'[A-Z]+\d*\s+Limited',
            r'CASH\s*CASH',
            r'NIL?'
        ]
        
        for sample in name_samples:
            matched = any(re.search(pat, sample.upper(), re.IGNORECASE) for pat in name_patterns)
            self.assertTrue(matched, f"Name sample '{sample}' did not match any pattern")
    
    def test_account_number_patterns(self):
        """Test all account number patterns from your CSV data"""
        account_samples = [
            "111-111111-101", "444-4444444-101", "666-6666-601", "666-66666-601", "666-666666-101",
            "66666666601", "122222221", "FPS:122222221", "FPS 122222221", "FPS: 122222221",
            "000402■■■■■■■", "024N2501■■■■■■■■■■■", "01211■■■■■■■", "037■■■■■■■■■■■■",
            "113■■■■■■■", "024N240■■■■■■■■■■■■", "NIL"
            # Removed "Cash", "Cash Deposit", "CASH" from account number tests
        ]
        
        account_patterns = [
            r'\d{3}-\d{5,7}-\d{3}',
            r'\d{8,11}',
            r'FPS:?\s*\d+',
            r'\d+■+',
            r'024N\d*■*',
            r'0\d+■+',
            r'Cash(?:\s+Deposit)?',
            r'CASH',
            r'NIL'
        ]
        
        for sample in account_samples:
            matched = any(re.search(pat, sample, re.IGNORECASE) for pat in account_patterns)
            self.assertTrue(matched, f"Account sample '{sample}' did not match any pattern")
    
    def test_bank_patterns(self):
        """Test all bank patterns from your CSV data"""
        bank_samples = [
            "The Hongkong and Shanghai Banking Corporation Limited",
            "THE HONGKONG AND SHANGHAI BANKING CORPORATION LIMITED (HSBC)",
            "STANDARD CHARTERED BANK (HONG KONG) LIMITED",
            "STANDARD CHARTERED BANK HK LTD", "Bank of China (Hong Kong) Limited",
            "Hang Seng Bank Ltd.", "HANG SENG BANK LTD.", "CHINA CONSTRUCTION BANK",
            "China Construction Bank (Asia) Corporation Limited",
            "INDUSTRIAL AND COMMERCIAL BANK OF CHINA (ASIA) LIMITED",
            "DBS Bank (Hong Kong) Ltd.", "The Bank of East Asia, Limited",
            "Bank of Communications (Hong Kong) Ltd.", "ZA Bank Limited",
            "HSBC", "HASE", "HSB", "BOC", "CCB", "CCBA", "DBS", "SCB",
            "004 BBAN", "024 BBAN", "BBAN 4", "009 BBAN", "016 BBAN", "387 BBAN",
            "ICBKCNB■■■■", "ICBKC■■■■■", "PCBCCN■■■■", "HASEHK■■■■■",
            "滙豐", "渣打银行", "恆生銀行", "恆生", "中國建設銀行貴陽河濱支行"
        ]
        
        bank_patterns = [
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
            r'\d{3}\s+BBAN',
            r'BBAN\s+\d+',
            r'[A-Z]{3,8}■+',
            r'滙豐|渣打银行|恆生銀行|恆生|中國建設銀行.*'
        ]
        
        for sample in bank_samples:
            matched = any(re.search(pat, sample, re.IGNORECASE) for pat in bank_patterns)
            self.assertTrue(matched, f"Bank sample '{sample}' did not match any pattern")
    
    def test_amount_patterns(self):
        """Test amount normalization patterns"""
        amount_samples = [
            "77000", "50000.0", "HKD 77,000.50", "$50,000", "123456.78",
            "116523.87", "147585.59", "10575.19", "1", "200", "336000"
        ]
        
        for sample in amount_samples:
            normalized = strict_normalization_functions['amount'](sample)
            # Should be digits only (no decimals, no currency symbols)
            self.assertTrue(normalized.isdigit() or '■' in normalized, 
                          f"Amount '{sample}' normalized to '{normalized}' is not valid")
    
    def test_police_reference_patterns(self):
        """Test police reference patterns from your CSV data"""
        police_samples = [
            "TYRN240■■■■", "KCRN240■■■■", "KTRN230■■■■", "TMRN240■■■■",
            "TSWRN240■■■■", "STRN240■■■■", "SSRN250■■■■", "YLRN 250■■■■",
            "C RN 250■■■■■■■", "HH RN 250■■■■", "MK RN 2500■■■■■■■",
            "ESPS ■■■■/2024 and WTSDIST ■■■■■■■■", "ESPS ■■■/2025 and KT RN ■■■■■■■■",
            "POLICEREF1", "Policeref2", "TM 001", "TM RN 002", "NP RN 001"
        ]
        
        police_patterns = [
            r'[A-Z]+RN\d*■*',
            r'[A-Z]+\s+RN\s+\d*■*',
            r'ESPS\s+■*\d*/\d{4}\s+and\s+\w+\s+■*\d*',
            r'POLICEREF\d+',
            r'Policeref\d+',
            r'TM\s+\d+',
            r'TM\s+RN\s+\d+'
        ]
        
        for sample in police_samples:
            matched = any(re.search(pat, sample, re.IGNORECASE) for pat in police_patterns)
            self.assertTrue(matched, f"Police reference sample '{sample}' did not match any pattern")
    
    def test_writ_no_patterns(self):
        """Test writ number patterns from your CSV data"""
        writ_samples = [
            "01■■■", "00■■■", "1■■■", "3■■■", "5■■■", "6■■■", "8■■■",
            "12■■■", "17■■■■", "67■■", "TM■■■", "TM12■■■/2024",
            "TM19■■ /2025", "TM86■■/2024", "3■■■/2025", "5■■/2025",
            "6■■■/2024", "TM ■■■■"
        ]
        
        writ_patterns = [
            r'\d+■*',
            r'TM\d*■*',
            r'TM\d*■*/\d{4}',
            r'\d+■*/\d{4}',
            r'TM\s+■*\d*'
        ]
        
        for sample in writ_samples:
            matched = any(re.search(pat, sample, re.IGNORECASE) for pat in writ_patterns)
            self.assertTrue(matched, f"Writ no sample '{sample}' did not match any pattern")
    
    def test_contact_person_patterns(self):
        """Test contact person patterns from your CSV data"""
        contact_samples = [
            "PC 1■■■■", "PC 2■■■■", "PC 6■■■■", "PC ■■■■■", "PC■■■■■",
            "SGT 2■■■■", "SGT 5■■■■", "SGT A■■■"
        ]
        
        contact_patterns = [
            r'PC\s+\d*■*',
            r'PC\d*■*',
            r'SGT\s+[A-Z]?\d*■*'
        ]
        
        for sample in contact_samples:
            matched = any(re.search(pat, sample, re.IGNORECASE) for pat in contact_patterns)
            self.assertTrue(matched, f"Contact person sample '{sample}' did not match any pattern")
    
    def test_transaction_channel_patterns(self):
        """Test transaction channel patterns"""
        channel_samples = [
            "FPS", "ATM", "Branch", "cash", "Cash", ""
        ]
        
        channel_patterns = [
            r'FPS',
            r'ATM',
            r'Branch',
            r'cash',
            r'Cash',
            r'^$'  # Empty string
        ]
        
        for sample in channel_samples:
            matched = any(re.fullmatch(pat, sample, re.IGNORECASE) for pat in channel_patterns)
            self.assertTrue(matched, f"Channel sample '{sample}' did not match any pattern")
    
    def test_normalization_functions(self):
        """Test all normalization functions"""
        # Test name normalization
        self.assertEqual(normalize_name_strict("Mr. Chan Tai Man"), "CHAN TAI MAN")
        self.assertEqual(normalize_name_strict("MISS YEUNG KAI"), "YEUNG KAI")
        self.assertEqual(normalize_name_strict("Dr LEE KA WAI AND OTHERS"), "LEE KA WAI")
        self.assertEqual(normalize_name_strict("NIL"), "NIL")
        
        # Test amount normalization
        self.assertEqual(strict_normalization_functions['amount']("77000.0"), "77000")
        self.assertEqual(strict_normalization_functions['amount']("HKD 50,000"), "50000")
        self.assertEqual(strict_normalization_functions['amount']("000402■■■■■■■"), "000402■■■■■■■")
        
        # Test account normalization - UPDATED: FPS should be preserved
        self.assertEqual(normalize_account_number_strict("FPS:122222221"), "FPS:122222221")
        self.assertEqual(normalize_account_number_strict("FPS 122222221"), "FPS:122222221")
        self.assertEqual(normalize_account_number_strict("111-111111-101"), "111-111111-101")
        self.assertEqual(normalize_account_number_strict("000402■■■■■■■"), "000402■■■■■■■")
        
        # Test bank normalization - UPDATED: HASE ≠ HSBC
        self.assertEqual(normalize_bank("The Hongkong and Shanghai Banking Corporation Limited"), "HSBC")
        self.assertEqual(normalize_bank("HASE"), "HASE")  # Changed expectation
        self.assertEqual(normalize_bank("024"), "HASE")   # Changed expectation
        self.assertEqual(normalize_bank("004"), "HSBC")
        self.assertEqual(normalize_bank("ICBKCNB■■■■"), "ICBKCNB■■■■")
    
    def test_random_generation_functions(self):
        """Test all random generation functions"""
        # Test that functions return valid values
        date_val = generate_random_date()
        self.assertIsInstance(date_val, str)
        self.assertTrue(len(date_val) > 0)
        
        amount_val = generate_random_amount()
        self.assertIsInstance(amount_val, str)
        self.assertTrue(amount_val.replace('.', '').isdigit())
        
        account_val = generate_random_account_number()
        self.assertIsInstance(account_val, str)
        self.assertTrue(len(account_val) > 0)
        
        police_val = generate_random_police_reference()
        self.assertIsInstance(police_val, str)
        self.assertTrue(len(police_val) > 0)
        
        writ_val = generate_random_writ_no()
        self.assertIsInstance(writ_val, str)
        self.assertTrue(len(writ_val) > 0)
        
        contact_val = generate_random_contact_person()
        self.assertIsInstance(contact_val, str)
        self.assertTrue(len(contact_val) > 0)

if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(argv=[''], verbosity=2, exit=False)

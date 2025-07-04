import unittest
import tempfile
import os
import pandas as pd
import json
from data_processor import (
    extract_unique_values, normalize_name_strict, normalize_amount_strict,
    normalize_account_number_strict, normalize_bank, normalize_police_reference_strict,
    normalize_writ_no_strict, normalize_contact_person_strict, generate_random_amount,
    generate_random_account_number, generate_random_police_reference,
    generate_random_writ_no, generate_random_contact_person, find_variations,
    replace_variations, replace_in_dataframe, random_generation_functions,
    NORMALIZED_NAMES, save_json_utf8, load_json_utf8, randomize_masked_value
)

class TestDataProcessor(unittest.TestCase):
    
    def setUp(self):
        """Set up test data"""
        self.test_data = {
            'Transactions': [
                'date,amount,currency,from.name,from.account_number,from.bank,to.name,to.account_number,to.bank,channel\n2024-11-12,77000,HKD,CHAN TAI MAN,333-333333-101,滙豐,MR CHAN TAI MAN,000402■■■■■■■,HASE,FPS'
            ],
            'Input': ['MR CHAN, TAIMAN did a transaction with account 000402■■■■■■■'],
            'Ground Truth': [json.dumps({
                "fraud_type": "Not provided",
                "alerted_transactions": [
                    {
                        "date": "2024-11-12",
                        "amount": 77000,
                        "currency": "HKD",
                        "from": {
                            "name": "CHAN TAI MAN",
                            "account_number": "333-333333-101",
                            "bank": "滙豐"
                        },
                        "to": {
                            "name": "MR CHAN TAI MAN",
                            "account_number": "000402■■■■■■■",
                            "bank": "HASE"
                        },
                        "channel": "FPS",
                        "cancel_amount_requested": 20000
                    }
                ]
            }, ensure_ascii=False)]
        }
        
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', encoding='utf-8-sig')
        df = pd.DataFrame(self.test_data)
        df.to_csv(self.temp_file.name, index=False, encoding='utf-8-sig')
        self.temp_file.close()
    
    def tearDown(self):
        """Clean up test data"""
        os.unlink(self.temp_file.name)
    
    def test_normalization_keeps_masked_chars(self):
        """Test that normalization keeps ■ characters as-is"""
        self.assertEqual(normalize_account_number_strict("000402■■■■■■■"), "000402■■■■■■■")
        self.assertEqual(normalize_police_reference_strict("TYRN240■■■■"), "TYRN240■■■■")
        self.assertEqual(normalize_writ_no_strict("01■■■"), "01■■■")
        self.assertEqual(normalize_contact_person_strict("PC 2■■■■"), "PC 2■■■■")
    
    def test_randomize_masked_value(self):
        """Test that randomization replaces ■ with random characters"""
        original = "000402■■■■■■■"
        randomized = randomize_masked_value(original)
        self.assertNotEqual(original, randomized)
        self.assertNotIn('■', randomized)
        self.assertTrue(randomized.startswith('000402'))
    
    def test_utf8_sig_handling(self):
        """Test UTF-8-sig handling with ■ and Chinese characters"""
        test_data = {"account": "000402■■■■■■■", "bank": "滙豐"}
        
        temp_json = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_json.close()
        
        try:
            save_json_utf8(test_data, temp_json.name)
            loaded_data = load_json_utf8(temp_json.name)
            
            self.assertEqual(loaded_data["account"], "000402■■■■■■■")
            self.assertEqual(loaded_data["bank"], "滙豐")
        finally:
            os.unlink(temp_json.name)
    
    def test_extraction_with_masked_chars(self):
        """Test extraction preserves ■ characters"""
        try:
            result = extract_unique_values(self.temp_file.name)
            self.assertIsInstance(result, dict)
            # Should contain values with ■ characters
            if 'account_number' in result:
                masked_accounts = [acc for acc in result['account_number'] if '■' in acc]
                self.assertTrue(len(masked_accounts) > 0)
        except Exception as e:
            self.fail(f"Extraction with masked chars failed: {e}")

if __name__ == '__main__':
    unittest.main()

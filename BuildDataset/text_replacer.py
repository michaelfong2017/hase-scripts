import json
import re
from typing import Dict, Any

class TextReplacer:
    def __init__(self, mappings: Dict[str, str]):
        self.mappings = mappings
    
    def replace_in_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Replace values in JSON structure"""
        return self._replace_recursive(json_data)
    
    def replace_in_text(self, text: str) -> str:
        """Replace values in plain text using placeholder approach"""
        modified_text = text
        replacement_map = {}
        
        # Sort mappings by length (longest first) to avoid partial replacements
        sorted_mappings = sorted(self.mappings.items(), key=lambda x: len(x[0]), reverse=True)
        
        # ADDED: Also try to match normalized versions of text patterns
        # Find amount patterns in text and normalize them for matching
        amount_patterns = re.finditer(r'(HKD|USD|CNY|SGD)?\s*[\d,]+\.?\d*', text, re.IGNORECASE)
        
        for match in amount_patterns:
            original_amount = match.group(0)
            normalized_amount = self._normalize_amount_candidate(original_amount)
            
            # Check if normalized amount has a mapping
            if normalized_amount in self.mappings:
                if original_amount not in replacement_map:
                    replacement_map[original_amount] = self.mappings[normalized_amount]
        
        # Step 1: Replace with unique placeholders (including normalized matches)
        placeholder_counter = 0
        final_replacement_map = {}
        
        # First handle direct mappings
        for old_value, new_value in sorted_mappings:
            if old_value in modified_text:
                placeholder = f"__PLACEHOLDER_{placeholder_counter}__"
                modified_text = modified_text.replace(old_value, placeholder)
                final_replacement_map[placeholder] = new_value
                placeholder_counter += 1
        
        # Then handle normalized amount matches
        for original_amount, new_value in replacement_map.items():
            if original_amount in modified_text:
                placeholder = f"__PLACEHOLDER_{placeholder_counter}__"
                modified_text = modified_text.replace(original_amount, placeholder)
                final_replacement_map[placeholder] = new_value
                placeholder_counter += 1
        
        # Step 2: Replace placeholders with final values
        for placeholder, new_value in final_replacement_map.items():
            modified_text = modified_text.replace(placeholder, new_value)
        
        return modified_text

    def _normalize_amount_candidate(self, candidate_str: str) -> str:
        """Normalize amount candidate for matching"""
        # Remove currency prefixes
        normalized = re.sub(r'^(HKD|USD|CNY|SGD)\s*', '', candidate_str, flags=re.IGNORECASE)
        # Remove commas
        normalized = normalized.replace(',', '')
        # Remove trailing .00 if present
        if normalized.endswith('.00'):
            normalized = normalized[:-3]
        return normalized
    
    def _replace_recursive(self, obj: Any) -> Any:
        """Recursively replace values in nested structures"""
        if isinstance(obj, dict):
            new_dict = {}
            for key, value in obj.items():
                new_dict[key] = self._replace_recursive(value)
            return new_dict
            
        elif isinstance(obj, list):
            return [self._replace_recursive(item) for item in obj]
            
        else:
            # Check multiple representations of the value
            candidates = [str(obj), obj]
            
            # For numeric values, also try formatted versions
            if isinstance(obj, (int, float)):
                candidates.extend([
                    f"{obj:.2f}",
                    f"{obj:,.2f}",
                    f"HKD {obj:.2f}",
                    f"HKD {obj:,.2f}",
                ])
            
            # FIXED: Try to find a mapping for any candidate with normalization
            for candidate in candidates:
                candidate_str = str(candidate)
                
                # Try exact match first
                if candidate_str in self.mappings:
                    replacement = self.mappings[candidate_str]
                    return self._convert_to_original_type(obj, replacement)
                
                # Try normalized match for amounts
                normalized_candidate = self._normalize_amount_candidate(candidate_str)
                if normalized_candidate in self.mappings:
                    replacement = self.mappings[normalized_candidate]
                    return self._convert_to_original_type(obj, replacement)
            
            return obj

    def _normalize_amount_candidate(self, candidate_str: str) -> str:
        """Normalize amount candidate for matching"""
        # Remove currency prefixes
        normalized = re.sub(r'^(HKD|USD|CNY|SGD)\s*', '', candidate_str, flags=re.IGNORECASE)
        # Remove commas
        normalized = normalized.replace(',', '')
        # Remove trailing .00 if present
        if normalized.endswith('.00'):
            normalized = normalized[:-3]
        return normalized

    def _convert_to_original_type(self, original_obj, replacement):
        """Convert replacement back to original type if needed"""
        if isinstance(original_obj, (int, float)):
            try:
                # Extract numeric part from replacement
                numeric_part = re.search(r'[\d.]+', replacement)
                if numeric_part:
                    if isinstance(original_obj, int):
                        return int(float(numeric_part.group()))
                    else:
                        return float(numeric_part.group())
            except:
                pass
        
        return replacement


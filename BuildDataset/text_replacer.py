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
        
        # Step 1: Replace with unique placeholders
        for i, (old_value, new_value) in enumerate(sorted_mappings):
            if old_value in modified_text:
                placeholder = f"__PLACEHOLDER_{i}__"
                modified_text = modified_text.replace(old_value, placeholder)
                replacement_map[placeholder] = new_value
        
        # Step 2: Replace placeholders with final values
        for placeholder, new_value in replacement_map.items():
            modified_text = modified_text.replace(placeholder, new_value)
        
        return modified_text
    
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
            candidates = [
                str(obj),  # Original string representation
                obj,       # Original value
            ]
            
            # For numeric values, also try formatted versions
            if isinstance(obj, (int, float)):
                candidates.extend([
                    f"{obj:.2f}",           # 1248.00
                    f"{obj:,.2f}",          # 1,248.00
                    f"HKD {obj:.2f}",       # HKD 1248.00
                    f"HKD {obj:,.2f}",      # HKD 1,248.00
                ])
            
            # Try to find a mapping for any candidate
            for candidate in candidates:
                candidate_str = str(candidate)
                if candidate_str in self.mappings:
                    replacement = self.mappings[candidate_str]
                    
                    # Try to maintain original type for numeric values
                    if isinstance(obj, (int, float)):
                        try:
                            # Extract numeric part from replacement
                            numeric_part = re.search(r'[\d.]+', replacement)
                            if numeric_part:
                                if isinstance(obj, int):
                                    return int(float(numeric_part.group()))
                                else:
                                    return float(numeric_part.group())
                        except:
                            pass
                    
                    return replacement
            
            return obj

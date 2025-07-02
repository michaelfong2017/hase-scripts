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
        """Replace values in plain text"""
        modified_text = text
        
        # Sort mappings by length (longest first) to avoid partial replacements
        sorted_mappings = sorted(self.mappings.items(), key=lambda x: len(x), reverse=True)
        
        for old_value, new_value in sorted_mappings:
            if old_value in modified_text:
                modified_text = modified_text.replace(old_value, new_value)
        
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
            # Check if this value needs replacement
            str_value = str(obj)
            if str_value in self.mappings:
                replacement = self.mappings[str_value]
                # Try to maintain original type
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

import json
import re
from typing import Dict, Any

class JSONParser:
    def __init__(self):
        pass
    
    def parse_json(self, ground_truth_str: str) -> Dict[str, Any]:
        """Parse ground truth JSON from various formats"""
        try:
            # Extract JSON content from markdown if present
            json_content = ground_truth_str
            if ground_truth_str.strip().startswith('```json'):
                match = re.search(r'```json\s*(.*?)\s*```', ground_truth_str, re.DOTALL)
                if match:
                    json_content = match.group(1).strip()
                else:
                    raise ValueError("Could not extract JSON from markdown code block")
            
            # Parse the JSON
            return json.loads(json_content)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise ValueError(f"Error parsing JSON: {str(e)}")

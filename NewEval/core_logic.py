import json
import re

# Load the inverted_sorted_mappings.json once at module level
try:
    with open('inverted_sorted_mappings.json', 'r', encoding='utf-8') as f:
        INVERTED_MAPPINGS = json.load(f)
    print("[✓] Loaded inverted_sorted_mappings.json for field mapping")
except FileNotFoundError:
    print("[!] Warning: inverted_sorted_mappings.json not found. Using fallback logic.")
    INVERTED_MAPPINGS = {}
except json.JSONDecodeError:
    print("[!] Warning: inverted_sorted_mappings.json is not valid JSON. Using fallback logic.")
    INVERTED_MAPPINGS = {}

def extract_json_content(text):
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    match2 = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
    match3 = re.search(r'```json\s*(\{.*\})', text, re.DOTALL)  # New case for no closing tag
    match4 = re.search(r'```\s*(\{.*\})', text, re.DOTALL)  # New case for no closing tag

    if match:
        return json.loads(match.group(1))
    elif match2:
        return json.loads(match2.group(1))
    elif match3:
        return json.loads(match3.group(1))
    elif match4:
        return json.loads(match4.group(1))
    else:
        return json.loads(text)

def are_exact_match_for_eval(value1, value2, key):
    """Enhanced comparison using inverted mappings for specific fields."""
    null_representations = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
    
    try:
        val1_is_null = value1 in null_representations
    except TypeError:
        val1_is_null = False
    try:
        val2_is_null = value2 in null_representations
    except TypeError:
        val2_is_null = False
    
    if val1_is_null and val2_is_null:
        return True
    if val1_is_null or val2_is_null:
        return False

    # Special handling for transaction_references field
    if key == 'transaction_references':
        if isinstance(value1, list) and isinstance(value2, list):
            set1 = set(str(item).strip() for item in value1 if item not in null_representations)
            set2 = set(str(item).strip() for item in value2 if item not in null_representations)
            return set1 == set2
        return False

    # Numeric comparison
    if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
        return value1 == value2

    # Boolean comparison
    if isinstance(value1, bool) and isinstance(value2, bool):
        return value1 == value2

    # String preparation
    val1_str = str(value1).strip()
    val2_str = str(value2).strip()
    key_lower = key.lower()

    # Account number special handling
    if 'account_number' in key_lower:
        val1_str = val1_str.replace('(', '').replace(')', '').replace('-', '')
        val2_str = val2_str.replace('(', '').replace(')', '').replace('-', '')

    # Use inverted mappings if available
    if key_lower in INVERTED_MAPPINGS:
        mapping = INVERTED_MAPPINGS[key_lower]
        mapped_val1 = mapping.get(val1_str, val1_str)
        mapped_val2 = mapping.get(val2_str, val2_str)
        return mapped_val1 == mapped_val2

    # Default case-insensitive comparison
    try:
        val1_str = val1_str.encode().decode('unicode_escape')
        val2_str = val2_str.encode().decode('unicode_escape')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return val1_str.lower() == val2_str.lower()

def compare_structures_for_eval(obj1, obj2, path="", comparison_count=[0]):
    """Recursively compare JSON objects with enhanced field matching."""
    mismatches = []
    
    # Define fields to ignore in LLM output
    IGNORE_FIELDS = {'rematch_note', 'original_amount'}

    if isinstance(obj1, dict) and isinstance(obj2, dict):
        all_keys = set(obj1.keys()) | set(obj2.keys())
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            
            # Skip ignored fields when they're extra in LLM output
            if key not in obj2 and key in IGNORE_FIELDS:
                continue
                
            if key not in obj1:
                mismatches.append(f"{current_path}: Missing in LLM output (Truth has value: {obj2.get(key)})")
            elif key not in obj2:
                mismatches.append(f"{current_path}: Extra in LLM output (LLM has value: {obj1.get(key)})")
            else:
                mismatches.extend(compare_structures_for_eval(obj1[key], obj2[key], current_path, comparison_count))

    elif isinstance(obj1, list) and isinstance(obj2, list):
        # Special handling for transaction_references - compare as whole lists
        if path.endswith('transaction_references'):
            field_name = 'transaction_references'
            if not are_exact_match_for_eval(obj1, obj2, field_name):
                mismatches.append(f"{path}: Value Mismatch - LLM: '{obj1}', Truth: '{obj2}'")
        else:
            # Regular list comparison for other fields
            if len(obj1) != len(obj2):
                mismatches.append(f"{path}: List length mismatch - LLM: {len(obj1)}, Truth: {len(obj2)}")
            else:
                for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                    mismatches.extend(compare_structures_for_eval(item1, item2, f"{path}[{i}]", comparison_count))

    else:
        # Extract field name for mapping
        if 'alerted_transactions[' in path and '].' in path:
            field_part = path.split('].', 1)[1]
            field_for_mapping = field_part.split('.')[-1] if '.' in field_part else field_part
        else:
            field_for_mapping = path.split('.')[-1].split('[')[0]
        
        if not are_exact_match_for_eval(obj1, obj2, field_for_mapping):
            mismatches.append(f"{path}: Value Mismatch - LLM: '{obj1}', Truth: '{obj2}'")

    return mismatches

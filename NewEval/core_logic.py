import json
import re

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
    """Simple exact match for this script."""
    nulls = {None, "None", "null", "NULL", "NaN", "nan", "Nil", "nil", "", "N/A", "n/a"}
    
    try:
        val1_is_null = value1 in nulls
    except TypeError:
        val1_is_null = False
    try:
        val2_is_null = value2 in nulls
    except TypeError:
        val2_is_null = False
    
    if val1_is_null and val2_is_null:
        return True
    if val1_is_null or val2_is_null:
        return False
    
    return str(value1).strip().lower() == str(value2).strip().lower()

def compare_structures_for_eval(obj1, obj2, path=""):
    """Recursively compare two JSON objects, return list of mismatch strings."""
    mismatches = []
    
    if isinstance(obj1, dict) and isinstance(obj2, dict):
        all_keys = set(obj1) | set(obj2)
        for k in all_keys:
            p = f"{path}.{k}" if path else k
            if k not in obj1:
                mismatches.append(f"{p}: Missing in LLM output (Truth has value: {obj2.get(k)})")
            elif k not in obj2:
                mismatches.append(f"{p}: Extra in LLM output (LLM has value: {obj1.get(k)})")
            else:
                mismatches.extend(compare_structures_for_eval(obj1[k], obj2[k], p))
    elif isinstance(obj1, list) and isinstance(obj2, list):
        if len(obj1) != len(obj2):
            mismatches.append(f"{path}: List length mismatch - LLM: {len(obj1)}, Truth: {len(obj2)}")
        else:
            for i, (a, b) in enumerate(zip(obj1, obj2)):
                mismatches.extend(compare_structures_for_eval(a, b, f"{path}[{i}]"))
    else:
        key = path.split('.')[-1]
        if not are_exact_match_for_eval(obj1, obj2, key):
            mismatches.append(f"{path}: Value Mismatch - LLM: '{obj1}', Truth: '{obj2}'")
    
    return mismatches

# core_logic.py
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

# --- Shared Utilities ---

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
    
# --- Evaluation-Specific Logic ---

def are_exact_match_for_eval(value1, value2, key):
    """
    Compares two values using field-specific exact match rules for evaluation reports.
    Uses simple == for numeric comparison and case-insensitive string comparison.
    """
    # --- Handle various null representations ---
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

    # --- Special handling for transaction_references field (order-independent set comparison) ---
    if key == 'transaction_references':
        if isinstance(value1, list) and isinstance(value2, list):
            # Convert to sets for order-independent comparison
            set1 = set(str(item).strip() for item in value1 if item not in null_representations)
            set2 = set(str(item).strip() for item in value2 if item not in null_representations)
            return set1 == set2
        # If one is list and other isn't, they don't match
        return False

    # --- Simple numeric comparison using == ---
    if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
        return value1 == value2

    # --- Direct boolean comparison ---
    if isinstance(value1, bool) and isinstance(value2, bool):
        return value1 == value2

    # --- For writ_no and contact_person, do exact match without any mapping ---
    if key in ['writ_no', 'contact_person']:
        return str(value1).strip().lower() == str(value2).strip().lower()

    # --- Prepare string values for comparison ---
    val1_str = str(value1).strip()
    val2_str = str(value2).strip()
    key_lower = key.lower()

    # --- Special handling for account_number fields ---
    if 'account_number' in key_lower:
        val1_str = val1_str.replace('(', '').replace(')', '').replace('-', '')
        val2_str = val2_str.replace('(', '').replace(')', '').replace('-', '')

    # --- Use inverted mappings if available for this field ---
    if key_lower in INVERTED_MAPPINGS:
        mapping = INVERTED_MAPPINGS[key_lower]
        mapped_val1 = mapping.get(val1_str, val1_str)
        mapped_val2 = mapping.get(val2_str, val2_str)
        return mapped_val1 == mapped_val2

    # --- Default to case-insensitive string comparison ---
    try:
        val1_str = val1_str.encode().decode('unicode_escape')
        val2_str = val2_str.encode().decode('unicode_escape')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return val1_str.lower() == val2_str.lower()

def compare_structures_for_eval(obj1, obj2, path="", comparison_count=[0]):
    """
    Recursively compares two JSON objects and lists human-readable mismatches.
    --- FIXED: Proper field extraction for your mapping structure ---
    """
    mismatches = []

    if isinstance(obj1, dict) and isinstance(obj2, dict):
        all_keys = set(obj1.keys()) | set(obj2.keys())
        for key in all_keys:
            current_path = f"{path}.{key}" if path else key
            if key not in obj1: 
                mismatches.append(f"{current_path}: Missing in LLM output (Truth has value: {obj2.get(key)})")
                if comparison_count[0] < 3:
                    print(f"DEBUG [Comparison {comparison_count[0] + 1}/3]: {current_path} - Missing in LLM output (Truth has value: {obj2.get(key)})")
                    comparison_count[0] += 1
            elif key not in obj2: 
                mismatches.append(f"{current_path}: Extra in LLM output (LLM has value: {obj1.get(key)})")
                if comparison_count[0] < 3:
                    print(f"DEBUG [Comparison {comparison_count[0] + 1}/3]: {current_path} - Extra in LLM output (LLM has value: {obj1.get(key)})")
                    comparison_count[0] += 1
            else: 
                mismatches.extend(compare_structures_for_eval(obj1[key], obj2[key], current_path, comparison_count))
    elif isinstance(obj1, list) and isinstance(obj2, list):
        if len(obj1) != len(obj2):
            mismatches.append(f"{path}: List length mismatch - LLM: {len(obj1)}, Truth: {len(obj2)}")
            if comparison_count[0] < 3:
                print(f"DEBUG [Comparison {comparison_count[0] + 1}/3]: {path} - List length mismatch - LLM: {len(obj1)}, Truth: {len(obj2)}")
                comparison_count[0] += 1
        else:
            for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                mismatches.extend(compare_structures_for_eval(item1, item2, f"{path}[{i}]", comparison_count))
    else:
        # --- FIXED: Extract field name to match your mapping structure ---
        if 'alerted_transactions[' in path and '].' in path:
            # For "alerted_transactions[0].to.name" -> extract "name"
            field_part = path.split('].', 1)[1]  # Gets "to.name"
            if '.' in field_part:
                field_for_mapping = field_part.split('.')[-1]  # Gets "name"
            else:
                field_for_mapping = field_part
        else:
            # For top-level fields
            field_for_mapping = path.split('.')[-1].split('[')[0]
        
        if not are_exact_match_for_eval(obj1, obj2, field_for_mapping):
            mismatches.append(f"{path}: Value Mismatch - LLM: '{obj1}', Truth: '{obj2}'")
            if comparison_count[0] < 3:
                print(f"DEBUG [Comparison {comparison_count[0] + 1}/3]: {path} - Value Mismatch - LLM: '{obj1}', Truth: '{obj2}' (using field key: '{field_for_mapping}')")
                comparison_count[0] += 1
    return mismatches

def generate_evaluation_report(llm_json_str: str, gt_json_str: str) -> tuple:
    """
    Generates an evaluation report comparing LLM output to ground truth.
    """
    llm_json, gt_json = None, None
    extracted_llm_str, extracted_gt_str = None, None
    try:
        llm_json, gt_json = extract_json_content(llm_json_str), extract_json_content(gt_json_str)
        if llm_json is not None: 
            extracted_llm_str = json.dumps(llm_json, indent=2, ensure_ascii=False)
        if gt_json is not None: 
            extracted_gt_str = json.dumps(gt_json, indent=2, ensure_ascii=False)
        if llm_json is None and gt_json is None: return "PASS", True, True, True, extracted_llm_str, extracted_gt_str
        if llm_json is None: return "FAIL: LLM output did not contain valid JSON", False, False, False, extracted_llm_str, extracted_gt_str
        if gt_json is None: return "FAIL: Ground truth did not contain valid JSON", False, False, False, extracted_llm_str, extracted_gt_str
    except Exception as e:
        return f"FAIL: Error parsing JSON - {e}", False, False, False, extracted_llm_str, extracted_gt_str
    mismatches = compare_structures_for_eval(llm_json, gt_json)
    alert_mismatches, other_mismatches = [m for m in mismatches if m.startswith("alerted_transactions")], [m for m in mismatches if not m.startswith("alerted_transactions")]
    alert_pass, other_pass, overall_pass = not alert_mismatches, not other_mismatches, not mismatches
    if overall_pass:
        report = "PASS"
    else:
        parts = ["FAIL:"]
        if other_mismatches: parts.extend(["Other Fields Mismatches:"] + [f"  - {m}" for m in other_mismatches])
        if alert_mismatches: parts.extend(["Alerted Transactions Mismatches:"] + [f"  - {m}" for m in alert_mismatches])
        report = "\n".join(parts)
    return report, alert_pass, other_pass, overall_pass, extracted_llm_str, extracted_gt_str

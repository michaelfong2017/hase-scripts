import json
from jsondiff import diff

def count_entries(obj):
    """
    Recursively count the number of leaf entries in a JSON object.
    Only counts actual values, not intermediate structures.
    
    Args:
        obj: JSON object (dict, list, or primitive)
        
    Returns:
        int: Total number of leaf entries
    """
    if isinstance(obj, dict):
        count = 0
        for value in obj.values():
            count += count_entries(value)
        return count
    elif isinstance(obj, list):
        count = 0
        for item in obj:
            count += count_entries(item)
        return count
    else:
        return 1  # Count only leaf nodes

def count_differences(diff_result):
    """
    Count the number of actual differences in the diff result.
    
    Args:
        diff_result: The diff result from jsondiff
        
    Returns:
        int: Number of actual differences
    """
    if isinstance(diff_result, dict):
        count = 0
        for key, value in diff_result.items():
            if str(key) == 'delete':
                if isinstance(value, list):
                    count += len(value)
                else:
                    count += 1
            elif str(key) == 'insert':
                if isinstance(value, list):
                    for _, item in value:
                        count += count_entries(item)
            else:
                if isinstance(value, (dict, list)):
                    count += count_differences(value)
                else:
                    count += 1
        return count
    elif isinstance(diff_result, list):
        return sum(count_differences(item) for item in diff_result)
    else:
        return 1

def format_diff(diff_result, indent=0):
    """
    Format the diff result in a human-readable format.
    
    Args:
        diff_result: The diff result from jsondiff
        indent (int): Current indentation level
        
    Returns:
        str: Formatted diff string
    """
    indent_str = "  " * indent
    output = []
    
    if isinstance(diff_result, dict):
        for key, value in diff_result.items():
            # Handle special jsondiff keys
            if str(key) == 'delete':
                if isinstance(value, list):
                    output.append(f"{indent_str}- Deleted fields: {', '.join(str(x) for x in value)}")
                else:
                    output.append(f"{indent_str}- Deleted: {value}")
            elif str(key) == 'insert':
                if isinstance(value, list):
                    output.append(f"{indent_str}+ Inserted at positions:")
                    for pos, item in value:
                        output.append(f"{indent_str}  Position {pos}:")
                        output.append(format_diff(item, indent + 2))
            else:
                # Handle regular dictionary keys
                if isinstance(value, (dict, list)):
                    output.append(f"{indent_str}Changes in '{key}':")
                    output.append(format_diff(value, indent + 1))
                else:
                    output.append(f"{indent_str}Changed '{key}' to: {value}")
    elif isinstance(diff_result, list):
        for item in diff_result:
            output.append(format_diff(item, indent))
    else:
        output.append(f"{indent_str}{diff_result}")
    
    return "\n".join(output)

def clean_json_string(json_str):
    """
    Clean a JSON string by removing any characters before the first '{' and after the last '}'.
    
    Args:
        json_str (str): Input string that contains JSON
        
    Returns:
        str: Cleaned JSON string
    """
    try:
        start = json_str.index('{')
        end = json_str.rindex('}') + 1
        return json_str[start:end]
    except ValueError:
        # If no { or } is found, return the original string
        return json_str

def compare_json_strings(json_str1, json_str2):
    """
    Compare two JSON strings and return their differences.
    
    Args:
        json_str1 (str): First JSON string
        json_str2 (str): Second JSON string
        
    Returns:
        tuple: (differences, json1, json2) - The differences and parsed JSON objects
    """
    try:
        # Clean the JSON strings
        json_str1 = clean_json_string(json_str1)
        json_str2 = clean_json_string(json_str2)
        
        # Parse JSON strings into Python dictionaries
        json1 = json.loads(json_str1)
        json2 = json.loads(json_str2)
        
        # Calculate difference between the two JSON objects (outputs how to get from json1 to json2)
        difference = diff(json1, json2)
        return difference, json1, json2
    except json.JSONDecodeError as e:
        return f"Error parsing JSON: {str(e)}", None, None

# Example usage
json_str1 = '''
Some random text before the JSON
{
  "source": "Internal Referral",
  "fraud_type": "External Fraud",
  "alerted_transactions": [
    {
      "date": "2024-11-12",
      "amount": "HKD77,000",
      "from": {
        "name": "CHAN TAI MAN",
        "account_number": "333-333333-101",
        "bank": "HASE"
      },
      "to": {
        "name": "CHAN TAI MAN",
        "account_number": "111-111111-101",
        "bank": "HASE"
      },
      "channel": "FPS"
    }
  ]
}
And some random text after the JSON
'''

json_str2 = '''
{
  "source": "Internal Referral",
  "fraud_type": "External Fraud",
  "alerted_transactions": [
    {
      "date": "2024-11-12",
      "amount": "HKD77,000",
      "from": {
        "name": "CHAN TAI MAN",
        "account_number": "333-333333-101"
      },
      "to": {
        "name": "CHAN TAI MAN",
        "account_number": "111-111111-101",
        "bank": "HASE"
      },
      "channel": "FPS"
    }
  ]
}
'''

# Get the differences and parsed JSON objects
differences, json1, json2 = compare_json_strings(json_str1, json_str2)

if isinstance(differences, str):  # Error occurred
    print(differences)
else:
    # Print the formatted differences
    print("Differences between JSON 1 and JSON 2:")
    print(format_diff(differences))
    
    # Calculate and print the matching score
    total_entries = count_entries(json2)
    diff_count = count_differences(differences)
    matching_entries = total_entries - diff_count
    match_percentage = (matching_entries / total_entries) * 100
    
    print("\nMatching Score:")
    print(f"Total entries in JSON 2: {total_entries}")
    print(f"Different entries: {diff_count}")
    print(f"Matching entries: {matching_entries}")
    print(f"Match percentage: {match_percentage:.2f}%")

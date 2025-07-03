import os

def get_model_folder(file_path, output_base_folder):
    """Extract model name from file path and create folder."""
    base_name = os.path.basename(file_path)
    model_name = base_name.split('_test_set')[0]  # e.g. cycle2_final32B_full60
    folder_path = os.path.join(output_base_folder, model_name)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path, model_name

def flatten_json(y, parent_key='', sep='.'):
    """Flatten a nested JSON dict."""
    items = []
    if isinstance(y, dict):
        for k, v in y.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(flatten_json(v, new_key, sep=sep).items())
    elif isinstance(y, list):
        for i, v in enumerate(y):
            new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
            items.extend(flatten_json(v, new_key, sep=sep).items())
    else:
        items.append((parent_key, y))
    return dict(items)

def flatten_excluding_alerted(json_obj):
    """Flatten JSON excluding alerted_transactions."""
    if not isinstance(json_obj, dict):
        return {}
    return {k: v for k, v in flatten_json(json_obj).items() if not k.startswith('alerted_transactions')}

def tx_key(tx):
    """Generate key from transaction_references."""
    refs = tx.get("transaction_references", [])
    if not isinstance(refs, list):
        refs = [str(refs)]
    return ",".join(sorted(map(str, refs)))

def flatten_tx(tx):
    """Flatten transaction dict."""
    return flatten_json(tx) if isinstance(tx, dict) else {}

def is_transaction_field(field_name):
    """Check if a field name is transaction-related - COMPREHENSIVE VERSION."""
    transaction_keywords = [
        'transaction', 'tx', 'alerted', 'alert',
        'from', 'to', 'bank', 'account', 'date', 'amount', 'currency',
        'originator', 'beneficiary', 'reference', 'swift', 'iban',
        'transfer', 'payment', 'deposit', 'withdrawal', 'balance',
        'sender', 'receiver', 'payer', 'payee', 'routing',
        'transaction_references', 'can_be_located', 'channel',
        'name', 'account_number'  # These appear in transaction context
    ]
    field_lower = field_name.lower()
    
    # Check for direct keyword matches
    if any(keyword in field_lower for keyword in transaction_keywords):
        return True
    
    # Check for nested transaction field patterns like "to.name", "from.bank", etc.
    transaction_patterns = [
        'to.', 'from.', '.name', '.bank', '.account', '.amount', '.date', 
        '.currency', '.channel', '.can_be_located', '.transaction_references'
    ]
    if any(pattern in field_lower for pattern in transaction_patterns):
        return True
    
    return False

import pandas as pd
import sys
import os
import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

# ===== OPENROUTER MODEL CONFIGURATIONS =====
OPENROUTER_MODELS = [
    "google/gemini-2.0-flash-001"  # Only Gemini
]

# OpenRouter API settings
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# Threading configuration
MAX_WORKERS = 50  # Number of concurrent requests
RATE_LIMIT_DELAY = 0.1  # Delay between requests to avoid rate limits
TEMPERATURE = 0.0
# ==============================================

# Thread-safe lock for DataFrame updates
df_lock = threading.Lock()
progress_counter = 0
progress_lock = threading.Lock()

def load_instruction_for_type(type_name):
    """Load instruction from instruction/<Type> instruction.txt file"""
    instruction_file = f"instruction/{type_name} instruction.txt"
    
    if os.path.exists(instruction_file):
        try:
            with open(instruction_file, 'r', encoding='utf-8') as f:
                instruction = f.read().strip()
            print(f"Loaded instruction for type {type_name} from {instruction_file}")
            return instruction
        except Exception as e:
            print(f"Error reading instruction file for type {type_name}: {e}")
            return f"You are an AI assistant specialized in analyzing {type_name} documents. Please extract relevant information from the provided documents."
    else:
        print(f"Instruction file not found for type {type_name}: {instruction_file}")
        return f"You are an AI assistant specialized in analyzing {type_name} documents. Please extract relevant information from the provided documents."

def generate_response_openrouter(model_name: str, instruction: str, user_input: str, 
                                max_retries: int = 3, retry_delay: int = 5) -> str:
    """Generate a response using OpenRouter API"""
    
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY environment variable not set")
    
    messages = [
        {"role": "system", "content": instruction},
        {"role": "user", "content": user_input}
    ]
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/yourusername/dpo-scripts",
        "X-Title": "DPO Training Data Generation"
    }
    
    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": TEMPERATURE,
        "top_p": 1.0,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    
    for attempt in range(max_retries):
        try:
            # Add small random delay to spread out requests
            time.sleep(RATE_LIMIT_DELAY + (threading.current_thread().ident % 100) / 1000)
            
            response = requests.post(
                OPENROUTER_BASE_URL,
                headers=headers,
                json=payload,
                timeout=120  # 2 minute timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data["choices"][0]["message"]["content"]
            
            elif response.status_code == 429:  # Rate limit
                backoff_time = retry_delay * (2 ** attempt)  # Exponential backoff
                print(f"Rate limit hit for {model_name}, waiting {backoff_time} seconds...")
                time.sleep(backoff_time)
                continue
                
            elif response.status_code == 400:  # Bad request
                error_msg = response.json().get("error", {}).get("message", "Bad request")
                return f"ERROR: Bad request - {error_msg}"
                
            elif response.status_code == 401:  # Unauthorized
                return "ERROR: Invalid API key"
                
            elif response.status_code == 402:  # Insufficient credits
                return "ERROR: Insufficient credits"
                
            else:
                error_msg = response.json().get("error", {}).get("message", f"HTTP {response.status_code}")
                print(f"API error for {model_name}: {error_msg}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    return f"ERROR: {error_msg}"
                    
        except requests.exceptions.Timeout:
            print(f"Timeout for {model_name}, attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (2 ** attempt))
                continue
            else:
                return "ERROR: Request timeout"
                
        except requests.exceptions.RequestException as e:
            print(f"Request exception for {model_name}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                continue
            else:
                return f"ERROR: Request failed - {str(e)}"
                
        except Exception as e:
            print(f"Unexpected error for {model_name}: {e}")
            return f"ERROR: {str(e)}"
    
    return "ERROR: Max retries exceeded"

def process_single_request(args):
    """Process a single row/model combination"""
    model_name, instruction, user_input, row_index, column_name, transactions = args

    # ==== Begin custom logic ====
    # If transactions is not None and not empty, use the custom prompt logic
    if transactions is not None and str(transactions).strip() != "":
        user_prompt = (
            f"Now, process the following documents.\n"
            f"<FRAUD_ALERT_SOURCE>\n{user_input}\n</FRAUD_ALERT_SOURCE>\n"
            f"<TRANSACTION_RECORDS_CSV>\n{transactions}\n</TRANSACTION_RECORDS_CSV>"
        )
    else:
        user_prompt = user_input
    # ==== End custom logic ====

    try:
        response = generate_response_openrouter(model_name, instruction, user_prompt)
        
        # Update progress counter
        global progress_counter
        with progress_lock:
            progress_counter += 1
        
        return row_index, column_name, response
        
    except Exception as e:
        print(f"Error processing row {row_index} with {model_name}: {e}")
        return row_index, column_name, f"ERROR: {str(e)}"

def clean_model_name(model_name: str) -> str:
    """Convert model name to a clean column name"""
    return model_name.replace("/", "_").replace("-", "_").replace(".", "_")

def main():
    global progress_counter
    
    # Load CSV data
    csv_file = "Dataset_Source_v5_original_set.csv"
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    # Check if file exists
    if not os.path.exists(csv_file):
        print(f"Error: CSV file '{csv_file}' not found")
        return
    
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} rows from {csv_file}")
    
    # Check for required columns
    required_columns = ["Type", "Input"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        print(f"Error: Missing required columns: {missing_columns}")
        print(f"Available columns: {list(df.columns)}")
        return
    
    # Load instructions for each type and update the Instruction column
    print("Loading type-specific instructions...")
    for index, row in df.iterrows():
        type_name = row['Type']
        instruction = load_instruction_for_type(type_name)
        df.at[index, 'Instruction'] = instruction
    
    # Create output columns for each model if they don't exist
    for model_name in OPENROUTER_MODELS:
        clean_name = clean_model_name(model_name)
        column_name = f"Output_{clean_name}"
        if column_name not in df.columns:
            df[column_name] = ""
            print(f"Added column: {column_name}")
    
    print(f"Using OpenRouter models: {OPENROUTER_MODELS}")
    
    # Check API key
    if not OPENROUTER_API_KEY:
        print("❌ ERROR: OPENROUTER_API_KEY environment variable not set")
        print("Please set your API key: export OPENROUTER_API_KEY='your-key-here'")
        return
    
    print(f"Using {MAX_WORKERS} concurrent workers")
    print(f"Processing {len(OPENROUTER_MODELS)} models with {len(df)} rows each")
    
    # Prepare all tasks
    tasks = []
    for model_name in OPENROUTER_MODELS:
        clean_name = clean_model_name(model_name)
        column_name = f"Output_{clean_name}"
        
        for index, row in df.iterrows():
            # Skip if already processed
            if pd.notna(df.at[index, column_name]) and str(df.at[index, column_name]).strip():
                continue
            
            instruction = str(row["Instruction"]) if pd.notna(row["Instruction"]) else ""
            user_input = str(row["Input"]) if pd.notna(row["Input"]) else ""
            transactions = str(row["Transactions"]) if "Transactions" in df.columns and pd.notna(row["Transactions"]) else None
            
            if not instruction and not user_input and not transactions:
                continue
            
            # Pass transactions as an extra argument
            tasks.append((model_name, instruction, user_input, index, column_name, transactions))
    
    print(f"Total tasks to process: {len(tasks)}")
    
    if not tasks:
        print("No tasks to process!")
        return
    
    # Process tasks with ThreadPoolExecutor
    start_time = time.time()
    completed_tasks = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks
        future_to_task = {executor.submit(process_single_request, task): task for task in tasks}
        
        # Process completed tasks
        for future in as_completed(future_to_task):
            try:
                row_index, column_name, response = future.result()
                
                # Thread-safe DataFrame update
                with df_lock:
                    df.at[row_index, column_name] = response
                
                completed_tasks += 1
                
                # Save progress periodically
                if completed_tasks % 20 == 0:  # Save every 20 completions
                    with df_lock:
                        output_file = f"inference/t_{TEMPERATURE}_gemini_output_{os.path.basename(csv_file)}"
                        os.makedirs("inference", exist_ok=True)
                        df.to_csv(output_file, index=False)
                    
                    elapsed = time.time() - start_time
                    rate = completed_tasks / elapsed
                    remaining = len(tasks) - completed_tasks
                    eta = remaining / rate if rate > 0 else 0
                    
                    print(f"Progress: {completed_tasks}/{len(tasks)} ({completed_tasks/len(tasks)*100:.1f}%) "
                          f"Rate: {rate:.1f} req/sec ETA: {eta/60:.1f}min")
                
            except Exception as e:
                print(f"Task failed: {e}")
    
    # Save final results
    output_file = f"inference/gemini_output_{os.path.basename(csv_file)}"
    os.makedirs("inference", exist_ok=True)
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"All tasks completed in {elapsed/60:.1f} minutes!")
    print(f"Average rate: {len(tasks)/elapsed:.1f} requests per second")
    print(f"Final output saved to: {output_file}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

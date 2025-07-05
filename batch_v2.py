import pandas as pd
import sys
import os
import time
import torch
import psutil
import re
import json
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig

def print_gpu_memory():
    if torch.cuda.is_available():
        for i in range(torch.cuda.device_count()):
            allocated = torch.cuda.memory_allocated(i) / 1024**3
            reserved = torch.cuda.memory_reserved(i) / 1024**3
            print(f"  [GPU {i}] {allocated:.2f}GB allocated, {reserved:.2f}GB reserved", flush=True)
    else:
        print("  [GPU] CUDA not available", flush=True)

def print_cpu_memory():
    mem = psutil.virtual_memory()
    print(f"  [CPU] {mem.used/1024**3:.2f}GB used, {mem.percent:.1f}% of total", flush=True)

def create_slurm_symlinks(output_dir, job_id):
    slurm_log_dir = f"/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_{job_id}"
    if os.path.isdir(slurm_log_dir):
        for fname in os.listdir(slurm_log_dir):
            src = os.path.join(slurm_log_dir, fname)
            dst = os.path.join(output_dir, fname)
            try:
                if os.path.islink(dst) or os.path.exists(dst):
                    os.remove(dst)
                os.symlink(src, dst)
                print(f"[INFO] Created symlink: {dst} -> {src}", flush=True)
            except Exception as e:
                print(f"[WARN] Could not create symlink for {src}: {e}", flush=True)
    else:
        print(f"[WARN] SLURM log directory does not exist: {slurm_log_dir}", flush=True)

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

def create_rematch_prompt(original_json, transactions_csv):
    """Create a prompt for re-matching transactions with tolerance for fees but strict date matching"""
    prompt = f"""I previously analyzed fraud alert transactions and found some that could not be located in the transaction records. Please re-examine these with more flexibility for amounts only, as transaction amounts might be slightly different due to processing fees, currency conversion, or rounding.

ORIGINAL ANALYSIS RESULT:
{json.dumps(original_json, indent=2)}

TRANSACTION RECORDS CSV:
{transactions_csv}

INSTRUCTIONS:
1. For each alerted transaction where "can_be_located" is false, re-examine the transaction records
2. Allow for small differences in amounts (up to 5% tolerance) that could be due to:
   - Transaction fees
   - Currency conversion fees  
   - Rounding differences
   - Processing charges
3. **IMPORTANT: Date must match exactly - do not allow any tolerance for dates**
4. Consider partial matches in descriptions, merchant names, or account numbers
5. If you find a match with amount tolerance but exact date match, update the JSON:
   - Set "can_be_located" to true
   - Update "transaction_references" with the matched Transaction ID(s)
   - Replace the "amount" field with the actual amount from the CSV transaction record
   - Add "original_amount" field to store the original amount from the fraud alert source
   - Overwrite existing transaction fields using transaction CSV values when CSV values exist (originator becomes "from", beneficiary becomes "to")
   - Add a "rematch_note" field explaining what amount tolerance was applied

**Channel Rules (Payment Method):**
The channel field can only be: "FPS", "cash", "ATM", "cash deposits via ATM", "cheque", "Remittance", "Branch", or null
In case the channel is "cheque", it might or might not provide hint that the global field fraud_type is "Cheque Fraud"
If there is no hint, assume the channel is null

Based on Transaction Source in CSV:
- "CUTF" → need to look at Transaction Code Description and source file
- "CMTF" → "Branch"
- "CWTF" → "Remittance" if Transaction Code Description is INWARD TELEGRAPHIC TRANSFER (R22), otherwise "FPS"
- "DWTF" → "FPS"
- "FPWICT" → "FPS"

Based on Transaction Code Description in CSV:
- "ATM TRANSFER UNRELATED DEPOSIT" → "ATM"
- "ATM TRANSFER UNRELATED WITHDRAWAL" → "ATM"
- "CASH DEP VIA CDM/BCDM - AC INPUT (TOUCH SCREEN)" → "cash"
- "ATM/CDM CASH CREDIT USINGACCOUNT INPUT" → "cash deposits via ATM" if source file mentions ATM, otherwise "cash"
- "CIF CASH DEPOSIT" → "cash"

Please return the updated JSON with any newly matched transactions. If no additional matches are found, return the original JSON unchanged.

Output the result in JSON format enclosed in `````` tags."""
    
    return prompt

def needs_rematching(json_response):
    """Check if any transactions have can_be_located = false"""
    if 'alerted_transactions' not in json_response:
        return False
    
    for alert in json_response['alerted_transactions']:
        if alert.get('can_be_located') == False:
            return True
    return False

def process_chunk(chunk, model_name, gpu_index, input_csv, timestamp, job_id):
    folder_name = model_name.split('/')[-1] if model_name.split('/')[-1].startswith("job_") else f"Base_{timestamp}_{model_name.split('/')[-1]}"
    output_csv_path = (
        f"model_responses/{folder_name}/{input_csv.split('/')[-1].split('.')[0]}_model_responses_chunk_{gpu_index}_job_{job_id}.csv"
    )
    output_dir = os.path.dirname(output_csv_path)
    os.makedirs(output_dir, exist_ok=True)

    create_slurm_symlinks(output_dir, job_id)

    print(f"[INFO] Loading model: {model_name}", flush=True)
    model_load_start = time.time()
    model = AutoModelForCausalLM.from_pretrained(
        model_name, torch_dtype="auto", device_map=f"cuda:0"
    )
    model_load_time = time.time() - model_load_start
    print(f"[INFO] Model loaded in {model_load_time:.2f} seconds.", flush=True)
    print_gpu_memory()
    print_cpu_memory()

    print(f"[INFO] Loading tokenizer from: {model_name}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    print("[INFO] Tokenizer loaded successfully.", flush=True)

    total_rows = len(chunk)
    print(f"[INFO] Starting inference for {total_rows} rows.", flush=True)

    start_total = time.time()
    total_input_tokens = 0
    total_output_tokens = 0
    row_times = []
    rematch_count = 0

    for index, row in chunk.iterrows():
        print(f"\n[INFO] Processing row {index + 1}/{total_rows}", flush=True)
        print(f"[INFO] Instruction (truncated): {row['Instruction'][:80]}...", flush=True)

        user_prompt = f'Now, process the following documents.\n<FRAUD_ALERT_SOURCE>\n{row["Input"]}\n</FRAUD_ALERT_SOURCE>\n<TRANSACTION_RECORDS_CSV>\n{row["Transactions"]}\n</TRANSACTION_RECORDS_CSV>'
        print(f"[INFO] User Prompt (truncated): {user_prompt[:120]}...", flush=True)

        start_inference = time.time()

        messages = [
            {"role": "system", "content": row["Instruction"]},
            {"role": "user", "content": user_prompt},
        ]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        model_inputs = tokenizer([text], return_tensors="pt").to("cuda:0")
        input_tokens = model_inputs.input_ids.shape[-1]

        # Initial inference
        generated_ids = model.generate(
            **model_inputs, max_new_tokens=8192, do_sample=False
        )
        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        output_tokens = len(tokenizer.encode(response))

        total_input_tokens += input_tokens
        total_output_tokens += output_tokens

        # Check if re-matching is needed
        try:
            json_response = extract_json_content(response)
            
            if needs_rematching(json_response):
                print(f"[INFO] Re-matching needed for row {index + 1} - found transactions with can_be_located=false", flush=True)
                rematch_count += 1
                
                # Create re-match prompt
                rematch_prompt = create_rematch_prompt(json_response, row["Transactions"])
                
                # Run re-matching inference
                rematch_messages = [
                    {"role": "system", "content": "You are an expert at analyzing financial transactions and matching records with tolerance for small differences due to fees and processing."},
                    {"role": "user", "content": rematch_prompt}
                ]
                
                rematch_text = tokenizer.apply_chat_template(rematch_messages, tokenize=False, add_generation_prompt=True)
                rematch_inputs = tokenizer([rematch_text], return_tensors="pt").to("cuda:0")
                rematch_input_tokens = rematch_inputs.input_ids.shape[-1]
                
                rematch_generated = model.generate(
                    **rematch_inputs, max_new_tokens=8192, do_sample=False
                )
                rematch_generated = [
                    output_ids[len(input_ids):]
                    for input_ids, output_ids in zip(rematch_inputs.input_ids, rematch_generated)
                ]
                
                rematch_response = tokenizer.batch_decode(rematch_generated, skip_special_tokens=True)[0]
                rematch_output_tokens = len(tokenizer.encode(rematch_response))
                
                total_input_tokens += rematch_input_tokens
                total_output_tokens += rematch_output_tokens
                
                try:
                    updated_json = extract_json_content(rematch_response)
                    final_response = json.dumps(updated_json, indent=2)
                    print(f"[INFO] Successfully re-matched transactions for row {index + 1}", flush=True)
                except Exception as e:
                    print(f"[WARN] Re-matching JSON extraction failed for row {index + 1}: {e}", flush=True)
                    final_response = response  # Fall back to original response
            else:
                final_response = response
                print(f"[INFO] No re-matching needed for row {index + 1}", flush=True)
                
        except Exception as e:
            print(f"[WARN] JSON extraction failed for row {index + 1}: {e}", flush=True)
            final_response = response

        chunk.at[index, f"{model_name.split('/')[-1]}"] = final_response
        chunk.at[index, "input_tokens"] = input_tokens
        chunk.at[index, "output_tokens"] = output_tokens

        chunk.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
        end_inference = time.time()
        duration = end_inference - start_inference
        row_times.append(duration)
        print(f"[INFO] Row {index + 1} processed in {duration:.2f} seconds.", flush=True)
        print(f"[INFO] Input tokens: {input_tokens}, Output tokens: {output_tokens}", flush=True)
        print(f"[INFO] Output CSV saved to: {output_csv_path}", flush=True)
        print_gpu_memory()
        print_cpu_memory()

    end_total = time.time()
    print(f"\n[INFO] All rows processed in {end_total - start_total:.2f} seconds.", flush=True)
    print(f"[INFO] Final output CSV path: {output_csv_path}", flush=True)

    # Print summary metrics
    print("\n========== INFERENCE SUMMARY ==========", flush=True)
    print(f"Total rows processed: {total_rows}", flush=True)
    print(f"Rows requiring re-matching: {rematch_count}", flush=True)
    print(f"Total input tokens: {total_input_tokens}", flush=True)
    print(f"Total output tokens: {total_output_tokens}", flush=True)
    print(f"Average time per row: {sum(row_times)/len(row_times):.2f} seconds", flush=True)
    print(f"Total elapsed time: {end_total - start_total:.2f} seconds", flush=True)
    print_gpu_memory()
    print_cpu_memory()
    print("=======================================", flush=True)

def main():
    input_csv = sys.argv[1]
    model_name = sys.argv[2]
    n = int(sys.argv[3])
    gpu_index = int(sys.argv[4])
    timestamp = int(sys.argv[5])
    job_id = int(sys.argv[6])

    print(f"[INFO] Inference script started at {time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print(f"[INFO] Input CSV path: {input_csv}", flush=True)
    print(f"[INFO] Model: {model_name}", flush=True)
    print(f"[INFO] Num splits: {n}, This GPU index: {gpu_index}", flush=True)
    print(f"[INFO] Timestamp: {timestamp}", flush=True)

    df = pd.read_csv(input_csv)
    chunk_size = len(df) // n + (len(df) % n > 0)
    chunks = [df.iloc[i: i + chunk_size] for i in range(0, len(df), chunk_size)]
    process_chunk(chunks[gpu_index], model_name, gpu_index, input_csv, timestamp, job_id)

if __name__ == "__main__":
    main()

import pandas as pd
import sys
import torch
import time
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig

def get_model_layer_count(model_name):
    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True)
    return config.num_hidden_layers

def create_device_map(model_name, num_gpus):
    num_layers = get_model_layer_count(model_name)
    layers_per_gpu = num_layers // num_gpus
    remainder = num_layers % num_gpus

    device_map = {"model.embed_tokens": 0}
    current_layer = 0
    for gpu in range(num_gpus):
        count = layers_per_gpu + (1 if gpu < remainder else 0)
        for i in range(current_layer, current_layer + count):
            device_map[f"model.layers.{i}"] = gpu
        current_layer += count

    device_map["model.norm"] = num_gpus - 1
    device_map["lm_head"] = num_gpus - 1
    return device_map

def main():
    base_model_name = sys.argv[1]
    input_csv_path = "dataset/Dataset_Source_v4.1.csv"
    output_csv_path = f"dataset/Dataset_Source_v4.1_generated_{base_model_name.split('/')[-1]}.csv"

    print(f"[INFO] Input CSV path: {input_csv_path}")
    df = pd.read_csv(input_csv_path)

    num_gpus = torch.cuda.device_count()
    device_map = create_device_map(base_model_name, num_gpus)
    print(f"[INFO] Number of GPUs detected: {num_gpus}")
    print(f"[INFO] Device map: {device_map}")

    print(f"[INFO] Loading base model from: {base_model_name}")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
        device_map=device_map,
        low_cpu_mem_usage=True,
        max_memory={i: "50GB" for i in range(num_gpus)}
    )
    print("[INFO] Base model loaded successfully.")

    print(f"[INFO] Loading tokenizer from: {base_model_name}")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name)
    print("[INFO] Tokenizer loaded successfully.")

    model = base_model
    total_rows = len(df)
    print(f"[INFO] Starting processing of {total_rows} rows.")

    start_total = time.time()

    for index, row in df.iterrows():
        print(f"\n[INFO] Processing row {index + 1}/{total_rows}")
        print(f"[INFO] Instruction preview: {row['Instruction'][:50]}...")

        start_inference = time.time()

        messages = [
            {"role": "system", "content": row["Instruction"]},
            {"role": "user", "content": f'Now, process the following documents.\n<FRAUD_ALERT_SOURCE>\n{row["Input"]}\n</FRAUD_ALERT_SOURCE>\n<TRANSACTION_RECORDS_CSV>\n{row["Transactions"]}\n</TRANSACTION_RECORDS_CSV>'}
        ]

        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = tokenizer([text], return_tensors="pt").to("cuda:0")

        generated_ids = model.generate(**model_inputs, max_new_tokens=4096)
        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        df.at[index, base_model_name.split('/')[-1]] = response

        df.to_csv(output_csv_path, index=False)
        end_inference = time.time()
        print(f"[INFO] Row {index + 1} processed in {end_inference - start_inference:.2f} seconds.")
        print(f"[INFO] Output CSV saved to: {output_csv_path}")

    end_total = time.time()
    print(f"\n[INFO] All rows processed successfully in {end_total - start_total:.2f} seconds.")
    print(f"[INFO] Final output CSV path: {output_csv_path}")

if __name__ == "__main__":
    main()

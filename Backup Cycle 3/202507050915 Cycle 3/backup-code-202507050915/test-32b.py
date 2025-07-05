import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
from peft import PeftModel, PeftConfig
import argparse

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
    # Parse arguments
    parser = argparse.ArgumentParser(description="Test model with model parallelism")
    parser.add_argument("--model_dir", type=str, required=True,
                       help="Directory containing the model to test")
    args = parser.parse_args()
    
    model_name = args.model_dir

    # Load CSV data
    df = pd.read_csv("dataset/Data_Source_v4.csv")

    # Initialize model and tokenizer
    if model_name.startswith("/cm/shared/llm_models/"):
        model = AutoModelForCausalLM.from_pretrained(
            model_name, torch_dtype="auto", device_map="cuda:0"
        )
        tokenizer = AutoTokenizer.from_pretrained(model_name)

    else:
        base_model_name = "/cm/shared/llm_models/Qwen/Qwen2.5-32B-Instruct"
        num_gpus = torch.cuda.device_count()
        device_map = create_device_map(base_model_name, num_gpus)

        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=torch.bfloat16,
            trust_remote_code=True,
            device_map=device_map,
            low_cpu_mem_usage=True,
            max_memory={i: "50GB" for i in range(num_gpus)}
        )
        tokenizer = AutoTokenizer.from_pretrained(base_model_name)
        model = PeftModel.from_pretrained(base_model, model_name)

    # Process each row
    for index, row in df.iterrows():
        messages = [
            {"role": "system", "content": row["Instruction"]},
            {"role": "user", "content": f'Now, process the following documents.\n<FRAUD_ALERT_SOURCE>\n{row["Input"]}\n</FRAUD_ALERT_SOURCE>\n<TRANSACTION_RECORDS_CSV>\n{row["Transactions"]}\n</TRANSACTION_RECORDS_CSV>'}
        ]

        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = tokenizer([text], return_tensors="pt").to("cuda:0")

        generated_ids = model.generate(**model_inputs, max_new_tokens=2048)
        generated_ids = [
            output_ids[len(input_ids):]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        df.at[index, "Qwen 32B Instruct Base"] = response

        df.to_csv("model_responses-32b.csv", index=False)
        print(f"Processed row {index + 1}/{len(df)}")

if __name__ == "__main__":
    main()

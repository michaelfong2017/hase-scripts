#!/bin/bash

# Parameters
input_csv="/home/projects/fraudagent/hase-michael/V4/dataset/full60_test_set_v6.csv"
# input_csv="/home/projects/fraudagent/hase-michael/V4/dataset/exam18_test_set_v1.csv"  # Update this path
model_name="/home/projects/fraudagent/hase-michael/V4/output_models/job_67902_20250704_1444_Qwen2.5-32B-Instruct_LoRA"
# model_name="/cm/shared/llm_models/Qwen/Qwen2.5-14B-Instruct"
# model_name="/cm/shared/llm_models/meta-llama/Llama3.1-8B-Instruct"
# model_name="/cm/shared/llm_models/meta-llama/Llama-3.2-1B-Instruct"

num_gpus=1

# Generate a timestamp (format: YYYYMMDD_HHMMSS)
timestamp=$(date +"%Y%m%d_%H%M%S")

# Submit jobs for each GPU index, passing the timestamp
for ((i=0; i<num_gpus; i++)); do
    sbatch b-split.sh "$input_csv" "$model_name" "$num_gpus" "$i" "$timestamp"
done

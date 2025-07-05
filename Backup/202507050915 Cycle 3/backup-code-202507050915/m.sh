#!/bin/bash
#SBATCH --job-name=merge_job
#SBATCH --output=/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_%j/%x_%j_%a.out  # Unique output file
#SBATCH --error=/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_%j/%x_%j_%a.err   # Unique error file
#SBATCH --ntasks=1
#SBATCH --time=4-00:00:00
#SBATCH --partition=aisandbox
#SBATCH --gpus=1
#SBATCH --mem=257G
#SBATCH --account=fraudagent

base_model="/cm/shared/llm_models/Qwen/Qwen2.5-32B-Instruct"
# base_model="/cm/shared/llm_models/meta-llama/Llama3.1-8B-Instruct"
# base_model="/cm/shared/llm_models/meta-llama/Llama-3.2-1B-Instruct"
lora_adapter_basename="job_68004_20250705_0854_Qwen2.5-32B-Instruct_LoRA"
output_path="/home/projects/fraudagent/all-downloads/"$lora_adapter_basename"_job_$SLURM_JOB_ID"

# Print some info
echo "Job started on $(hostname) at $(date)"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"
echo "Base model: $base_model"
echo "LoRA adapter: $lora_adapter_basename"
echo "Output path: $output_path"

# Start enroot container with mounts and enter working directory
enroot start --mount /cm/shared --mount /home -w pytorch <<EOC
set -e

cd /home/projects/fraudagent/hase-michael/V4

if python merge_lora_multigpu.py --base_model "$base_model" --lora_adapter "/home/projects/fraudagent/hase-michael/V4/output_models/$lora_adapter_basename" --output_path "$output_path"; then
    echo "✅ Merge model completed at \$(date)"

    echo "🎉 All tasks completed successfully!"
    exit 0
else
    echo "❌ Merge failed at \$(date)"
    exit 1
fi

EOC

# Capture the exit code from the container
EXIT_CODE=$?

# Final status report
echo "=================================="
echo "Job finished at $(date)"
echo "Exit code: $EXIT_CODE"

if [ $EXIT_CODE -eq 0 ]; then
    echo "🎉 Job completed successfully!"
else
    echo "❌ Job failed with exit code $EXIT_CODE"
fi

# Exit with the same code as the container
exit $EXIT_CODE

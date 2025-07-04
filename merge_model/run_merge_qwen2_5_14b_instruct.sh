#!/bin/bash
#SBATCH --job-name=merge_lora_hase
#SBATCH --partition=aisandbox
#SBATCH --account=fraudagent
#SBATCH --gpus=1
#SBATCH --mem=256G
#SBATCH --output=sbatchlog/merge_model/qwen2.5_14b_instruct/job-%j/output.txt
#SBATCH --error=sbatchlog/merge_model/qwen2.5_14b_instruct/job-%j/error.txt
#SBATCH --time=48:00:00
#SBATCH --ntasks=1

# Print some info
echo "Job started on $(hostname) at $(date)"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"

# Start enroot container with mounts and enter working directory
enroot start --mount /cm/shared --mount /home -w hase-cyril-torch-25 <<'EOC'
set -e

cd /home/projects/fraudagent/hase-cyril

if python merge_lora_multigpu.py --base_model "/cm/shared/llm_models/Qwen/Qwen2.5-14B-Instruct" --lora_adapter "/home/projects/fraudagent/hase-michael/V4/output_models/job_65282_20250616_1709_Qwen2.5-14B-Instruct_LoRA" --output_path "./merged_models/Qwen2.5-14B-Instruct"; then
    echo "✅ Merge model completed at $(date)"

    echo "🎉 All tasks completed successfully!"
    exit 0
else
    echo "❌ Merge failed at $(date)"
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

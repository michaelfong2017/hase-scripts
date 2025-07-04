#!/bin/bash
#SBATCH --job-name=finetune
#SBATCH --partition=aisandbox
#SBATCH --account=fraudagent
#SBATCH --gpus=4
#SBATCH --mem=1024G
#SBATCH --output=sbatchlog/finetune/qwen25-32b-instruct/job-%j/output.txt
#SBATCH --error=sbatchlog/finetune/qwen25-32b-instruct/job-%j/error.txt
#SBATCH --time=48:00:00
#SBATCH --ntasks=1

# Print some info
echo "Job started on $(hostname) at $(date)"
echo "SLURM_JOB_ID: $SLURM_JOB_ID"

# Initialize exit code
EXIT_CODE=0

# Start enroot container with mounts and enter working directory
enroot start --mount /cm/shared --mount /home -w hase-cyril-torch-25 bash <<'EOC'
set -e

cd /home/projects/fraudagent/hase-cyril

echo "Starting fine-tuning at $(date)"

# Run Accelerate fine-tuning with error capture
if python finetune.py --config config_qwen2_5_32b_instruct.json; then
    echo "✅ Fine-tuning completed successfully at $(date)"
    
    find . -name "*.tmp" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    echo "🎉 All tasks completed successfully!"
    exit 0
else
    echo "❌ Fine-tuning failed at $(date)"
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

echo "Check output files:"
echo "  - sbatchlog/finetune/qwen25-32b-instruct/job-${SLURM_JOB_ID}/output.txt"
echo "  - sbatchlog/finetune/qwen25-32b-instruct/job-${SLURM_JOB_ID}/error.txt"

# Exit with the same code as the container
exit $EXIT_CODE

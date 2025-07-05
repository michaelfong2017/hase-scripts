#!/bin/bash
#SBATCH --job-name=finetune_8b_job
#SBATCH --output=/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_%j/%x_%j_%a.out  # Unique output file
#SBATCH --error=/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_%j/%x_%j_%a.err   # Unique error file
#SBATCH --ntasks=1
#SBATCH --time=4-00:00:00
#SBATCH --partition=aisandbox
#SBATCH --gpus=2
#SBATCH --mem=514G
#SBATCH --account=fraudagent

export CONTDIR=/cm/shared/containers/ngc/
export PIP=/cm/shared/python_modules/

# Get current datetime and job ID
current_datetime=$(date +"%Y%m%d_%H%M")
job_id=$SLURM_JOB_ID

# Create a directory for logs and completed jobs tracking
LOG_DIR="/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_${job_id}"
COMPLETED_DIR="/home/projects/fraudagent/hase-michael/V4/completed_jobs/job_${job_id}"
mkdir -p $LOG_DIR $COMPLETED_DIR

# Submit the job with the current hyperparameter combination
srun --pty bash -c "enroot start --mount /cm/shared --mount /home -w pytorch bash -c \
'cd /home/projects/fraudagent/hase-michael/V4; \
python finetune.py --job_id $SLURM_JOB_ID --config config-llama-8b-instruct-lora.json'"

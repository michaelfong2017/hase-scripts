#!/bin/bash
#SBATCH --job-name=gen_job
#SBATCH --output=/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_%j/%x_%j_%a.out  # Unique output file
#SBATCH --error=/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_%j/%x_%j_%a.err   # Unique error file
#SBATCH --ntasks=1
#SBATCH --time=4-00:00:00
#SBATCH --partition=aisandbox
#SBATCH --gpus=1
#SBATCH --mem=257G
#SBATCH --account=fraudagent

base_model_name="/cm/shared/llm_models/Qwen/Qwen2.5-14B-Instruct"

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
# srun --pty bash -c "enroot create --name pytorch $CONTDIR/pytorch.24.08-py3.sqsh; \
# enroot start --mount /cm/shared --mount /home -w pytorch bash -c \
# 'pip install --no-index --find-links $PIP transformers accelerate deepspeed bitsandbytes; \
# cd /home/projects/fraudagent/hase-michael/V4; \
# python gen.py $base_model_name'"

srun --pty bash -c "enroot start --mount /cm/shared --mount /home -w pytorch bash -c \
'cd /home/projects/fraudagent/hase-michael/V4; \
python gen.py $base_model_name'"

#!/bin/bash
#SBATCH --job-name=batch_test_job
#SBATCH --output=/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_%j/%x_%j.out  # Unique output file
#SBATCH --error=/home/projects/fraudagent/hase-michael/V4/slurm_logs/job_%j/%x_%j.err   # Unique error file
#SBATCH --ntasks=1
#SBATCH --time=4-00:00:00
#SBATCH --partition=aisandbox
#SBATCH --gpus=1  # Request 1 GPU
#SBATCH --mem=257G
#SBATCH --account=fraudagent

# Get the input CSV and GPU index from arguments
input_csv=$1
model_name=$2
num_gpus=$3
gpu_index=$4
timestamp=$5

export CONTDIR=/cm/shared/containers/ngc/
export PIP=/cm/shared/python_modules/

# Create the job environment
enroot start --mount /cm/shared --mount /home -w pytorch bash -c "
cd /home/projects/fraudagent/hase-michael/V4; \
python batch.py $input_csv $model_name $num_gpus $gpu_index $timestamp $SLURM_JOB_ID"

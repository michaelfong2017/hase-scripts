#!/bin/bash

# Base directories
export BASE_MODEL_DIR="/cm/shared/llm_models/meta-llama/Llama3.1-8B-Instruct"
export PROJECT_ROOT="/home/projects/fraudagent/hase-michael/V4"

# Dataset paths
export DATASET_DIR="${PROJECT_ROOT}/dataset"
export INPUT_CSV="${DATASET_DIR}/Combined.csv"

# Output paths
export OUTPUT_CSV="${PROJECT_ROOT}/model_responses-8b.csv"
export SLURM_LOG_ROOT="${PROJECT_ROOT}/slurm_logs"
export COMPLETED_JOBS_DIR="${PROJECT_ROOT}/completed_jobs"

# Container and Python module paths
export CONTDIR="/cm/shared/containers/ngc/"
export PIP="/cm/shared/python_modules/"

export OUTPUT_COL_NAME="Llama 8B Instruct Base"

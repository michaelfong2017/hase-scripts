#!/bin/bash

# Check if prefix argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <prefix>"
    exit 1
fi

prefix="$1"

# Recursively process all subdirectories
find . -type d | while read -r dir; do
    cd "$dir" || continue

    # Match files with the pattern ${prefix}_test_set_model_responses_chunk_*.csv
    chunk_files=(${prefix}_test_set_model_responses_chunk_*.csv)
    # Skip if no such files exist in this directory
    if [ ! -e "${chunk_files[0]}" ]; then
        cd - > /dev/null
        continue
    fi

    # Extract suffix from the first chunk file
    # Pattern: prefix_test_set_model_responses_chunk_{gpu_index}_job_{job_id}.csv
    first_file="${chunk_files[0]}"
    # Extract everything after "chunk_" and before ".csv"
    suffix=$(echo "$first_file" | sed "s/.*chunk_\(.*\)\.csv/\1/")
    
    output_file="${prefix}_test_set_model_responses_${suffix}.csv"
    [ -f "$output_file" ] && rm "$output_file"

    for file in ${prefix}_test_set_model_responses_chunk_*.csv; do
        if [ -f "$file" ]; then
            if [ ! -s "$output_file" ]; then
                cat "$file" >> "$output_file"
            else
                tail -n +2 "$file" >> "$output_file"
            fi
        fi
    done

    echo "Merged CSV created in $dir/$output_file"
    cd - > /dev/null
done

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

    # Match files with the pattern ${prefix}_model_responses_chunk_*.csv
    chunk_files=(${prefix}_model_responses_chunk_*.csv)
    # Skip if no such files exist in this directory
    if [ ! -e "${chunk_files[0]}" ]; then
        cd - > /dev/null
        continue
    fi

    # Get unique suffixes
    suffixes=$(for file in ${prefix}_model_responses_chunk_*.csv; do
        if [ -f "$file" ]; then
            echo "$file" | sed "s/${prefix}_model_responses_chunk_[0-9]*\(.*\)\.csv/\1/"
        fi
    done | sort -u)

    # Process each suffix group
    echo "$suffixes" | while IFS= read -r suffix; do
        # Create output filename
        if [ -z "$suffix" ]; then
            output_file="${prefix}_model_responses.csv"
            pattern="${prefix}_model_responses_chunk_[0-9]*.csv"
        else
            output_file="${prefix}_model_responses${suffix}.csv"
            pattern="${prefix}_model_responses_chunk_[0-9]*${suffix}.csv"
        fi
        
        [ -f "$output_file" ] && rm "$output_file"
        
        # Find and sort matching files
        matching_files=$(ls ${pattern} 2>/dev/null | sort -V)
        
        for file in $matching_files; do
            if [ -f "$file" ]; then
                if [ ! -s "$output_file" ]; then
                    cat "$file" >> "$output_file"
                else
                    tail -n +2 "$file" >> "$output_file"
                fi
            fi
        done

        if [ -f "$output_file" ]; then
            echo "Merged CSV created in $dir/$output_file"
        fi
    done

    cd - > /dev/null
done

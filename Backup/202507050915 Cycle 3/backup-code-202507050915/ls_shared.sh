#!/bin/bash

TARGET_DIR="/cm/shared/"
OUTPUT_FILE="cm_shared_tree.txt"
DEPTH=4

# Function to create indented listing
create_formatted_tree() {
    local dir="$1"
    local max_depth="$2"
    local output="$3"
    
    echo "Directory Tree for $dir" > "$output"
    echo "Max Depth: $max_depth" >> "$output"
    echo "Generated: $(date)" >> "$output"
    echo "========================================" >> "$output"
    echo "" >> "$output"
    
    if command -v tree &> /dev/null; then
        tree -L "$max_depth" -a -I ".git|node_modules" "$dir" >> "$output"
    else
        echo "Using find command (tree not available):" >> "$output"
        find "$dir" -maxdepth "$max_depth" -type d | sort | sed 's|[^/]*/|  |g' >> "$output"
        echo "" >> "$output"
        echo "Files:" >> "$output"
        find "$dir" -maxdepth "$max_depth" -type f | sort >> "$output"
    fi
}

# Check if directory exists
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory $TARGET_DIR does not exist."
    exit 1
fi

# Create the tree
create_formatted_tree "$TARGET_DIR" "$DEPTH" "$OUTPUT_FILE"

echo "Directory tree saved to $OUTPUT_FILE"
echo "File size: $(du -h "$OUTPUT_FILE" | cut -f1)"

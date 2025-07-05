#!/bin/bash

# Define the tar file name
tar_file="backup-code.tar.gz"

# Create a tar.gz file containing all .sh, .py, and .json files
tar -czf "$tar_file" *.sh *.py *.json *.txt

# Check if the tar command was successful
if [ $? -eq 0 ]; then
    echo "Successfully created $tar_file"
else
    echo "Failed to create tar file"
fi

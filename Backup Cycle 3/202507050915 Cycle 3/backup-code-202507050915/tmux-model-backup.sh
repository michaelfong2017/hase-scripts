#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <numeric_id>"
    exit 1
fi

id="$1"
prefix="job_${id}"
backup_datetime=$(date +"%Y%m%d_%H%M")
backup_dir="backupV4/model_${id}"
archive_file="${backup_dir}/model_${id}_${backup_datetime}.tar.gz"
info_archive_file="${backup_dir}/model_info_${id}_${backup_datetime}.tar.gz"
session="backup_${id}"

mkdir -p "$backup_dir"

tmux new-session -d -s "$session" "
echo '[INFO] Starting backup for job prefix: $prefix'
echo '[INFO] Backup datetime: $backup_datetime'
mkdir -p '$backup_dir'

dirs=\$(find . -type d -name '${prefix}*')
if [ -z \"\$dirs\" ]; then
    echo '[WARN] No directories found matching prefix \"${prefix}\"'
    exit 0
fi

tmpfile_all=\$(mktemp)
tmpfile_info=\$(mktemp)
total_files=0
safetensors_count=0

for dir in \$dirs; do
    echo '[INFO] === Found directory: \$dir ==='
    all_files=\$(find \"\$dir\" -type f)
    info_files=\$(find \"\$dir\" -type f ! -name '*.safetensors')

    # Add non-safetensors files to info tar list
    if [ -n \"\$info_files\" ]; then
        while IFS= read -r file; do
            echo \"[INFO] (INFO TAR) Adding file: \$file\"
            echo \"\$file\" >> \"\$tmpfile_info\"
        done <<< \"\$info_files\"
    fi

    # Add all files to full tar list
    if [ -n \"\$all_files\" ]; then
        while IFS= read -r file; do
            size=\$(stat -c %s \"\$file\" 2>/dev/null)
            if [ -z \"\$size\" ]; then
                echo '[WARN]   Could not determine size for: \$file'
                continue
            fi
            hr_size=\$(numfmt --to=iec --suffix=B \"\$size\" 2>/dev/null)
            echo \"[INFO] (FULL TAR) Adding file: \$file (\$hr_size)\"
            if [[ \"\$file\" == *.safetensors ]]; then
                echo '[NOTICE]   -> Detected .safetensors file (large, may take a long time to archive)'
                ((safetensors_count++))
            fi
            echo \"\$file\" >> \"\$tmpfile_all\"
            ((total_files++))
        done <<< \"\$all_files\"
    fi
    echo '-------------------------'
done

# Create info tar (without .safetensors)
if [ -s \"\$tmpfile_info\" ]; then
    echo '[INFO] Creating info tar.gz archive (excluding .safetensors) at $info_archive_file ...'
    tar -h -czvf \"$info_archive_file\" -T \"\$tmpfile_info\"
    echo '[INFO] Info archive created: $info_archive_file'
else
    echo '[WARN] No files found for info archive.'
fi

# Create full tar (including .safetensors)
if [ -s \"\$tmpfile_all\" ]; then
    echo '[INFO] Total files to archive: \$total_files'
    if [ \"\$safetensors_count\" -gt 0 ]; then
        echo '[INFO] .safetensors files detected: \$safetensors_count'
        echo '[INFO] Archiving may take several minutes for large model files.'
    fi
    echo '[INFO] Creating full tar.gz archive at $archive_file ...'
    tar -h -czvf \"$archive_file\" -T \"\$tmpfile_all\"
    echo '[INFO] Full archive created: $archive_file'
else
    echo '[WARN] No files found for full archive.'
fi

rm \"\$tmpfile_all\" \"\$tmpfile_info\"
echo '[INFO] Backup process completed.'
exit
"

echo "[INFO] tmux session '$session' started. Attach with: tmux attach -t $session"

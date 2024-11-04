#!/bin/bash

# exit on errors
set -e

script_dir="$(dirname "$0")"
fens2cdb="$script_dir/../fens2cdb.py"

default_concurrency=32
default_size=100000
concurrency=$default_concurrency
size=$default_size
reverse_flag=""

while [[ $# -gt 0 ]]; do
    case "$1" in
    -c | --concurrency)
        concurrency="$2"
        shift 2
        ;;
    -s | --size)
        size="$2"
        shift 2
        ;;
    -r | --reverse)
        reverse_flag="-r"
        shift
        ;;
    -h | --help)
        echo "Usage: $0 [OPTIONS] file.epd(.gz)"
        echo "Options:"
        echo "  -c, --concurrency CONCURRENCY   Set the concurrency level (default: $default_concurrency)"
        echo "  -s, --size SIZE                 Set the chunk size (default: $default_size)"
        echo "  -r, --reverse                   Process the chunks in reverse order"
        echo
        echo "The script can be used for massive data uploads to chessdb.cn. It splits"
        echo "file.epd(.gz) into chunks of SIZE, then feeds them sequentially to cdb"
        echo "with CONCURRENCY, guaranteeing an evaluation for each position in the"
        echo "file. Larger values of SIZE need more RAM but are faster, while smaller"
        echo "values overall take more time but are more robust. E.g.\ restarting an"
        echo "interrupted upload will continue from the last completed chunk."
        exit 0
        ;;
    *)
        break
        ;;
    esac
done

if [ $# -ne 1 ]; then
    echo "Usage: $0 [--help] [OPTIONS] file.epd(.gz)"
    exit 1
fi

gzfile="$1"
epdfile="$(basename "$gzfile" .gz)"

if [[ "$gzfile" != "$epdfile" ]]; then
    if [[ -f $gzfile ]]; then
        gunzip "$gzfile"
    else
        echo "Error: File '$gzfile' not found."
        exit 1
    fi
fi

if [[ ! -f $epdfile ]]; then
    echo "Error: File '$epdfile' not found."
    exit 1
fi

total_lines=$(wc -l <"$epdfile")
size=$((size < total_lines ? size : total_lines))
chunk_number=$((total_lines / size + 1))
num_digits=${#chunk_number}
namehash=$(echo -n "$epdfile" | md5sum | cut -d ' ' -f 1)

split -l "$size" -d -a "$num_digits" "$epdfile" "_tmp_jumbo_${namehash}_${size}_"

find ./ -type f -regex "./_tmp_jumbo_${namehash}_${size}_[0-9]*$" | sort $reverse_flag | while read -r chunk; do
    output_file="$chunk"_cdb.epd
    if [ -e "$output_file" ] && [ "$(wc -l <"$output_file")" -eq "$(wc -l <"$chunk")" ]; then
        echo "Chunk '$chunk' already processed completely. Skipping."
    else
        python "$fens2cdb" -s -c "$concurrency" -ee "$chunk" >"$output_file"
    fi
done

find ./ -type f -regex "./_tmp_jumbo_${namehash}_${size}_[0-9]*$" -delete

cdbfile="$(basename "$epdfile" .epd)"_cdb.epd
cat $(find ./ -type f -regex "./_tmp_jumbo_${namehash}_${size}_[0-9]*_cdb.epd" | sort) >"$cdbfile"

find ./ -type f -regex "./_tmp_jumbo_${namehash}_${size}_[0-9]*_cdb.epd" -delete

echo "Jumbo upload completed, with cdb evals stored in '$cdbfile'."

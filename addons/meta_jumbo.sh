#!/bin/bash

# exit on errors
set -e

script_dir="$(dirname "$0")"
jumbo="$script_dir/jumbo_fens2cdb.sh"
score_locally="$script_dir/score_fens_locally.py"

concurrency=""
size=""
reverse_flag=""

while [[ $# -gt 0 ]]; do
    case "$1" in
    -c | --concurrency)
        concurrency="--concurrency $2"
        shift 2
        ;;
    -s | --size)
        size="--size $2"
        shift 2
        ;;
    -r | --reverse)
        reverse_flag="-r"
        shift
        ;;
    -h | --help)
        echo "Usage: $0 [OPTIONS] file.epd(.gz)"
        echo "Options:"
        echo "  -c, --concurrency CONCURRENCY   Optional parameter passed to jumbo_fens2cdb.sh"
        echo "  -s, --size SIZE                 Optional parameter passed to jumbo_fens2cdb.sh"
        echo "  -r, --reverse                   Optional parameter passed to jumbo_fens2cdb.sh"
        echo
        echo "The script can be used to call jumbo_fens2cdb.sh --quick repeatedly, in"
        echo "order to achieve a higher throughput, and overall faster upload to cdb."
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
epdname="$(basename "$epdfile" .epd)"
meta_all="_"$epdname"_meta_all.epd"
meta_unknown="_"$epdname"_meta_unknown.epd"
meta_unknown_cdb="_"$epdname"_meta_unknown_cdb.epd"

if [[ ! -f $meta_all ]]; then
    echo "Creating master file $meta_all ..."
    if [[ "$gzfile" != "$epdfile" ]]; then
        if [[ -f $gzfile ]]; then
            gunzip -kc "$gzfile" >"$meta_all"
        else
            echo "Error: File '$gzfile' not found."
            exit 1
        fi
    else
        if [[ -f $epdfile ]]; then
            cp "$epdfile" "$meta_all"
        else
            echo "Error: File '$epdfile' not found."
            exit 1
        fi
    fi
fi

count_unknown=1
while [ $count_unknown -ne 0 ]; do
    if [[ ! -f $meta_unknown ]]; then
        grep -v "cdb eval:" "$meta_all" >"$meta_unknown" || true
        count_unknown=$(wc -l <"$meta_unknown")
        echo "Stored $count_unknown unknown positions in '$meta_unknown'."
        if [ $count_unknown -ne 0 ]; then
            echo "Parsing these with jumbo_fens2cdb.sh --quick to cdb ..."
        fi
    else
        count_unknown=$(wc -l <"$meta_unknown")
        echo "Found '$meta_unknown' with $count_unknown unknown positions."
        if [ $count_unknown -ne 0 ]; then
            echo "Attempting to restart aborted jumbo upload ..."
        fi
    fi

    if [ $count_unknown -ne 0 ]; then
        $jumbo $concurrency $size $reverse_flag --quick "$meta_unknown"
        if [[ ! -f $meta_unknown_cdb ]]; then
            echo "Fatal error: Cannot find '$meta_unknown_cdb'."
            exit 1
        fi

        count_scores=$(grep -c "cdb eval:" <"$meta_unknown_cdb" || true)
        if [ $count_scores -ne 0 ]; then
            tmpname="$(mktemp -q)"
            echo "Incorporating $count_scores scores from '$meta_unknown_cdb' into '$meta_all' ..."
            python "$score_locally" "$meta_all" "$meta_unknown_cdb" >"$tmpname"
            mv "$tmpname" "$meta_all"
        else
            echo "No new scores found in $meta_unknown_cdb. Retrying ..."
        fi
    else
        echo "Scored all the unknown positions in '$1'. Done."
    fi

    rm -f "$meta_unknown" "$meta_unknown_cdb"
done

cdbfile="$(basename "$epdfile" .epd)"_cdb.epd
if [[ -f $cdbfile ]]; then
    echo "Meta upload completed, but '$cdbfile' already exists. Kept cdb evals stored in '$meta_all'."
else
    mv "$meta_all" "$cdbfile"
    echo "Meta upload completed, with cdb evals stored in '$cdbfile'."
fi

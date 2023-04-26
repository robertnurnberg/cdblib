"""
   Script to bulk-evaluate FENs/EPDs with chessdb.cn.
"""
import argparse, sys, time, cdblib

parser = argparse.ArgumentParser(
    description='A simple script to request evals from chessdb.cn for a list of FENs/EPDs stored in a file. The script will add "; EVALSTRING;" to every line containing a FEN. Lines beginning with "#" are ignored, as well as text after the first ";" on each line.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("input", help="source filename with FENs/EPDs")
parser.add_argument("output", nargs="?", help="optional destination filename")
parser.add_argument(
    "--shortFormat",
    action="store_true",
    help='EVALSTRING is either just a number, or "#" for checkmate, or "".',
)
parser.add_argument(
    "--quiet",
    action="store_true",
    help="Suppress all unnecessary output to the screen.",
)
args = parser.parse_args()

if args.output:
    output = open(args.output, "w")
    display = sys.stdout
else:
    output = sys.stdout
    display = sys.stderr
if args.quiet:
    display = None

with open(args.input) as f:
    lines = [line for line in f]
if display:
    print(f"FENs loaded...", file=display)
    tic = time.time()

cdb = cdblib.cdbAPI()
scored, unknown = 0, 0
for line in lines:
    line = line.strip()
    if line:
        if line.startswith("#"):  # ignore comments
            print(line, file=output)
            continue
        fen, _, _ = line.partition(";")  # ignore all beyond first ";"
        r = cdb.queryscore(fen)
        score = cdblib.json2eval(r)
        if r.get("status") == "unknown" and score == "":
            unknown += 1
        if args.shortFormat:
            if score == "mated":
                score = "#"
            elif type(score) != int:
                score = ""
        elif score != "":
            if "ply" in r:
                score = f"{score}, ply: {r['ply']}"
            score = f"cdb eval: {score}"
        print(f"{line}{';' if line[-1] != ';' else ''} {score};", file=output)
        scored += 1

if display:
    elapsed = time.time() - tic
    print(f"Done. Scored {scored} FENs in {elapsed:.1f}s.", file=display)
    if unknown:
        print(
            f"The file {args.input} contained {unknown} new chessdb.cn positions.",
            file=display,
        )
        print(
            f"Rerunning the script after a short break should provide their evals.",
            file=display,
        )

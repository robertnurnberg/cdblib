"""
   Script to bulk-evaluate FENs/EPDs with chessdb.cn.
"""
import argparse, cdblib

parser = argparse.ArgumentParser(description="A simple script to request evals from chessdb.cn for a list of FENs/EPDs.")
parser.add_argument("filename", help="text file with FENs/EPDs")
parser.add_argument("-v", "--verbose", action="count", default=0,
       help="increase output")
args = parser.parse_args()

cdb = cdblib.cdbAPI()
unknown = 0
with open(args.filename) as f:
    for line in f:
        line = line.strip()
        if line:
            if line.startswith("#"): # ignore comments
                print(line)
                continue
            fen, _, _ = line.partition(";") # ignore all beyond first ";"
            parts = fen.split()
            pc = sum(p in "pnbrqk" for p in parts[0].lower())
            cf = (len(parts) >= 4 and parts[3] != "-" or
                  len(parts) >= 3 and parts[2] != "-")
            if pc <= 7 and cf: # cdb uses 7men TBs, so no castling flags allowed
                r = {}
                score = f"{pc}men w/ castling flags"
            else:
                r = cdb.queryscore(fen)
                if r.get("status") == "unknown": unknown += 1
                score = cdblib.json2eval(r)
            if score != "" and args.verbose: 
                if "ply" in r: score = f"{score}, ply: {r['ply']}"
                score = f"cdb eval: {score}"
            print(f"{line}{';' if line[-1] != ';' else ''} {score};")

if unknown:
    print(f"# The file {args.filename} contained {unknown} new chessdb.cn positions.")
    print(f"# Rerunning the script after a short break should provide their evals.")

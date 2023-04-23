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
    for fen in f:
        if fen and fen.strip():
            if fen.startswith("#"): continue # ignore comments
            r = cdb.queryscore(fen)
            if r.get("status") == "unknown": unknown += 1
            score = cdblib.json2eval(r)
            if score != "" and args.verbose: 
                if type(score) is int: score = f"{score}cp"
                if "ply" in r: score += f", ply: {r['ply']}"
                score = f"({score})"
            print(f"{fen[:-1]} {score}")

if unknown:
    print(f"# The file {args.filename} contained {unknown} new chessdb.cn positions.")
    print(f"# Rerunning the script after a short break should provide their evals.")

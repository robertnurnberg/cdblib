import argparse, sys, math, random
import chess, chess.pgn, cdblib


parser = argparse.ArgumentParser(
    description="A script that queries chessdb.cn for the PV of all positions in a file.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "filename", help="PGN file if suffix is .pgn, o/w a text file with FENs"
)
parser.add_argument(
    "--stable", action="store_true", help='pass "&stable=1" option to API'
)
parser.add_argument(
    "--san",
    action="store_true",
    help="For PGN files, give PVs in short algebraic notation (SAN).",
)
parser.add_argument(
    "-u",
    "--user",
    help="Add this username to the http user-agent header",
)
parser.add_argument(
    "--forever",
    action="store_true",
    help="Run the script in an infinite loop.",
)
args = parser.parse_args()
isPGN = args.filename.endswith(".pgn")
san = args.san if isPGN else False
cdb = cdblib.cdbAPI(args.user)
while True:  # if args.forever is true, run indefinitely; o/w stop after one run
    # re-reading the data in each loop allows updates to it in the background
    metalist = []
    if isPGN:
        pgn = open(args.filename)
        while game := chess.pgn.read_game(pgn):
            metalist.append(game)
        print(
            f"Read {len(metalist)} (opening) lines from file {args.filename}.",
            file=sys.stderr,
        )
    else:
        comments = 0
        with open(args.filename) as f:
            for line in f:
                line = line.strip()
                if line:
                    if line.startswith("#"):
                        comments += 1
                    metalist.append(line)
        print(
            f"Read {len(metalist)-comments} FENs from file {args.filename}.",
            file=sys.stderr,
        )
    gn = len(metalist)
    for i in range(gn):
        if isPGN:
            epd = metalist[i].end().board().epd()
        else:
            if metalist[i].startswith("#"):  # ignore comments
                print(metalist[i])
                continue
            epd = " ".join(metalist[i].split()[:4])  # cdb ignores move counters anyway
        r = cdb.querypvstable(epd) if args.stable else cdb.querypv(epd)
        score = cdblib.json2eval(r)
        if san:
            ply = len(list(metalist[i].mainline_moves()))
            pv = cdblib.json2pv(r, san=True, ply=ply)
            print(f"{metalist[i].mainline_moves()}; cdb eval: {score}; PV: {pv}")
        else:
            pv = cdblib.json2pv(r)
            line = epd if isPGN else metalist[i]
            print(f"{line}{';' if line[-1] != ';' else ''} cdb eval: {score}; PV: {pv}")
    print(f"Done processing {args.filename}.", flush=True)
    if not args.forever:
        break

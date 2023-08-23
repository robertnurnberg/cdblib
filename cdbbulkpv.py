import argparse, math, random
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
    "-v",
    "--verbose",
    action="count",
    default=0,
    help="Increase output with -v, -vv, -vvv etc.",
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
verbose = args.verbose
isPGN = args.filename.endswith(".pgn")
cdb = cdblib.cdbAPI(args.user)
while True:  # if args.forever is true, run indefinitely; o/w stop after one run
    # re-reading the data in each loop allows updates to it in the background
    metalist = []
    if isPGN:
        pgn = open(args.filename)
        while game := chess.pgn.read_game(pgn):
            metalist.append(game)
        print(f"Read {len(metalist)} (opening) lines from file {args.filename}.")
    else:
        with open(args.filename) as f:
            for line in f:
                line = line.strip()
                if line:
                    if line.startswith("#"):  # ignore comments
                        continue
                    fen = " ".join(line.split()[:4])  # cdb ignores move counters anyway
                    metalist.append(fen)
        print(f"Read {len(metalist)} FENs from file {args.filename}.")
    gn = len(metalist)
    for i in range(gn):
        if isPGN:
            board = metalist[i].end().board()
        else:
            board = chess.Board(metalist[i])
        r = cdb.querypvstable(board.epd()) if args.stable else cdb.querypv(board.epd())
        if verbose:
            score = cdblib.json2eval(r)
            if isPGN:
                print(f"Line {i+1}/{gn}", end=": ")
                print(metalist[i].mainline_moves(), end=" (")
            else:
                print(f"FEN {i+1}/{gn}: {board.epd()}", end=" (")
            if isPGN:
                ply = len(list(metalist[i].mainline_moves()))
                pv = cdblib.json2pv(r, san=True, ply=ply)
            else:
                pv = cdblib.json2pv(r)
            print(f"{score}{'cp' if type(score) is int else ''}) {pv}")
            if verbose >= 2:
                url = f"https://chessdb.cn/queryc_en/?{board.epd()}"
                if "pv" in r and len(r["pv"]):
                    url += " moves " + " ".join(tuple(r["pv"]))
                print("  URL:", url.replace(" ", "_"))
    print(f"Done processing {args.filename}.", flush=True)
    if not args.forever:
        break

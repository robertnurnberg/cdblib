"""
   Script that sends the first --depth plies of games in a PGN file to cdb at
   chessdb.cn. Use local cache to reduce API requests for large PGN files.
"""
import argparse, time
import chess, chess.pgn, cdblib


class dbcache:
    # local cache for cdbAPI responses that avoids duplicate queries to API
    def __init__(self):
        self.cdbAPI = cdblib.cdbAPI()
        self.cache = {}
        self.req_received, self.req_cached, self.queued = 0, 0, 0

    def get(self, fen):
        """queryscore from API, use cached result if possible"""
        self.req_received += 1
        r = self.cache.get(fen)
        if r is not None:
            self.req_cached += 1
        else:
            # returns dictionary with keys "status", "eval" and possibly "ply"
            r = self.cdbAPI.queryscore(fen)
            self.cache[fen] = r
        return r

    def queue(self, fen):
        """queue fen via API, add entry to cache as well"""
        self.cdbAPI.queue(fen)
        self.queued += 1
        self.cache[fen] = {"status": "ok"}  # assume fen is in cdb from now on


parser = argparse.ArgumentParser(
    description="A simple script to pass pgns to chessdb.cn.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("filename", help="pgn file")
parser.add_argument(
    "-v",
    "--verbose",
    action="count",
    default=0,
    help="increase output with -v, -vv, -vvv etc.",
)
parser.add_argument(
    "-d",
    "--depth",
    type=int,
    default=30,
    help="number of plies to be added to chessdb.cn",
)
args = parser.parse_args()
pgn = open(args.filename)
gamelist = []
while game := chess.pgn.read_game(pgn):
    gamelist.append(game)
gn, seen = len(gamelist), 0
print(f"Read {gn} pgns from file {args.filename}.")
print(f"Starting to pass these to chessdb.cn to depth {args.depth} ...", flush=True)
db = dbcache()
for i in reversed(range(gn)):
    board = chess.Board()
    if args.verbose >= 4:
        print("    pgn {i+1}/{gn}:" + str(gamelist[i].mainline_moves()))
    plies, pc = 0, 32
    for move in gamelist[i].mainline_moves():
        if args.verbose >= 3:
            print(f"    pgn {i+1}/{gn}, ply {plies+1:3d}: " + str(move))
        board.push(move)
        plies += 1
        pc = 64 - str(board).count(".")  # count pieces left on the board
        if plies >= args.depth or pc <= 7:
            break  # cdb only stores pos if >= 8
    if args.verbose:
        print(
            f"  For pgn {i+1}/{gn} read {plies}/{args.depth} plies. Final pos has {pc} pieces.",
            flush=True,
        )
    if plies == 0:
        continue  # some pgn's include empty games
    if board.is_checkmate() or board.is_stalemate():
        # mates and stalemates are not stored as nodes on chessdb.cn
        if args.verbose:
            print(f"    Position at depth {plies} is checkmate or stalemate.")
        board.pop()
        plies -= 1
    r = db.get(board.fen())
    cdbply = r.get("ply", -1)
    if r["status"] == "ok":
        seen += 1
        if args.verbose:
            print(
                f"    Position at depth {plies} is already in chessdb.cn"
                + (
                    f", with distance {cdbply} from root."
                    if cdbply != -1
                    else ", not yet connected to root."
                )
            )
    elif r["status"] == "unknown":
        if args.verbose:
            print(f"    Position at depth {plies} is new to chessdb.cn.")
    new_fens, startply = False, plies
    while plies and cdbply != plies:  # walk back until we are connected to root
        if r["status"] == "unknown":
            if not new_fens and args.verbose >= 2:
                print(f"    Queueing new positions from ply {plies} ... ")
            db.queue(board.fen())
            new_fens = True
        elif new_fens:
            if args.verbose >= 2:
                print(f"    Queued new positions until ply {plies+1}.")
            new_fens = False
        move = board.pop()
        r = db.get(board.fen())
        cdbply = r.get("ply", -1)
        plies -= 1
        if args.verbose >= 4:
            print(f"      plies = {plies}, cdbply = {cdbply}.")
    if new_fens and args.verbose >= 2:
        print(f"    Queued new positions until ply {plies+1}.")
    if plies < startply and args.verbose:
        print(f"    Position at depth {plies} is connected to the root.")

print(f"Done processing {args.filename} to depth {args.depth}.")
print(f"{seen}/{gn} final positions already in chessdb.cn. ({seen/gn*100:.2f}%)")
print(
    f"Queued {db.queued} new positions to chessdb.cn. Local cache hit rate: {db.req_cached}/{db.req_received} = {db.req_cached/db.req_received*100:.2f}%."
)

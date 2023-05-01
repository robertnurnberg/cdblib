"""
   Script that makes chessdb.cn explore certain openings or book exits.
"""
import argparse, math, random
import chess, chess.pgn, cdblib


def select_move(movelist, temp):
    # select a random move from movelist, using an exponential distribution
    # in the argument (score - bestscore) / temp
    if temp <= 0:  # return best move if temp <= 0
        return movelist[0]["uci"]
    best = int(movelist[0]["score"])
    weights = [math.exp((int(m["score"]) - best) / temp) for m in movelist]
    p = random.random() * sum(weights)
    wsum = 0
    for i, m in enumerate(movelist):
        if (wsum := wsum + weights[i]) > p:
            break
    return m["uci"]


parser = argparse.ArgumentParser(
    description="A script that walks within the chessdb.cn tree, starting from lines in a pgn file. Based on the given parameters, the script selects a move in each node, walking towards the leafs. Once an unknown position is reached, it is queued for analysis and the walk terminates.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("filename", help="pgn file")
parser.add_argument(
    "-v",
    "--verbose",
    action="count",
    default=0,
    help="Increase output with -v, -vv, -vvv etc.",
)
parser.add_argument(
    "--moveTemp",
    type=float,
    default=10,
    help="Temperature T for move selection: in each node of the tree the probability to pick a move m will be proportional to exp((eval(m)-eval(bestMove))/T). If T is zero, then always select the best move.",
)
parser.add_argument(
    "--backtrack",
    type=int,
    default=0,
    help="The number of plies to walk back from newly the created leaf towards the root, queuing each position on the way for analysis.",
)
parser.add_argument(
    "--forever",
    action="store_true",
    help="Run the script in an infinite loop.",
)
args = parser.parse_args()
verbose = args.verbose
cdb = cdblib.cdbAPI()
while True:  # if args.forever is true, run indefinitely; o/w stop after one run
    pgn = open(args.filename)
    gamelist = []
    while game := chess.pgn.read_game(pgn):
        gamelist.append(game)
    gn, seen = len(gamelist), 0
    print(f"Read {gn} (opening) lines from file {args.filename}.")
    for i in range(gn):
        board = gamelist[i].end().board()
        r = cdb.queryall(board.fen())
        score = cdblib.json2eval(r)
        if verbose:
            print(f"Line {i+1}/{gn}", end=": ")
            print(gamelist[i].mainline_moves(), end=" (")
            print(f"{score}{'cp' if type(score) is int else ''})", end=" ")
        ply = len(list(gamelist[i].mainline_moves()))
        while "moves" in r:
            m = select_move(r["moves"], temp=args.moveTemp)
            if not m:
                break
            move = chess.Move.from_uci(m)
            if verbose:
                if board.turn == chess.WHITE:
                    print(f"{(ply+2) // 2}.", end=" ")
                print(board.san(move), end=" ")
            board.push(move)
            ply += 1
            r = cdb.queryall(board.fen())
        if verbose >= 3:
            print("\n  Final fen =", board.fen(), end="")
        if verbose >= 2:
            print(f"\n  Ply queued for analysis: {ply}", end="")
        bt = 0
        while bt < args.backtrack and bt < ply:
            cdb.queue(board.fen())
            board.pop()
            bt += 1
        if bt and verbose >= 2:
            print(f" ... {ply-bt}.", end="")
        if verbose:
            print("", flush=True)
    print(f"Done processing {args.filename}.")
    if not args.forever:
        break

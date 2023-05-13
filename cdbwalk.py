"""
   Script that makes chessdb.cn explore certain openings or book exits.
"""
import argparse, math, random
import chess, chess.pgn, cdblib


def select_move(movelist, temp):
    # select a random move from movelist, using an exponential distribution in the argument (score - bestscore) / temp
    if temp <= 0:  # return best move if temp <= 0
        return movelist[0]["uci"]
    weights = []
    first, score = True, 0
    for m in movelist:
        if (
            "score" in m and type(m["score"]) == int
        ):  # if e.g. m["score"] == "??", then use score from previous move
            score = m["score"]
        if first:
            first, best = False, score
        weights.append(math.exp((score - best) / temp))
    p = random.random() * sum(weights)
    wsum = 0
    for i, m in enumerate(movelist):
        if (wsum := wsum + weights[i]) > p:
            break
    return m["uci"]


parser = argparse.ArgumentParser(
    description="A script that walks within the chessdb.cn tree, starting from FENs or lines in a PGN file. Based on the given parameters, the script selects a move in each node, walking towards the leafs. Once an unknown position is reached, it is queued for analysis and the walk terminates.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument(
    "filename", help="PGN file if suffix is .pgn, o/w a text file with FENs"
)
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
    help="Temperature T for move selection: in each node of the tree the probability to pick a move m will be proportional to exp((score(m)-score(bestMove))/T). Here unscored moves get assigned the score of the currently worst move. If T is zero, then always select the best move.",
)
parser.add_argument(
    "--backtrack",
    type=int,
    default=0,
    help="The number of plies to walk back from the newly created leaf towards the root, queuing each position on the way for analysis.",
)
parser.add_argument(
    "--depthLimit",
    help="The upper limit of plies the walk is allowed to last.",
    type=int,
    default=200,
)
parser.add_argument(
    "--forever",
    action="store_true",
    help="Run the script in an infinite loop.",
)
args = parser.parse_args()
verbose = args.verbose
isPGN = args.filename.endswith(".pgn")
cdb = cdblib.cdbAPI()
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
    gn, seen = len(metalist), 0
    for i in range(gn):
        if isPGN:
            board = metalist[i].end().board()
        else:
            board = chess.Board(metalist[i])
        r = cdb.showall(board.epd())
        score = cdblib.json2eval(r)
        if verbose:
            if isPGN:
                print(f"Line {i+1}/{gn}", end=": ")
                print(metalist[i].mainline_moves(), end=" (")
            else:
                print(f"FEN {i+1}/{gn}: {board.epd()}", end=" (")
            print(f"{score}{'cp' if type(score) is int else ''})", end=" ")
            url = f"https://chessdb.cn/queryc_en/?{board.epd()}"
        if isPGN:
            ply0 = len(list(metalist[i].mainline_moves()))
        else:
            if board.turn == chess.WHITE:
                ply0 = 0
            else:
                ply0 = 1
                if verbose:
                    print(f"1...", end=" ")
        ply = ply0
        while "moves" in r and ply - ply0 < args.depthLimit:
            m = select_move(r["moves"], temp=args.moveTemp)
            move = chess.Move.from_uci(m)
            if verbose:
                if board.turn == chess.WHITE:
                    print(f"{(ply+2) // 2}.", end=" ")
                print(board.san(move), end=" ")
                if ply == ply0:
                    url += " moves"
                url += " " + m
            board.push(move)
            ply += 1
            if board.can_claim_draw() or board.is_insufficient_material():
                r = {}
                if verbose:
                    print("1/2 - 1/2", end="")
            else:
                r = cdb.queryall(board.epd())
        if verbose >= 3:
            print("\n  URL:", url.replace(" ", "_"), end="")
        if verbose >= 2:
            print(f"\n  Ply queued for analysis: {ply}", end="")
        bt = 0
        while bt < args.backtrack and board.move_stack:
            cdb.queue(board.epd())
            board.pop()
            bt += 1
        if bt and verbose >= 2:
            print(f" ... {ply-bt}.", end="")
        if verbose:
            print("", flush=True)
    print(f"Done processing {args.filename}.")
    if not args.forever:
        break

import argparse, gzip, sys, chess, chess.pgn


def open_pgn(filename):
    if filename.endswith(".gz"):
        return gzip.open(filename, "rt", encoding="utf-8", errors="replace")
    return open(filename, "rt", encoding="utf-8", errors="replace")


def game_link(game):
    board = game.board()
    url = f"https://chessdb.cn/queryc_en/?{board.epd()}"
    moves = [m.uci() for m in game.mainline_moves()]
    if moves:
        url += " moves " + " ".join(moves)
    return url.replace(" ", "_")


parser = argparse.ArgumentParser(
    description="Print an extended chessdb.cn link (with the game moves) for each game in a PGN file."
)
parser.add_argument("filename", help="PGN file (.pgn or .pgn.gz).")
parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Precede each link with a comment line giving the game number and players.",
)
args = parser.parse_args()

n = 0
with open_pgn(args.filename) as pgn:
    while game := chess.pgn.read_game(pgn):
        n += 1
        if args.verbose:
            h = game.headers
            print(
                f"# Game {n}: {h.get('White', '?')} - {h.get('Black', '?')}, {h.get('Result', '*')}"
            )
        print(game_link(game))
print(f"Processed {n} games from {args.filename}.", file=sys.stderr)

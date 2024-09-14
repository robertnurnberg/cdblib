import argparse, asyncio, math, time
import chess, chess.pgn, cdblib
from io import StringIO


def softmax(movelist, temp):
    best = movelist[0]["score"]
    if temp <= 0:  # return best move if temp <= 0
        return best
    average = total_weights = 0
    for m in movelist:
        score = m["score"]
        weight = math.exp((score - best) / temp)
        average += score * weight
        total_weights += weight
        print(f"move: {m['uci']:>5s}, score: {m['score']:4d}, weight: {weight:.6f}")
    average /= total_weights
    return average


async def main():
    parser = argparse.ArgumentParser(
        description="Compute new softmax eval for a cdb position.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--epd",
        help="""EPD/FEN to evaluate: acceptable are FENs w/ and w/o move counters, as well as the extended "['startpos'|FEN] moves m1 m2 m3" syntax.""",
        default="startpos moves g2g4",
    )
    group.add_argument(
        "--san",
        help='Moves in SAN notation that lead to the position to be evaluated. E.g. "1. g4".',
    )
    parser.add_argument(
        "--moveTemp",
        type=float,
        default=10,
        help="cdb's temperature",
    )
    parser.add_argument(
        "-u",
        "--user",
        help="Add this username to the http user-agent header",
    )
    args = parser.parse_args()

    if args.san is not None:
        if args.san:
            game = chess.pgn.read_game(StringIO(args.san))
            epd = game.board().epd() + " moves"
            for move in game.mainline_moves():
                epd += f" {move}"
        else:
            epd = chess.STARTING_FEN  # passing empty string to --san gives startpos
    else:
        epd = args.epd.replace("startpos", chess.STARTING_FEN[:-3])

    if "moves" in epd:
        epd, _, epdMoves = epd.partition("moves")
        epdMoves = epdMoves.split()
    else:
        epdMoves = []
    board = chess.Board(epd)
    for move in epdMoves:
        uci = chess.Move.from_uci(move)
        if not uci in board.legal_moves:
            print(
                f' - Warning: Encountered illegal move {move} at position "{board.epd()}". Ignoring this and all following moves.'
            )
            break
        board.push(uci)

    cdb = cdblib.cdbAPI(concurrency=1, user=args.user)
    r = await cdb.queryall(board.epd())
    e = softmax(r["moves"], temp=args.moveTemp)

    print("Weighted eval: ", e)


if __name__ == "__main__":
    asyncio.run(main())

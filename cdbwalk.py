"""
   Script that makes chessdb.cn explore certain openings or book exits.
"""
import argparse, asyncio, math, random, time, chess, chess.pgn, cdblib


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


class cdbwalk:
    def __init__(
        self,
        filename,
        verbose,
        moveTemp,
        backtrack,
        depthLimit,
        TBwalk,
        concurrency,
        user,
    ):
        self.filename = filename
        self.isPGN = filename.endswith(".pgn") or filename.endswith(".pgn.gz")
        self.verbose = verbose
        self.moveTemp = moveTemp
        self.backtrack = backtrack
        self.depthLimit = depthLimit
        self.TBwalk = TBwalk
        self.concurrency = concurrency
        self.cdb = cdblib.cdbAPI(concurrency, user)

    def reload(self):
        self.metalist = []
        if self.isPGN:
            pgn = cdblib.open_file_rt(self.filename)
            while game := chess.pgn.read_game(pgn):
                self.metalist.append(game)
            print(
                f"Read {len(self.metalist)} (opening) lines from file {self.filename}.",
                flush=True,
            )
        else:
            with cdblib.open_file_rt(self.filename) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        if line.startswith("#"):  # ignore comments
                            continue
                        fen = line.split()[:6]  # include potential move counters
                        if len(fen) == 6 and not (
                            fen[4].isnumeric() and fen[5].isnumeric()
                        ):
                            fen = fen[:4]
                        fen = " ".join(fen)
                        self.metalist.append(fen)
            print(
                f"Read {len(self.metalist)} FENs from file {self.filename}.", flush=True
            )
        self.gn = len(self.metalist)

    async def parse_all(self, batchSize=None):
        print(
            f"Started parsing the positions with concurrency {self.concurrency}"
            + (" ..." if batchSize == None else f" and batch size {batchSize} ..."),
            flush=True,
        )
        if batchSize is None:
            batchSize = len(self.metalist)
        self.tic = time.time()
        for i in range(0, len(self.metalist), batchSize):
            tasks = []
            for lineIdx in range(i, min(i + batchSize, len(self.metalist))):
                tasks.append(asyncio.create_task(self.parse_single_line(lineIdx)))

            for parse_line in tasks:
                p = await parse_line
                if p:
                    print(p)

        elapsed = time.time() - self.tic
        print(
            f"Done processing {self.filename} in {elapsed:.1f}s.",
        )

    async def parse_single_line(self, lineIdx):
        line = self.metalist[lineIdx]
        if self.isPGN:
            board = line.end().board()
        else:
            board = chess.Board(line)
        r = await self.cdb.showall(board.epd())
        score = cdblib.json2eval(r)
        retStr = ""
        if self.verbose:
            if self.isPGN:
                retStr += f"Line {lineIdx+1}/{self.gn}: "
                retStr += str(line.mainline_moves()) + " ("
            else:
                retStr += f"FEN {lineIdx+1}/{self.gn}: {board.epd()} ("
            retStr += f"{score}{'cp' if type(score) is int else ''}) "
            url = f"https://chessdb.cn/queryc_en/?{board.epd()}"
        if self.isPGN:
            ply0 = len(list(line.mainline_moves()))
        else:
            if board.turn == chess.WHITE:
                ply0 = 0
            else:
                ply0 = 1
                if self.verbose:
                    retStr += f"1... "
        ply = ply0
        while "moves" in r and ply - ply0 < self.depthLimit:
            m = select_move(r["moves"], temp=self.moveTemp)
            move = chess.Move.from_uci(m)
            if self.verbose:
                if board.turn == chess.WHITE:
                    retStr += f"{(ply+2) // 2}. "
                retStr += f"{str(board.san(move))} "
                if ply == ply0:
                    url += " moves"
                url += " " + m
            board.push(move)
            ply += 1
            if board.can_claim_draw() or board.is_insufficient_material():
                r = {}
                if self.verbose:
                    retStr += "1/2 - 1/2"
            elif (
                not self.TBwalk
                and (pc := sum(p in "pnbrqk" for p in board.epd().lower().split()[0]))
                <= 7
            ):
                r = {}
                if self.verbose:
                    retStr += f"{pc}men EGTB"
            else:
                r = await self.cdb.queryall(board.epd())
        if self.verbose >= 3:
            retStr += f'\n  URL: {url.replace(" ", "_")}'
        bt = 0
        while bt <= self.backtrack:
            asyncio.ensure_future(self.cdb.queue(board.epd()))
            bt += 1
            if not board.move_stack:
                break
            board.pop()
        if bt and self.verbose >= 2:
            retStr += f"\n  Plies queued for analysis: {ply} ... {ply-bt+1}."
        return retStr


async def main():
    parser = argparse.ArgumentParser(
        description="A script that walks within the chessdb.cn tree, starting from FENs or lines in a PGN file. Based on the given parameters, the script selects a move in each node, walking towards the leafs. Once an unknown position is reached, it is queued for analysis and the walk terminates.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "filename", help="PGN file if suffix is .pgn(.gz), o/w a file with FENs."
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
        "--TBwalk",
        action="store_true",
        help="Continue the walk in 7men EGTB land.",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        help="Maximum concurrency of requests to cdb.",
        type=int,
        default=16,
    )
    parser.add_argument(
        "-b",
        "--batchSize",
        help="Number of positions processed in parallel. Small values guarantee more responsive output, large values give faster turnaround.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-u",
        "--user",
        help="Add this username to the http user-agent header.",
    )
    parser.add_argument(
        "--forever",
        action="store_true",
        help="Run the script in an infinite loop.",
    )
    args = parser.parse_args()

    walk = cdbwalk(
        args.filename,
        args.verbose,
        args.moveTemp,
        args.backtrack,
        args.depthLimit,
        args.TBwalk,
        args.concurrency,
        args.user,
    )
    while True:  # if args.forever is true, run indefinitely; o/w stop after one run
        # re-reading the data in each loop allows updates to it in the background
        walk.reload()
        await walk.parse_all(args.batchSize)

        if not args.forever:
            break


if __name__ == "__main__":
    asyncio.run(main())

import argparse, asyncio, gzip, logging, time, chess, chess.pgn, cdblib


def open_file_rt(filename):
    # allow reading text files either plain or in gzip format
    open_func = gzip.open if filename.endswith(".gz") else open
    return open_func(filename, "rt")


class bulk2cdb:
    def __init__(self, args):
        self.verbose = args.verbose
        self.concurrency = args.concurrency
        self.plyBegin = args.plyBegin
        self.plyEnd = args.plyEnd
        self.pieceMin = args.pieceMin
        self.pieceMax = args.pieceMax
        print(f"Loading games from {len(args.filenames)} file(s) ...", flush=True)
        self.tic = time.time()
        self.fens = set()
        self.gameCount = 0
        for f in args.filenames:
            epds, count = self.load_epds(f)
            self.fens.update(epds)
            self.gameCount += count
        elapsed = time.time() - self.tic
        print(f"Done. Parsed {self.gameCount} games/lines in {elapsed:.1f}s.")
        print(
            f"Found {len(self.fens)} unique positions from {self.gameCount} games/lines in {len(args.filenames)} file(s) to send to cdb.",
            flush=True,
        )
        if args.outFile:
            fens = sorted(list(self.fens))
            with open(args.outFile, "w") as f:
                for fen in fens:
                    f.write(fen + "\n")
            print(f"Wrote the unique positions to {args.outFile}.")

        self.cdb = cdblib.cdbAPI(args.concurrency, args.user)

    def load_epds(self, filename):
        """returns a set of unique EPDs found in the given file"""
        epdlist = []
        if filename.endswith(".pgn") or filename.endswith(".pgn.gz"):
            pgn = open_file_rt(filename)
            logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)
            while True:
                game = chess.pgn.read_game(pgn)
                if game is None:
                    break
                for e in game.errors:
                    if isinstance(e, chess.IllegalMoveError):
                        move = str(e).split(":")[-1].strip()
                        print(f"Ignoring illegal move {move}")
                    else:
                        print(f'Encountered error "{e}". Will try to continue.')
                epd = game.board().epd()  # ignore move counters
                epdMoves = " moves"
                for m in game.mainline_moves():
                    epdMoves += f" {m}"
                if epdMoves != " moves":
                    epd += epdMoves
                epdlist.append(epd)
            print(f"Loaded {len(epdlist)} games from file {filename}.")
        else:
            with open_file_rt(filename) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        if line.startswith("#"):  # ignore comments
                            continue
                        line = line.split(";")[0]  # ignore epd opcodes
                        epd, _, moves = line.partition("moves")
                        epd = epd.split()[:4]  # ignore move counters
                        epd = " ".join(epd)
                        epdMoves = " moves"
                        for m in moves.split():
                            if (
                                len(m) < 4
                                or len(m) > 5
                                or not {m[0], m[2]}.issubset(set("abcdefgh"))
                                or not {m[1], m[3]}.issubset(set("12345678"))
                                or (len(m) == 5 and not m[4] in "qrbn")
                            ):
                                break
                            epdMoves += f" {m}"
                        if epdMoves != " moves":
                            epd += epdMoves
                        epdlist.append(epd)
            print(f"Loaded {len(epdlist)} (extended) EPDs from file {filename}.")

        epds = set()  # use a set to filter duplicates
        for i, epd in enumerate(epdlist):
            if self.verbose >= 2:
                print(f"Line {i}: {epd}")
            epd, _, moves = epd.partition(" moves")
            moves = [None] + moves.split()  # to be able to use plyBegin=0 for epd
            plyB = (
                0
                if self.plyBegin is None
                else max(0, self.plyBegin + len(moves))
                if self.plyBegin < 0
                else min(self.plyBegin, len(moves))
            )
            plyE = (
                len(moves)
                if self.plyEnd is None
                else max(0, self.plyEnd + len(moves))
                if self.plyEnd < 0
                else min(self.plyEnd, len(moves))
            )
            board = chess.Board(epd)
            c = 0
            for ply, m in enumerate(moves):
                if m is not None:
                    board.push(chess.Move.from_uci(m))
                pc = 64 - str(board).count(".")  # piece count
                if ply >= plyE or pc < self.pieceMin or not bool(board.legal_moves):
                    break
                if (
                    plyB <= ply
                    and ply < plyE
                    and self.pieceMin <= pc
                    and pc <= self.pieceMax
                ):
                    epds.add(board.epd())
                    c += 1
            if self.verbose:
                print(f" ... found {c} positions.")

        print(f"Loaded {len(epds)} unique EPDs from file {filename}.")
        return epds, len(epdlist)

    async def parse_all(self):
        print(
            f"Started parsing the FENs with concurrency {self.concurrency} ...",
            flush=True,
        )
        self.tic = time.time()
        tasks = []
        for fen in self.fens:
            tasks.append(asyncio.create_task(self.parse_single_fen(fen)))

        for parse_fen in tasks:
            await parse_fen

        elapsed = time.time() - self.tic
        print(
            f"Done. Queued {len(self.fens)} FENs from {self.gameCount} games in {elapsed:.1f}s."
        )

    async def parse_single_fen(self, fen):
        timeout = 0
        r = {"status": ""}
        while r["status"] != "ok" and r["status"] != "invalid board":
            r = await self.cdb.queue(fen)
            if timeout:
                if self.verbose:
                    print(f"Got status {r['status']} for FEN {fen}.")
                await asyncio.sleep(timeout)
            timeout = max(5, min(timeout * 1.5, 120))


async def main():
    parser = argparse.ArgumentParser(
        description="A script to queue positions from files to chessdb.cn.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "filenames",
        nargs="+",
        help="""Files that contain games/lines to be uploaded. Suffix .pgn(.gz) indicates PGN format, o/w a (.gz) text file with FENs/EPDs. The latter may use the extended "moves m1 m2 m3" syntax from cdb's API.""",
    )
    parser.add_argument(
        "-o",
        "--outFile",
        help="Filename to write unique FENs to.",
        default=None,
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output with -v, -vv, -vvv etc.",
    )
    parser.add_argument(
        "--plyBegin",
        help="Ply in each line from which positions will be queued to cdb. A value of 0 corresponds to the starting FEN without any moves played. Negative values count from the back, as per the Python standard.",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--plyEnd",
        help="Ply in each line until which positions will be queued to cdb. A value of None means including the final move of the line.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--pieceMin",
        help="Only queue positions with at least this many pieces (cdb only stores positions with 8 pieces or more).",
        type=int,
        default=8,
    )
    parser.add_argument(
        "--pieceMax",
        help="Only queue positions with at most this many pieces.",
        type=int,
        default=32,
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        help="Maximum concurrency of requests to cdb.",
        type=int,
        default=16,
    )
    parser.add_argument(
        "-u",
        "--user",
        help="Add this username to the http user-agent header.",
    )
    args = parser.parse_args()
    p2c = bulk2cdb(args)
    await p2c.parse_all()


if __name__ == "__main__":
    asyncio.run(main())

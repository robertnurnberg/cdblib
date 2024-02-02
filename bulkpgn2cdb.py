import argparse, asyncio, logging, time, chess, chess.pgn, cdblib


class bulkpgn2cdb:
    def __init__(self, filenames, outFile, verbose, depth, concurrency, user):
        self.verbose = verbose
        self.depth = depth
        self.concurrency = concurrency
        self.fens = set()
        self.gameCount = 0
        print(f"Loading games from {len(filenames)} file(s) ...", flush=True)
        self.tic = time.time()
        for f in filenames:
            pgn = cdblib.open_file_rt(f)
            logging.getLogger("chess.pgn").setLevel(logging.CRITICAL)
            while game := chess.pgn.read_game(pgn):
                self.gameCount += 1
                for e in game.errors:
                    if isinstance(e, chess.IllegalMoveError):
                        move = str(e).split(":")[-1].strip()
                        print(f"Ignoring illegal move {move}")
                    else:
                        print(f'Encountered error "{e}". Will try to continue.')
                board = game.board()
                if self.verbose >= 2:
                    print(f"game {self.gameCount}: {str(game.mainline_moves())}")
                plies, pc = 0, 32
                for move in game.mainline_moves():
                    pc = 64 - str(board).count(".")  # piece count
                    if (
                        plies > self.depth
                        or pc <= 7
                        or board.is_checkmate()
                        or board.is_stalemate()
                    ):
                        break
                    self.fens.add(board.epd())
                    board.push(move)
                    plies += 1
                if self.verbose:
                    print(f"For game {self.gameCount} found {plies} positions.")

        elapsed = time.time() - self.tic
        print(
            f"Done. Parsed {self.gameCount} games to depth {self.depth} in {elapsed:.1f}s."
        )
        print(
            f"Found {len(self.fens)} unique positions from {self.gameCount} games in {len(filenames)} file(s) to send to cdb.",
            flush=True,
        )
        if outFile:
            fens = sorted(list(self.fens))
            with open(outFile, "w") as f:
                for fen in fens:
                    f.write(fen + "\n")
            print(f"Wrote the unique positions to {outFile}.")

        self.cdb = cdblib.cdbAPI(concurrency, user)

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
            f"Done. Queued {len(self.fens)} FENs from {self.gameCount} games to depth {self.depth} in {elapsed:.1f}s."
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
        description="A script to pass many positions from pgns to chessdb.cn.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("filenames", nargs="+", help=".pgn(.gz) file(s)")
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
        "-d",
        "--depth",
        type=int,
        default=100,
        help="Number of plies to be added to chessdb.cn.",
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
    p2c = bulkpgn2cdb(
        args.filenames,
        args.outFile,
        args.verbose,
        args.depth,
        args.concurrency,
        args.user,
    )
    await p2c.parse_all()


if __name__ == "__main__":
    asyncio.run(main())

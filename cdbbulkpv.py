import argparse, asyncio, sys, time
import chess, chess.pgn, cdblib


class bulkpv:
    def __init__(self, filename, stable, san, concurrency, user):
        self.filename = filename
        self.stable = stable
        self.isPGN = filename.endswith(".pgn")
        self.san = san if self.isPGN else False
        self.concurrency = concurrency
        self.cdb = cdblib.cdbAPI(concurrency, user)

    def reload(self):
        self.metalist = []
        if self.isPGN:
            pgn = open(self.filename)
            while game := chess.pgn.read_game(pgn):
                self.metalist.append(game)
            self.count = len(self.metalist)
            print(
                f"Read {self.count} (opening) lines from file {self.filename}.",
                file=sys.stderr,
                flush=True,
            )
        else:
            comments = 0
            with open(self.filename) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.metalist.append(line)
                        if line.startswith("#"):
                            comments += 1
            self.count = len(self.metalist) - comments
            print(
                f"Read {self.count} FENs from file {self.filename}.",
                file=sys.stderr,
                flush=True,
            )

    async def parse_all(self, batchSize=None):
        print(
            f"Started parsing the positions with concurrency {self.concurrency}"
            + (" ..." if batchSize == None else f" and batch size {batchSize} ..."),
            file=sys.stderr,
            flush=True,
        )
        if batchSize is None:
            batchSize = len(self.metalist)
        self.tic = time.time()
        for i in range(0, len(self.metalist), batchSize):
            tasks = []
            for line in self.metalist[i : i + batchSize]:
                tasks.append(asyncio.create_task(self.parse_single_line(line)))

            for parse_line in tasks:
                print(await parse_line)

        elapsed = time.time() - self.tic
        print(
            f"Done. Polled {self.count} positions in {elapsed:.1f}s.",
            file=sys.stderr,
        )

    async def parse_single_line(self, line):
        if self.isPGN:
            epd = line.end().board().epd()
        else:
            if line.startswith("#"):  # ignore comments
                return line
            epd = " ".join(line.split()[:4])  # cdb ignores move counters anyway
        r = await (
            self.cdb.querypvstable(epd) if self.stable else self.cdb.querypv(epd)
        )
        score = cdblib.json2eval(r)
        if self.san:
            ply = len(list(line.mainline_moves()))
            pv = cdblib.json2pv(r, san=True, ply=ply)
            return f"{line.mainline_moves()}; cdb eval: {score}; PV: {pv}"
        else:
            pv = cdblib.json2pv(r)
            if self.isPGN:
                line = epd
            return f"{line}{';' if line[-1] != ';' else ''} cdb eval: {score}; PV: {pv}"


async def main():
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
        help="Add this username to the http user-agent header",
    )
    parser.add_argument(
        "--forever",
        action="store_true",
        help="Run the script in an infinite loop.",
    )
    args = parser.parse_args()
    bpv = bulkpv(args.filename, args.stable, args.san, args.concurrency, args.user)
    while True:  # if args.forever is true, run indefinitely; o/w stop after one run
        # re-reading the data in each loop allows updates to it in the background
        bpv.reload()
        await bpv.parse_all(args.batchSize)

        if not args.forever:
            break


if __name__ == "__main__":
    asyncio.run(main())

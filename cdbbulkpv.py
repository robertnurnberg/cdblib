import argparse, asyncio, sys, time
import chess, chess.pgn, cdblib


class bulkpv:
    def __init__(self, filename, san, concurrency, user):
        self.filename = filename
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
            print(
                f"Read {len(self.metalist)} (opening) lines from file {self.filename}.",
                file=sys.stderr,
            )
        else:
            with open(self.filename) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.metalist.append(line)
            print(
                f"Read {len(self.metalist)} FENs from file {self.filename}.",
                file=sys.stderr,
            )

    async def parse_all(self, batchSize=None):
        print(
            f"Started parsing the positions with concurrency {self.concurrency}"
            + (" ..." if batchSize == None else f" and batch size {batchSize} ..."),
            file=sys.stderr,
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
            f"Done. Polled {len(self.metalist)} positions in {elapsed:.1f}s.",
            file=sys.stderr,
        )

    async def parse_single_line(self, line):
        if self.isPGN:
            epd = line.end().board().epd()
        else:
            if line.startswith("#"):  # ignore comments
                return line
            epd = " ".join(line.split()[:4])  # cdb ignores move counters anyway
        r = await self.cdb.querypv(epd)
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
    bpv = bulkpv(args.filename, args.san, args.concurrency, args.user)
    while True:  # if args.forever is true, run indefinitely; o/w stop after one run
        # re-reading the data in each loop allows updates to it in the background
        bpv.reload()
        await bpv.parse_all(args.batchSize)

        if not args.forever:
            break


if __name__ == "__main__":
    asyncio.run(main())

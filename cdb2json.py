"""
   Script to get json data for FENs from chessdb.cn.
"""
import argparse, asyncio, json, sys, time, cdblib


class cdb2json:
    def __init__(self, filename, output, retainAll, quiet, concurrency, user):
        self.input = filename
        self.lines = []
        self.loaded = 0
        with cdblib.open_file_rt(filename) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):  # ignore comments
                    self.lines.append(line)
                    self.loaded += 1
        if output:
            self.output = open(output, "w")
            self.display = sys.stdout
        else:
            self.output = sys.stdout
            self.display = sys.stderr
        if quiet:
            self.display = None
        if self.display:
            print(
                f"Read {self.loaded} FENs from file {self.input}.",
                file=self.display,
                flush=True,
            )
        self.retainAll = retainAll
        self.concurrency = concurrency
        self.cdb = cdblib.cdbAPI(concurrency, user)

    async def parse_all(self, batchSize=None):
        if self.display:
            print(
                f"Started parsing the FENs with concurrency {self.concurrency}"
                + (" ..." if batchSize == None else f" and batch size {batchSize} ..."),
                file=self.display,
                flush=True,
            )
        if batchSize is None:
            batchSize = len(self.lines)
        self.tic = time.time()
        self.json = {}
        for i in range(0, len(self.lines), batchSize):
            tasks = []
            for line in self.lines[i : i + batchSize]:
                tasks.append(asyncio.create_task(self.parse_single_line(line)))

            for parse_line in tasks:
                fen, d = await parse_line
                self.json[fen] = d
                if self.display:
                    print(
                        f"Progress: {len(self.json)}/{self.loaded}",
                        end="\r",
                        file=self.display,
                        flush=True,
                    )

        print(json.dumps(self.json), file=self.output)

        if self.display:
            elapsed = time.time() - self.tic
            print(
                f"Done. Processed {self.loaded} FENs in {elapsed:.1f}s.",
                file=self.display,
            )

    async def parse_single_line(self, line):
        fen = " ".join(line.split()[:4])  # cdb ignores move counters anyway
        d = await self.cdb.queryall(fen)
        d.pop("fen")
        if self.retainAll:
            return fen, d
        moves = []
        for m in d.get("moves", []):
            moves.append({"uci": m.get("uci", None), "score": m.get("score", None)})
        return fen, {"moves": moves}


async def main():
    parser = argparse.ArgumentParser(
        description="A simple script to request json data from chessdb.cn for a list of FENs stored in a file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input", help="source filename with FENs (w/ or w/o move counters)"
    )
    parser.add_argument("output", nargs="?", help="optional destination filename")
    parser.add_argument(
        "--retainAll",
        action="store_true",
        help="Store the full json data from cdb (by default only uci moves and their scores).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all unnecessary output to the screen.",
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
        help="Number of FENs processed in parallel. Small values guarantee more responsive output, large values give faster turnaround.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "-u",
        "--user",
        help="Add this username to the http user-agent header.",
    )
    args = parser.parse_args()

    c2j = cdb2json(
        args.input,
        args.output,
        args.retainAll,
        args.quiet,
        args.concurrency,
        args.user,
    )

    await c2j.parse_all(args.batchSize)


if __name__ == "__main__":
    asyncio.run(main())

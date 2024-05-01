"""
   Script to get (clear) best moves for FENs from chessdb.cn.
"""
import argparse, asyncio, sys, time, cdblib


class cdb2bm:
    def __init__(self, filename, output, gap, drawGap, quiet, concurrency, user):
        self.input = filename
        self.lines = []
        self.loaded = 0
        with cdblib.open_file_rt(filename) as f:
            for line in f:
                line = line.strip()
                if line:
                    self.lines.append(line)
                    if not line.startswith("#"):  # ignore comments
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
        self.gap = gap
        self.drawGap = drawGap
        self.concurrency = concurrency
        self.cdb = cdblib.cdbAPI(concurrency, user)
        self.filtered = cdblib.AtomicInteger()

    def best_move(self, movelist):
        length = len(movelist)
        if length == 0:
            return None, ""
        best = movelist[0]
        if "score" not in best or type(best["score"]) != int:
            return None, ""
        score = best["score"]
        second = movelist[1] if length >= 2 else None
        if (
            length == 1
            or second is None
            or "score" not in second
            or type(second["score"]) != int
        ):
            return best["san"], f"cdb eval: {score}"
        gap = score - second["score"]
        if (score == 0 and gap < self.drawGap) or (score and gap < self.gap):
            return None, ""
        return (
            best["san"],
            f"cdb eval: {score} (sbm: {second['san']}, {second['score']})",
        )

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
        for i in range(0, len(self.lines), batchSize):
            tasks = []
            for line in self.lines[i : i + batchSize]:
                tasks.append(asyncio.create_task(self.parse_single_line(line)))

            for parse_line in tasks:
                l = await parse_line
                if l:
                    print(l, file=self.output)

        if self.display:
            elapsed = time.time() - self.tic
            print(
                f"Done. Processed {self.loaded} FENs in {elapsed:.1f}s.",
                file=self.display,
            )
            print(
                f"Filtered {self.filtered.get()} positions with bm output.",
                file=self.display,
            )

    async def parse_single_line(self, line):
        if line.startswith("#"):  # ignore comments
            return line
        fen = " ".join(line.split()[:4])  # cdb ignores move counters anyway
        r = await self.cdb.queryall(fen)
        bm, s = self.best_move(r["moves"]) if "moves" in r else (None, "")
        if bm:
            self.filtered.inc()
        return f'{fen} bm {bm}; c0 "{s}";' if bm else ""


async def main():
    parser = argparse.ArgumentParser(
        description='A simple script to request (clear) best moves from chessdb.cn for a list of FENs stored in a file. The script will output "{fen} bm {bm}; c0 {comment};" for every line containing a FEN with a clear best move on cdb. Lines beginning with "#" are ignored.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input", help="source filename with FENs (w/ or w/o move counters)"
    )
    parser.add_argument("output", nargs="?", help="optional destination filename")
    parser.add_argument(
        "--gap",
        help="Necessary gap between best move and second best move.",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--drawGap",
        help="Necessary gap between 0cp best move and second best move. (Default: max(GAP // 2, 1))",
        type=int,
        default=None,
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

    if args.drawGap is None:
        args.drawGap = max(args.gap // 2, 1)

    c2b = cdb2bm(
        args.input,
        args.output,
        args.gap,
        args.drawGap,
        args.quiet,
        args.concurrency,
        args.user,
    )

    await c2b.parse_all(args.batchSize)


if __name__ == "__main__":
    asyncio.run(main())

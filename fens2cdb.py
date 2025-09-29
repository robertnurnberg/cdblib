"""
   Script to bulk-evaluate FENs with chessdb.cn.
"""
import argparse, asyncio, sys, time, cdblib


class fens2cdb:
    def __init__(
        self,
        filename,
        output,
        shortFormat,
        quiet,
        enqueue,
        concurrency,
        user,
        suppressErrors,
    ):
        self.input = filename
        self.lines = []
        self.scored = 0
        with cdblib.open_file_rt(filename) as f:
            for line in f:
                line = line.strip()
                if line:
                    self.lines.append(line)
                    if not line.startswith("#"):  # ignore comments
                        self.scored += 1
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
                f"Read {self.scored} FENs from file {self.input}.",
                file=self.display,
                flush=True,
            )
        self.shortFormat = shortFormat
        self.enqueue = enqueue
        self.concurrency = concurrency
        self.cdb = cdblib.cdbAPI(concurrency, user, not suppressErrors)
        self.unknown = cdblib.AtomicInteger()

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
                print(await parse_line, file=self.output)

        if self.display:
            elapsed = time.time() - self.tic
            print(
                f"Done. Scored {self.scored} FENs in {elapsed:.1f}s.", file=self.display
            )
            if self.unknown.get():
                print(
                    f"The file {self.input} contained {self.unknown.get()} new chessdb.cn positions.",
                    file=self.display,
                )
                if self.enqueue == 0:
                    print(
                        "Rerunning the script after a short break should provide their evals.",
                        file=self.display,
                    )
                elif self.enqueue == 1:
                    print(
                        "They have now been queued for analysis.",
                        file=self.display,
                    )
                elif self.enqueue >= 2:
                    print(
                        "They have been queued for analysis, and their evals have been obtained.",
                        file=self.display,
                    )

    async def parse_single_line(self, line):
        if line.startswith("#"):  # ignore comments
            return line
        fen = " ".join(line.split()[:4])  # cdb ignores move counters anyway
        r = await (
            self.cdb.queryscore(fen) if self.enqueue >= 0 else self.cdb.readscore(fen)
        )
        score = cdblib.json2eval(r)
        if r.get("status") == "unknown" and score == "":
            self.unknown.inc()
            timeout = 5
            while self.enqueue >= 1 and r["status"] == "unknown":
                r = await self.cdb.queue(fen)
                if self.enqueue >= 2:
                    await asyncio.sleep(timeout)
                    r = await self.cdb.queryscore(fen)
                    score = cdblib.json2eval(r)
                    if timeout < 120:
                        timeout = min(timeout * 1.5, 120)
        if score == "":
            return line
        if self.shortFormat:
            if score == "mated":
                score = "#"
            elif type(score) != int:
                _, M, ply = score.partition("M")
                if M == "" or not ply.isnumeric():
                    score = ""
        else:
            if "ply" in r:
                score = f"{score}, ply: {r['ply']}"
            score = f"cdb eval: {score}"
        return f"{line}{' ;' if line[-1] != ';' else ''} {score};"


async def main():
    parser = argparse.ArgumentParser(
        description='A simple script to request evals from chessdb.cn for a list of FENs stored in a file. The script will add "; EVALSTRING;" to every line containing a FEN. Lines beginning with "#" are ignored, as well as any text after the first four fields of each FEN.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input", help="source filename with FENs (w/ or w/o move counters)"
    )
    parser.add_argument("output", nargs="?", help="optional destination filename")
    parser.add_argument(
        "--shortFormat",
        action="store_true",
        help='EVALSTRING will be just a number, or an "M"-ply mate score, or "#" for checkmate, or "".',
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress all unnecessary output to the screen.",
    )
    parser.add_argument(
        "-e",
        "--enqueue",
        action="count",
        default=0,
        help="-e queues unknown positions once, -ee until an eval comes back.",
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
    parser.add_argument(
        "-s",
        "--suppressErrors",
        action="store_true",
        help="Suppress error messages from cdblib.",
    )
    parser.add_argument(
        "--suppressLearning",
        action="store_true",
        help="Suppress cdb's automatic learning.",
    )
    args = parser.parse_args()

    if args.suppressLearning:
        if args.enqueue:
            print(
                "Options --suppressLearning and --enqueue are exclusive.",
                file=sys.stderr,
            )
            quit()
        args.enqueue = -1

    f2c = fens2cdb(
        args.input,
        args.output,
        args.shortFormat,
        args.quiet,
        args.enqueue,
        args.concurrency,
        args.user,
        args.suppressErrors,
    )

    await f2c.parse_all(args.batchSize)


if __name__ == "__main__":
    asyncio.run(main())

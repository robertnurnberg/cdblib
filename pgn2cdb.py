"""
   Script that sends the first --depth plies of games in a PGN file to cdb at
   chessdb.cn. Use local cache to reduce API requests for large PGN files.
"""
import argparse, asyncio, time, chess, chess.pgn, cdblib


class dbcache:
    # local cache for cdbAPI responses that avoids duplicate queries to API
    def __init__(self, concurrency, user=False):
        self.cdbAPI = cdblib.cdbAPI(concurrency, user)
        self.cache = cdblib.AtomicDict()
        self.req_received = cdblib.AtomicInteger()
        self.req_cached = cdblib.AtomicInteger()
        self.queued = cdblib.AtomicInteger()

    async def get(self, fen):
        """queryscore from API, use cached result if possible"""
        self.req_received.inc()
        r = self.cache.get(fen)
        if r is not None:
            self.req_cached.inc()
        else:
            # returns dictionary with keys "status", "eval" and possibly "ply"
            r = await self.cdbAPI.queryscore(fen)
            self.cache.set(fen, r)
        return r

    async def queue(self, fen):
        """queue fen via API, add entry to cache as well"""
        asyncio.ensure_future(self.cdbAPI.queue(fen))
        self.queued.inc()
        self.cache.set(fen, {"status": "ok"})  # assume fen is in cdb from now on


class pgn2cdb:
    def __init__(self, filename, verbose, depth, paint, concurrency, user):
        self.filename = filename
        self.verbose = verbose
        self.depth = depth
        self.paint = min(paint, depth)
        self.concurrency = concurrency
        pgn = open(self.filename)
        self.gamelist = []
        while game := chess.pgn.read_game(pgn):
            self.gamelist.append(game)
        self.gn = len(self.gamelist)
        print(f"Read {self.gn} pgns from file {self.filename}.")
        self.db = dbcache(self.concurrency, user)
        self.seen = cdblib.AtomicInteger()
        self.painted = cdblib.AtomicInteger()

    async def parse_all(self, batchSize=None):
        print(
            f"Started to parse these to chessdb.cn to depth {self.depth} with concurrency {self.concurrency}"
            + (" ..." if batchSize == None else f" and batch size {batchSize} ..."),
        )
        if batchSize is None:
            batchSize = len(self.gamelist)
        self.tic = time.time()
        for i in reversed(range(0, self.gn, batchSize)):
            tasks = []
            for lineIdx in reversed(range(i, min(i + batchSize, self.gn))):
                tasks.append(asyncio.create_task(self.parse_single_line(lineIdx)))

            for parse_line in tasks:
                p = await parse_line
                if p:
                    print(p, end="")

        elapsed = time.time() - self.tic
        print(
            f"Done processing {self.filename} to depth {self.depth} in {elapsed:.1f}s.",
        )
        s = self.seen.get()
        q = self.db.queued.get()
        c = self.db.req_cached.get()
        r = self.db.req_received.get()
        print(
            f"{s}/{self.gn} final positions already in chessdb.cn. ({s/self.gn*100:.2f}%)"
        )
        print(
            f"Queued {q} new positions to chessdb.cn. Local cache hit rate: {c}/{r} = {c/r*100:.2f}%."
        )
        if self.paint:
            p = self.painted.get()
            if p:
                print(
                    f"Painted {p} positions to help extend the starting position's connected component to depth {self.paint}."
                )
            else:
                print(
                    f"All lines are already in starting position's connected component to depth {self.paint}."
                )

    async def parse_single_line(self, lineIdx):
        line = self.gamelist[lineIdx]
        board = line.board()
        retStr = ""
        if self.verbose >= 4:
            retStr += f"    pgn {lineIdx+1}/{self.gn}: {str(line.mainline_moves())}\n"
        plies, pc = 0, 32
        for move in line.mainline_moves():
            if self.verbose >= 3:
                retStr += (
                    f"    pgn {lineIdx+1}/{self.gn}, ply {plies+1:3d}: {str(move)}\n"
                )
            board.push(move)
            plies += 1
            pc = 64 - str(board).count(".")  # count pieces left on the board
            if plies >= self.depth or pc <= 7:
                break  # cdb only stores pos if >= 8
        if self.verbose:
            retStr += f"  For pgn {lineIdx+1}/{self.gn} read {plies}/{self.depth} plies. Final position has {pc} pieces.\n"

        if plies == 0:
            return retStr  # some pgn's include empty games
        if board.is_checkmate() or board.is_stalemate() or pc <= 7:
            # mates, stalemates and 7men are not stored as nodes on chessdb.cn
            if self.verbose:
                if board.is_checkmate() or board.is_stalemate():
                    retStr += (
                        f"    Position at depth {plies} is checkmate or stalemate.\n"
                    )
                else:
                    retStr += f"    Position at depth {plies} is in 7men EGTB.\n"
            board.pop()
            plies -= 1
        r = await self.db.get(board.epd())
        cdbply = r.get("ply", -1)
        if r["status"] == "ok":
            self.seen.inc()
            if self.verbose:
                retStr += f"    Position at depth {plies} is already in chessdb.cn" + (
                    f", with distance {cdbply} from root.\n"
                    if cdbply != -1
                    else ", not yet connected to root.\n"
                )
        elif r["status"] == "unknown":
            if self.verbose:
                retStr += f"    Position at depth {plies} is new to chessdb.cn.\n"
        new_fens, finalply, poppedMoves = False, plies, []
        # now walk back until we are connected to root
        while plies and (cdbply == -1 or cdbply > plies):
            if r["status"] == "unknown":
                if not new_fens and self.verbose >= 2:
                    retStr += f"    Queueing new positions from ply {plies} ... \n"
                asyncio.ensure_future(self.db.queue(board.epd()))
                new_fens = True
            elif new_fens:
                if self.verbose >= 2:
                    retStr += f"    Queued new positions until ply {plies+1}.\n"
                new_fens = False
            move = board.pop()
            poppedMoves.append(move)
            r = await self.db.get(board.epd())
            cdbply = r.get("ply", -1)
            plies -= 1
            if self.verbose >= 4:
                retStr += f"      plies = {plies}, cdbply = {cdbply}.\n"
        if new_fens and self.verbose >= 2:
            retStr += f"    Queued new positions until ply {plies+1}.\n"
        if cdbply > -1 and plies < finalply:
            if self.verbose:
                retStr += f"    Position at depth {plies} is connected to the root, with distance {cdbply}.\n"
            paintTo = min(self.paint, finalply)
            if paintTo > plies:
                if self.verbose:
                    retStr += f"    Finally painting positions to depth {paintTo}.\n"
                for move in reversed(poppedMoves):
                    if self.verbose >= 3:
                        retStr += f"    pgn {lineIdx+1}/{self.gn}, ply {plies+1:3d}: {str(move)}\n"
                    board.push(move)
                    await self.db.cdbAPI.queryscore(board.epd())
                    self.painted.inc()
                    plies += 1
                    if plies >= paintTo:
                        break
        return retStr


async def main():
    parser = argparse.ArgumentParser(
        description="A simple script to pass pgns to chessdb.cn.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("filename", help="pgn file")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase output with -v, -vv, -vvv etc.",
    )
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=30,
        help="number of plies to be added to chessdb.cn",
    )
    parser.add_argument(
        "-p",
        "--paint",
        type=int,
        default=0,
        help="depth in plies to try to extend the root's connected component to in each line",
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
        help="username for the http user-agent header",
    )
    args = parser.parse_args()
    p2c = pgn2cdb(
        args.filename,
        args.verbose,
        args.depth,
        args.paint,
        args.concurrency,
        args.user,
    )
    await p2c.parse_all(args.batchSize)


if __name__ == "__main__":
    asyncio.run(main())

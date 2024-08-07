import argparse, asyncio, sys, time, cdblib, chess

VERSION = "cdb2uci engine 0.95"
VALUE_MATE = 30000
VALUE_TBWIN = 25000


def score2mate(score):
    if score > 0:
        return (VALUE_MATE - score + 1) // 2
    if score < 0:
        return -(VALUE_MATE + score) // 2
    return None


class Engine:
    def __init__(self, args):
        self.cdb = cdblib.cdbAPI(
            concurrency=args.concurrency, user=VERSION, showErrors=False
        )
        print(VERSION, flush=True)
        self.enqueue = args.enqueue
        self.multipv = args.MultiPV
        self.querypv = args.QueryPV
        self.debug = args.debug
        self.parse_epd("fen " + args.epd)
        self.go_task = None

    async def query_cdb_for_movelist(self):
        if self.debug:
            print(f"info string Querying cdb for FEN {self.board.epd()}", flush=True)
        r = await self.cdb.showall(self.board.epd())
        if self.debug:
            print(f"info string Obtained result {r}", flush=True)
        while "status" not in r or "moves" not in r or r["status"] != "ok":
            await asyncio.sleep(1)
            if self.debug:
                print(
                    f"info string Re-querying cdb for FEN {self.board.epd()}",
                    flush=True,
                )
            r = await self.cdb.showall(self.board.epd())
            if self.debug:
                print(f"info string Obtained result {r}", flush=True)
            print(
                f"info string Got response with status {r.get('status')} from cdb.",
                flush=True,
            )
        movelist = []
        can_claim_draw = False
        for m in r["moves"]:
            move, score = m["uci"], (m["score"] if type(m["score"]) == int else None)
            if score and score > 0:
                self.board.push_uci(move)
                if (
                    self.board.is_stalemate()
                    or self.board.is_insufficient_material()
                    or self.board.can_claim_draw()
                ):
                    if self.debug:
                        print(
                            f"info string After move {move} opponent can claim draw, so change score from {score} to 0.",
                            flush=True,
                        )
                    can_claim_draw = True
                    score = 0
                self.board.pop()
            movelist.append([move, score])
        # if scores were changed, sort movelist stably, non-None scores first
        if can_claim_draw:
            movelist.sort(key=lambda m: (float("inf") if m[1] is None else -m[1]))
        for m in movelist:
            score = m[1]
            if score is None:
                continue
            if abs(score) > VALUE_TBWIN:
                m[1] = f"mate {score2mate(score)}"
            else:
                m[1] = f"cp {score}"
        return movelist

    async def get_movelist(self, tb_with_cr):
        movelist = await self.query_cdb_for_movelist()
        while not tb_with_cr and self.enqueue and movelist[0][1] is None:
            if self.debug:
                print(f"info string Queueing FEN {self.board.epd()}", flush=True)
            await self.cdb.queue(self.board.epd())
            if self.enqueue < 2:
                break
            await asyncio.sleep(1)
            movelist = await self.query_cdb_for_movelist()
        return movelist

    async def go(self):
        tic = time.time()
        tb_with_cr = (
            chess.popcount(self.board.occupied) <= 7 and self.board.castling_rights
        )
        r = await self.get_movelist(tb_with_cr)
        if tb_with_cr:
            depth = nodes = 0
            r[0][1] = "cp 0"
            print(
                f"info string Probed 7men position with castling rights: eval and bestmove will be unreliable."
            )
        else:
            depth = int(r[0][1] is not None)
            nodes = 0
            for i in range(len(r)):
                if r[i][1] is None:
                    r[i][1] = "cp 0"
                else:
                    nodes += 1
        elapsed = round(1000 * (time.time() - tic))
        nps = round(1000 * nodes / max(1, elapsed))
        multipv = min(self.multipv, max(nodes, 1))
        tasks = []
        for i in range(multipv):
            print(
                f"info depth {depth} seldepth {depth} multipv {i+1} score {r[i][1]} time {elapsed} nodes {nodes} nps {nps} pv {r[i][0]}",
                flush=True,
            )
            if self.querypv:
                self.board.push_uci(r[i][0])
                tasks.append(
                    asyncio.create_task(self.cdb.querypvstable(self.board.epd())),
                )
                self.board.pop()
        for idx, query in enumerate(tasks):
            q = await query
            pv = cdblib.json2pv(q)
            if pv:
                nodes += pv.count(" ") + 1
                elapsed = round(1000 * (time.time() - tic))
                nps = round(1000 * nodes / max(1, elapsed))
            print(
                f"info depth {depth} seldepth {depth} multipv {idx+1} score {r[idx][1]} time {elapsed} nodes {nodes} nps {nps} pv {r[idx][0]} {pv}",
                flush=True,
            )
        print(f"bestmove {r[0][0]}", flush=True)

    def parse_epd(self, epd):
        parts = epd.split()
        index = parts.index("moves") if "moves" in parts else 0
        if parts[0] == "startpos":
            fen = chess.STARTING_FEN
        else:
            fen_end = min(index if index else 7, 7)
            fen = " ".join(parts[1:fen_end])
        self.board = chess.Board(fen)
        for m in parts[index + 1 :] if index else []:
            self.board.push_uci(m)

    async def UCIinterface(self):
        while True:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "quit":
                if self.go_task:
                    self.go_task.cancel()
                break
            elif parts[0] == "stop":
                if self.go_task:
                    self.go_task.cancel()
            elif parts[0] == "uci":
                print(f"id name {VERSION}\nid author Noob, really.\n")
                print(
                    "option name MultiPV type spin default 1 min 1 max 256",
                )
                print(
                    "option name Enqueue type spin default 0 min 0 max 2",
                )
                print("option name QueryPV type check default false\nuciok", flush=True)
            elif parts[0] == "debug":
                if len(parts) > 1:
                    self.debug = bool(parts[1].lower() == "on")
            elif parts[0] == "setoption":
                if len(parts) > 4 and parts[2] == "MultiPV":
                    self.multipv = int(parts[4])
                if len(parts) > 4 and parts[2] == "Enqueue":
                    self.enqueue = int(parts[4])
                elif len(parts) > 4 and parts[2] == "QueryPV":
                    self.querypv = bool(parts[4].lower() == "true")
            elif parts[0] == "ucinewgame":
                self.board = chess.Board()
            elif parts[0] == "isready":
                print("readyok", flush=True)
            elif parts[0] == "position" and len(parts) > 1:
                self.parse_epd(" ".join(parts[1:]))
            elif parts[0] == "d":
                print(self.board, flush=True)
            elif parts[0] == "go":
                if self.go_task:
                    self.go_task.cancel()
                if bool(self.board.legal_moves):
                    self.go_task = asyncio.create_task(self.go())


async def main():
    parser = argparse.ArgumentParser(
        description="A simple UCI engine that only queries chessdb.cn. On successful probing of a position it will report depth 1, otherwise depth 0 and score cp 0. For go commands any limits (including time) will be ignored. The https://backscattering.de/chess/uci for details on the UCI protocol.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-e",
        "--enqueue",
        action="count",
        default=0,
        help="-e queues unknown positions once, -ee until an eval comes back. The latter may be desirable in engine vs engine matches.",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        help="Maximum concurrency of requests to cdb. Values > 1 are meaningful only if QueryPV is True and MultiPV > 1.",
        type=int,
        default=8,
    )
    parser.add_argument(
        "--epd",
        help="Extended EPD of board on engine start-up.",
        default=chess.STARTING_FEN,
    )
    parser.add_argument(
        "--MultiPV",
        help="Value of UCI option MultiPV on engine start-up.",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--QueryPV",
        action="store_true",
        help="Value of UCI option QueryPV on engine start-up.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run in debug mode (with additional output).",
    )
    args = parser.parse_args()

    engine = Engine(args)
    await engine.UCIinterface()


if __name__ == "__main__":
    asyncio.run(main())

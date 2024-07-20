import argparse, asyncio, sys, time, cdblib, chess

VERSION = "cdb2uci engine 0.2"
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
        self.board = chess.Board()
        self.multipv = args.MultiPV
        self.querypv = args.QueryPV

    async def go(self):
        r = await self.cdb.showall(self.board.epd())
        while "status" not in r or "moves" not in r or r["status"] != "ok":
            await asyncio.sleep(1)
            r = await self.cdb.showall(self.board.epd())
            print(
                f"info string Got response with status {r.get('status')} from cdb.",
                flush=True,
            )
        movelist = []
        for m in r["moves"]:
            score = m["score"]
            if type(score) == int:
                if score > VALUE_TBWIN:
                    score = f"mate {score2mate(score)}"
                else:
                    score = f"cp {score}"
            else:
                score = None
            movelist.append([m["uci"], score])
        if movelist[0][1] is None:
            asyncio.ensure_future(self.cdb.queue(self.board.epd()))
        return movelist

    async def UCIinterface(self):
        for line in sys.stdin:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "quit":
                break
            elif parts[0] == "uci":
                print(f"id name {VERSION}\nid author Noob, really.\n")
                print(
                    "option name MultiPV type spin default 1 min 1 max 256",
                )
                print("option name QueryPV type check default false\nuciok", flush=True)
            elif parts[0] == "setoption":
                if len(parts) > 4 and parts[2] == "MultiPV":
                    self.multipv = int(parts[4])
                elif len(parts) > 4 and parts[2] == "QueryPV":
                    self.querypv = bool(parts[4].lower() == "true")
            elif parts[0] == "ucinewgame":
                self.board = chess.Board()
            elif parts[0] == "isready":
                print("readyok", flush=True)
            elif parts[0] == "position" and len(parts) > 1:
                index = parts.index("moves") if "moves" in parts else 0
                if parts[1] == "startpos":
                    fen = chess.STARTING_FEN
                else:
                    fen_end = min(index if index else 8, 8)
                    fen = " ".join(parts[2:fen_end])
                self.board = chess.Board(fen)
                for m in parts[index + 1 :] if index else []:
                    self.board.push_uci(m)
            elif parts[0] == "d":
                print(self.board, flush=True)
            elif parts[0] == "go":
                if not bool(self.board.legal_moves):
                    continue
                tic = time.time()
                r = await self.go()
                if (
                    chess.popcount(self.board.occupied) <= 7
                    and self.board.castling_rights
                ):
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
                            asyncio.create_task(
                                self.cdb.querypvstable(self.board.epd())
                            ),
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


async def main():
    parser = argparse.ArgumentParser(
        description="A simple UCI engine that only queries chessdb.cn. On successful probing of a position it will report depth 1, otherwise depth 0 and score 0 cp. For go commands any limits (including time) will be ignored.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        help="Maximum concurrency of requests to cdb. Values > 1 meaningful only if QueryPV is True and MultiPV > 1.",
        type=int,
        default=8,
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
    args = parser.parse_args()

    engine = Engine(args)
    await engine.UCIinterface()


if __name__ == "__main__":
    asyncio.run(main())

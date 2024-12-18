"""
   Script to monitor a position's PV on chessdb.cn at regular intervals.
"""
import argparse, asyncio, time, cdblib
from datetime import datetime


async def main():
    parser = argparse.ArgumentParser(
        description="Monitor dynamic changes in a position's PV on chessdb.cn by polling it at regular intervals.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--epd",
        help="FEN/EPD of the position to monitor.",
        default="rnbqkbnr/pppppppp/8/8/6P1/8/PPPPPP1P/RNBQKBNR b KQkq -",
    )
    parser.add_argument(
        "--stable", action="store_true", help='Pass "&stable=1" option to the API.'
    )
    parser.add_argument(
        "--sleep",
        type=int,
        default=3600,
        help="Time interval between polling requests in seconds.",
    )
    parser.add_argument(
        "--san", action="store_true", help="Give PV in short algebraic notation (SAN)."
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
    args = parser.parse_args()

    cdb = cdblib.cdbAPI(
        concurrency=1, user=args.user, showErrors=not args.suppressErrors
    )
    q = await cdb.queryscore(args.epd)
    s = q.get("status")
    if s != "ok" and s != "unknown":
        print("  It is imposssible to obtain a valid PV for the given position.")
        quit()

    while True:
        r = await (
            cdb.querypvstable(args.epd) if args.stable else cdb.querypv(args.epd)
        )
        pv = cdblib.json2pv(r, san=args.san)
        e = cdblib.json2eval(r)
        if type(e) == int:
            e = f"{e:4d}cp"
        else:
            e = " " * max(0, 6 - len(e)) + e
        print(f"  {datetime.now().isoformat()}: {e} -- {pv}")
        print("", flush=True)
        if args.sleep == 0:
            break
        time.sleep(args.sleep)


if __name__ == "__main__":
    asyncio.run(main())

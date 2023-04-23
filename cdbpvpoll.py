"""
   Script to monitor a position's PV on chessdb.cn at regular intervals.
"""
import argparse, time, cdblib
from datetime import datetime

parser = argparse.ArgumentParser(
    description="Monitor dynamic changes in a position's PV on chessdb.cn by polling it at regular intervals.",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("--epd", help="FEN/EPD of the position to monitor",
    default="rnbqkbnr/pppppppp/8/8/6P1/8/PPPPPP1P/RNBQKBNR b KQkq g3")
parser.add_argument('-s', '--sleep', type=int, default=3600,
    help = "time interval between polling requests in seconds")
parser.add_argument('--san', action="store_true",
    help = "give PV in short algebraic notation (SAN)")
args = parser.parse_args()

cdb = cdblib.cdbAPI()
s = cdb.queryscore(args.epd).get("status")
if s != "ok" and s != "unknown":
    print("  It is imposssible to obtain a valid PV for the given position.")
    quit()

while True:
    r = cdb.querypv(args.epd)
    pv = cdblib.json2pv(r, san=args.san)
    e = cdblib.json2eval(r)
    e = "      " if e == "" else f"{e:4d}cp"
    print(f"  {datetime.now().isoformat()}: {e} -- {pv}")
    print("", flush=True)
    time.sleep(args.sleep)

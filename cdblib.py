"""
   Wrapper functions to conveniently access chessdb.cn from within Python.
   Heavily based on Joost VandeVondele's https://github.com/vondele/cdbexplore
   See API documentation at https://www.chessdb.cn/cloudbookc_api_en.html
"""
import requests, time
from datetime import datetime


class cdbAPI:
    def __init__(self, user=None):
        # use a session to keep alive the connection to the server
        self.session = requests.Session()
        self.user = "" if user is None else str(user)

    def __apicall(self, url, timeout):
        try:
            response = self.session.get(
                url,
                timeout=timeout,
                headers={"user-agent": "cdblib" + bool(self.user) * "/" + self.user},
            )
            response.raise_for_status()
            content = response.json()
        except Exception:
            content = None
        return content

    def generic_call(self, action, fen, optionString=""):
        # action can be: "queryall", "querybest", "query", "querysearch", "queryscore", "querypv", "queue"
        # returns dict from API call to chessdb.cn with "status" guaranteed to be one of: "ok", "checkmate", "stalemate", "unknown", "nobestmove", "invalid board"
        api = "http://www.chessdb.cn/cdb.php"
        timeout = 5
        success = False
        first = True
        lasterror = ""

        while not success:
            # sleep a bit before further requests
            if not first:
                # adjust timeout increasing after every attempt, up to a max.
                if timeout < 60:
                    timeout = timeout * 1.5
                else:
                    print(
                        datetime.now().isoformat(),
                        " - failed to get reply for : ",
                        fen,
                        " last error: ",
                        lasterror,
                        flush=True,
                    )
                time.sleep(timeout)
            else:
                first = False

            url = api + f"?action={action}&board={fen}{optionString}&json=1"
            content = self.__apicall(url, timeout)

            if content is None:
                lasterror = f"Something went wrong with {action}{optionString}"
                continue

            elif action == "queue" and content == {}:
                # empty dict is returned for mates and stalemates
                content = {"status": "ok"}
                lasterror = "Enqueued position"
                success = True

            elif "status" not in content:
                lasterror = "Malformed reply, not containing status"
                continue

            elif content["status"] == "invalid board":
                # nothing to be done, bail out and return to caller
                lasterror = "Invalid board"
                success = True

            elif content["status"] == "rate limit exceeded":
                # special case, request to clear the limit
                url = api + "?action=clearlimit"
                self.__apicall(url, timeout)
                lasterror = "asked to clearlimit"
                continue

            elif content["status"] == "unknown":
                lasterror = "queried an unknown position"
                success = True

            elif content["status"] == "nobestmove":
                lasterror = "asked for move in mate/stalemate/unknown position"
                success = True

            elif content["status"] == "ok":
                if (
                    (action == "queryall" and "moves" not in content)
                    or (
                        action == "querybest"
                        and "move" not in content
                        and "search_moves" not in content
                        and "egtb" not in content
                    )
                    or (
                        action == "query"
                        and "move" not in content
                        and "search_moves" not in content
                        and "egtb" not in content
                    )
                    or (
                        action == "querysearch"
                        and "search_moves" not in content
                        and "egtb" not in content
                    )
                    or (action == "queryscore" and "eval" not in content)
                    or (
                        action == "querypv"
                        and (
                            "score" not in content
                            or "depth" not in content
                            or "pv" not in content
                            or "pvSAN" not in content
                        )
                    )
                ):
                    lasterror = "Unexpectedly missing keys"
                    continue
                else:
                    success = True

            elif content["status"] == "checkmate" or content["status"] == "stalemate":
                success = True

            else:
                lasterror = f"Surprise reply with status = {content['status']}"
                continue

        content["fen"] = fen  # add "fen" key to dict, used e.g. for PV SAN
        return content

    def queryall(self, fen):
        # returns dict with keys "status", "moves" and "ply" where "moves" is a sorted list of dict's with keys "uci", "san", "score", "rank", "note" and "winrate" (sorted by eval and rank)
        return self.generic_call("queryall", fen)

    def showall(self, fen):
        # same as querall, but returns _all_ possible moves, with "??" for score of unscored moves
        return self.generic_call("queryall", fen, "&showall=1")

    def querybest(self, fen):
        # returns one of the rank == 2 moves in a dict with keys "status" and either "move", "search_moves or "egtb"
        # also triggers automatic back-propagation on cdb
        return self.generic_call("querybest", fen)

    def query(self, fen):
        # returns one of the rank > 0 moves in a dict with keys "status" and either "move", "search_moves or "egtb"
        # also triggers automatic back-propagation on cdb
        return self.generic_call("query", fen)

    def querysearch(self, fen):
        # returns all of the rank > 0 moves in a dict with keys "status" and either "search_moves" or "egtb"
        return self.generic_call("querysearch", fen)

    def queryscore(self, fen):
        # returns dict with keys "status", "eval", "ply"
        return self.generic_call("queryscore", fen)

    def querypv(self, fen):
        # returns dict with keys "status", "score", "depth", "pv", "pvSAN"
        # also triggers automatic back-propagation on cdb
        return self.generic_call("querypv", fen)

    def queue(self, fen):
        # returns dict with key "status"
        # also triggers automatic back-propagation on cdb
        return self.generic_call("queue", fen)


def json2eval(r):
    # turns a json response from the API into an evaluation, if possible
    # output: on success eval/score E as reported by cdb, otherwise "mated", "invalid", f"{pc}men w/ cr" or ""
    # E is either "??" or an integer E. in the latter case 30000-ply = mate in ply, 20000-ply cursed win in ply, 25000-ply tb win in ply
    if r is None:  # only needed for buggy json responses from cdb
        return "invalid json reply"
    if "status" not in r:
        return ""
    if r["status"] == "checkmate":
        return "mated"
    if r["status"] == "stalemate":
        return 0
    if r["status"] == "invalid board":
        return "invalid"
    s = ""
    if "moves" in r:
        s = r["moves"][0]["score"]
    elif "eval" in r:
        s = r["eval"]
    elif "score" in r:
        s = r["score"]
    if type(s) == int and abs(s) > 25000:
        ply = 30000 - abs(s)
        s = "" if s > 0 else "-"
        s += f"M{ply}"
    if (r["status"] == "unknown" or s == "??") and "fen" in r:
        # 7men TB positions with castling rights will never get an eval
        parts = r["fen"].split()
        pc = sum(p in "pnbrqk" for p in parts[0].lower())
        cf = len(parts) >= 3 and parts[2] != "-"
        if pc <= 7 and cf:
            return f"{pc}men w/ cr"
    if s == "??":
        s = ""
    return s


def json2pv(r, san=False, ply=None):
    # turns the PV from a json response from the API into a string
    # output: PV as a string, if possible, otherwise ""
    if r is None:  # only needed for buggy json responses from cdb
        return "invalid json reply"
    if "status" not in r:
        return ""
    if san:
        if "pvSAN" not in r:
            return ""
        if ply is not None or "fen" in r:
            if ply is None:
                _, _, side = r["fen"].partition(" ")  # side to move for numbering
                ply = 0 if side[0] == "w" else 1
            ply += 1
            s = f"{ply//2}..." if ply % 2 == 0 else ""
            for m in r["pvSAN"]:
                if ply % 2 == 1:
                    s += f"{(ply+1)//2}. "
                s += m + " "
                ply += 1
        else:  # without the fen we do not know if white or black to move
            s = " ".join(tuple(r["pvSAN"]))
        return s
    else:
        if "pv" not in r:
            return ""
        s = " ".join(tuple(r["pv"]))
        return s

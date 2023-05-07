"""
   Wrapper functions to conveniently access chessdb.cn from within Python.
   Heavily based on Joost VandeVondele's https://github.com/vondele/cdbexplore
   See API documentation at https://www.chessdb.cn/cloudbookc_api_en.html
"""
import requests, time
from datetime import datetime


class cdbAPI:
    def __init__(self):
        self.session = requests.Session()

    def __apicall(self, url, timeout):
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            content = response.json()
        except Exception:
            content = None
        return content

    def generic_call(self, action, fen):
        # action can be: "queryall", "querybest", "query", "querysearch",
        #                "queryscore", "querypv", "queue"
        # returns dict from API call to chessdb.cn with "status" guaranteed to
        # be one of: "ok", "checkmate", "stalemate", "unknown", "nobestmove",
        #            "invalid board"
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

            url = api + f"?action={action}&board={fen}&json=1"
            content = self.__apicall(url, timeout)

            if content is None:
                lasterror = f"Something went wrong with {action}"
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
                        and "egtb" not in content
                        and "search_moves" not in content
                    )
                    or (
                        action == "query"
                        and "move" not in content
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
        # returns dictionary with keys "status", "moves" and "ply" where
        # "moves" is a sorted list of dict's with keys "uci", "san", "score",
        # "rank", "note" and "winrate" (sorted by eval and rank)
        return self.generic_call("queryall", fen)

    def querybest(self, fen):
        # returns dictionary with keys "status" and either "move" or "egtb"
        return self.generic_call("querybest", fen)

    def query(self, fen):
        # returns dictionary with keys "status" and either "move" or "egtb"
        return self.generic_call("query", fen)

    def querysearch(self, fen):
        # returns dictionary with keys "status" and either "search_moves" or
        # "egtb"
        return self.generic_call("querysearch", fen)

    def queryscore(self, fen):
        # returns dictionary with keys "status", "eval", "ply"
        return self.generic_call("queryscore", fen)

    def querypv(self, fen):
        # returns dict with keys "status", "score", "depth", "pv", "pvSAN"
        return self.generic_call("querypv", fen)

    def queue(self, fen):
        # returns dict with key "status"
        return self.generic_call("queue", fen)


def json2eval(r):
    # turns a json response from the API into an evaluation, if possible
    # output: on success eval in cp as int, otherwise "mated", "invalid",
    #         f"{pc}men w/ castling" or ""
    if "status" not in r:
        return ""
    if r["status"] == "checkmate":
        return "mated"
    if r["status"] == "stalemate":
        return 0
    if r["status"] == "invalid board":
        return "invalid"
    if r["status"] == "unknown" and "fen" in r:
        # 7men TB positions with castling flags will never get an eval
        parts = r["fen"].split()
        pc = sum(p in "pnbrqk" for p in parts[0].lower())
        cf = len(parts) >= 3 and parts[2] != "-"
        if pc <= 7 and cf:
            return f"{pc}men w/ castling"
    if r["status"] != "ok":
        return ""
    if "moves" in r:
        return r["moves"][0]["score"]
    if "eval" in r:
        return r["eval"]
    if "score" in r:
        return r["score"]
    return ""


def json2pv(r, san=False):
    # turns the PV from a json response from the API into a string
    # output: PV as a string, if possible, otherwise ""
    if "status" not in r:
        return ""
    if san:
        if "pvSAN" not in r:
            return ""
        if "fen" in r:
            _, _, side = r["fen"].partition(" ")  # side to move for numbering
            if side[0] == "w":
                ply, s = 1, ""
            else:
                ply, s = 2, "1..."
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

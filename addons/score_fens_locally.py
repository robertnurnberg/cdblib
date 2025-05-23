import argparse, gzip, sys


def line2fen(line):
    line = line.strip()
    if line and not line.startswith("#"):
        fen = " ".join(line.split()[:4])
        return fen[:-1] if fen[-1] == ";" else fen
    return ""


def open_file(filename):
    open_func = gzip.open if filename.endswith(".gz") else open
    return open_func(filename, "rt")


def read_scores_from_epd_file(db, filename):
    with open_file(filename) as f:
        for line in f:
            fen = line2fen(line)
            if fen == "":
                continue
            line = line.strip()
            _, p, cdb = line.rpartition(" cdb eval: ")
            if not p:
                continue
            if "ply" in cdb:
                score, _, ply = cdb.partition(", ply: ")
                ply = int(ply[:-1])
            else:
                ply = None
            if cdb == "":
                continue
            if fen not in db or (
                ply is not None and (db[fen][1] is None or db[fen][1] > ply)
            ):
                db[fen] = (p + cdb, ply)


def main():
    parser = argparse.ArgumentParser(
        description="Score EPDs given in input with the the cdb evaluations stored locally in oracles. The scored EPDs will be written to stdout.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "input", help="The source .epd(.gz) file, with EPDs to be scored."
    )
    parser.add_argument(
        "oracles", nargs="*", help="List of epd(.gz) files with scored EPDs."
    )
    args = parser.parse_args()

    db = {}
    for file in args.oracles:
        print(f"Reading scored positions from {file} ...", file=sys.stderr)
        read_scores_from_epd_file(db, file)
        print(f"... done. DB size now at {len(db.keys())}.", file=sys.stderr)

    with open_file(args.input) as f:
        for line in f:
            fen = line2fen(line)
            line = line[:-1]  # remove the newline character
            if fen not in db or "; cdb eval: " in line:
                print(line)
            else:
                cdb, _ = db[fen]
                print(f"{line}{' ;' if line[-1] != ';' else ''}{cdb}")


if __name__ == "__main__":
    main()

import argparse, gzip, sys


def line2fen(line):
    line = line.strip()
    if line and not line.startswith("#"):
        fen = " ".join(line.split()[:4])
        return fen[:-1] if fen[-1] == ";" else fen
    return ""


def open_file_rt(filename):
    open_func = gzip.open if filename.endswith(".gz") else open
    return open_func(filename, "rt")


def read_epd_file(filename, positions=None):
    if positions is None:
        positions = set()
    with open_file_rt(filename) as f:
        for line in f:
            positions.add(line2fen(line))
    positions.discard("")
    return positions


def main():
    parser = argparse.ArgumentParser(
        description="Find proportion of unique EPDs in source that exist in the given list of references, and print lines in source with EPDs not found in the references to stdout (for duplicate EPDs only the first occurrence in source will be printed).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("source", help="The source .epd(.gz) file.")
    parser.add_argument(
        "references", nargs="*", help="List of reference .epd(.gz) files, may be empty."
    )
    parser.add_argument(
        "--saveMemory",
        action="store_true",
        help="Non functional if source contains no duplicate EPDs.",
    )
    parser.add_argument(
        "--noStats",
        action="store_true",
        help="Do not compute individual overlapping stats (saves memory).",
    )
    args = parser.parse_args()
    len_refs = len(args.references)
    stats = len_refs and not args.noStats

    all_others = set()
    if stats:
        positions = [read_epd_file(args.source)]

    for file in args.references:
        if stats:
            positions.append(read_epd_file(file))
            if len_refs == 1:  # save memory for single reference file
                all_others = positions[-1]
            else:
                all_others |= positions[-1]
        else:
            read_epd_file(file, all_others)

    if stats:
        print(
            f"{args.source} has {len(positions[0])} unique positions. Of these ...",
            file=sys.stderr,
        )
        l0 = len(positions[0])
        common = len(positions[0].intersection(all_others))
        l = len(all_others)
        p = common / max(l, 1) * 100
        p0 = common / l0 * 100
        print(
            f"{common} ({p0:.2f}%) are found within the {l} unique positions in all the reference files ({p:.2f}% overlap)",
            file=sys.stderr,
        )
        for i, file in enumerate(args.references):
            common = len(positions[0].intersection(positions[i + 1]))
            l = len(positions[i + 1])
            p = common / max(l, 1) * 100
            p0 = common / l0 * 100
            print(
                f"{common} ({p0:.2f}%) are found within the {l} unique positions in {file} ({p:.2f}% overlap)",
                file=sys.stderr,
            )

    count_total, count_saved = 0, 0
    with open_file_rt(args.source) as f:
        for line in f:
            fen = line2fen(line)
            if fen:
                count_total += 1
                if fen not in all_others:
                    count_saved += 1
                    print(line, end="")
                    if not args.saveMemory:
                        all_others |= {fen}
    print(
        f"Kept {count_saved} of the {count_total} positions in {args.source}. ({count_saved/count_total*100:.2f}%)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

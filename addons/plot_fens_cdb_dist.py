import argparse, gzip
import matplotlib.pyplot as plt
from collections import Counter


def open_file(filename):
    open_func = gzip.open if filename.endswith(".gz") else open
    return open_func(filename, "rt")


class data:
    def __init__(self, filename, debug=False):
        self.connected = 0
        self.evals = Counter()
        self.plies = Counter()
        self.plydiffs = Counter()
        with open_file(filename) as f:
            for line in f:
                line = line.strip()
                if line:
                    if line.startswith("#"):  # ignore comments
                        continue
                    fen, _, cdb = line.partition(" cdb eval: ")
                    if "ply" in cdb:
                        self.connected += 1
                        cdb, _, ply = cdb.partition(", ply: ")
                        ply = int(ply[:-1])
                        self.plies[ply] += 1
                        fields = fen.split()
                        if (
                            len(fields) >= 6
                            and fields[4].isdigit()
                            and fields[5].isdigit()
                        ):
                            move = int(fields[5])
                            p = (
                                (move - 1) * 2
                                if fields[1] == "w"
                                else (move - 1) * 2 + 1
                            )
                            self.plydiffs[ply - p] += 1
                    else:
                        cdb, _, _ = cdb.partition(";")
                    if cdb.lstrip("-").isnumeric():
                        e = int(cdb)
                    elif cdb.startswith("M"):
                        e = 30000 - int(cdb[1:])
                    elif cdb.startswith("-M"):
                        e = -30000 + int(cdb[2:])
                    self.evals[e] += 1
        self.filename = filename[:-3] if filename.endswith(".gz") else filename
        print(
            f"Loaded {sum(self.evals.values())} EPDs with evals in [{min(self.evals.keys())}, {max(self.evals.keys())}], {self.connected} of which are connected to root on cdb."
        )
        s = sum(key * count for key, count in self.plies.items())
        l = sum(self.plies.values())
        if l:
            print(
                f"{l} of the EPDs have ply in [{min(self.plies.keys())}, {max(self.plies.keys())}], average = {s/l:.2f}."
            )
        if debug:
            print("eval frequencies:", end=" ")
            eval_count = sorted(
                self.evals.items(), key=lambda t: abs(t[0]) + 0.5 * (t[0] < 0)
            )
            print(", ".join([f"{eval}: {frequency}" for eval, frequency in eval_count]))
            print("ply frequencies:", end=" ")
            ply_count = sorted(self.plies.items(), key=lambda x: x[0])
            print(", ".join([f"{ply}: {frequency}" for ply, frequency in ply_count]))

    def create_evalgraph(self, bucketSize=10, cutOff=200, absEval=False, density=True):
        evals = Counter()

        for e, freq in self.evals.items():
            e = min(abs(e), cutOff) if absEval else min(max(-cutOff, e), cutOff)

            evals[e] += freq
        rangeMin, rangeMax = min(evals.keys()), max(evals.keys())
        fig, ax = plt.subplots()
        if bucketSize == 1:
            bins = (rangeMax - rangeMin) + 1
        else:
            bins = (rangeMax - rangeMin) // bucketSize
        bin_edges = [rangeMin + i * bucketSize for i in range(bins + 1)]
        ax.hist(
            evals.keys(),
            weights=evals.values(),
            range=(rangeMin, rangeMax),
            bins=bin_edges,
            density=density,
            alpha=0.5,
            color="blue",
            edgecolor="black",
        )
        fig.suptitle(
            f"Eval distribution for {self.filename}.",
        )
        if min(self.evals.keys()) < -cutOff or max(self.evals.keys()) > cutOff:
            ax.set_title(
                f"(Evals outside of [-{cutOff},{cutOff}] are included in the {'' if absEval else '+/-'}{cutOff} bucket{'' if absEval else 's'}.)",
                fontsize=6,
                family="monospace",
            )
        prefix, _, _ = self.filename.rpartition(".")
        pgnname = prefix + ".png"
        plt.savefig(pgnname, dpi=300)
        print(f"Saved eval distribution plot in file {pgnname}.")

    def create_plygraph(self, bucketSize=2, cutOff=200, density=True):
        plies = Counter()
        for p, freq in self.plies.items():
            plies[min(p, cutOff)] += freq
        rangeMin, rangeMax = min(plies.keys()), max(plies.keys())
        fig, ax = plt.subplots()
        if bucketSize == 1:
            bins = (rangeMax - rangeMin) + 1
        else:
            bins = (rangeMax - rangeMin) // bucketSize
        bin_edges = [rangeMin + i * bucketSize for i in range(bins + 1)]
        ax.hist(
            plies.keys(),
            weights=plies.values(),
            range=(rangeMin, rangeMax),
            bins=bin_edges,
            density=density,
            alpha=0.5,
            color="blue",
            edgecolor="black",
        )
        fig.suptitle(
            f"min_ply distribution for {self.filename}.",
        )
        if max(self.plies.keys()) > cutOff:
            ax.set_title(
                f"(Ply values > {cutOff} are included in the {cutOff} bucket.)",
                fontsize=6,
                family="monospace",
            )
        prefix, _, _ = self.filename.rpartition(".")
        pgnname = prefix + "_ply.png"
        plt.savefig(pgnname, dpi=300)
        print(f"Saved min_ply distribution plot in file {pgnname}.")

    def create_plydiffgraph(self, bucketSize=2, density=True):
        rangeMin, rangeMax = min(self.plydiffs.keys()), max(self.plydiffs.keys())
        fig, ax = plt.subplots()
        if bucketSize == 1:
            bins = (rangeMax - rangeMin) + 1
        else:
            bins = (rangeMax - rangeMin) // bucketSize
        bin_edges = [rangeMin + i * bucketSize for i in range(bins + 1)]
        ax.hist(
            self.plydiffs.keys(),
            weights=self.plydiffs.values(),
            range=(rangeMin, rangeMax),
            bins=bin_edges,
            density=density,
            alpha=0.5,
            color="blue",
            edgecolor="black",
        )
        fig.suptitle(
            f"(cdb min_ply - true ply) distribution for {self.filename}.",
        )
        prefix, _, _ = self.filename.rpartition(".")
        pgnname = prefix + "_plydiff.png"
        plt.savefig(pgnname, dpi=300)
        print(f"Saved (cdb ply - true ply) distribution plot in file {pgnname}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Plot cdb eval and min_ply distribution for data stored in filename.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "filename",
        help=".epd(.gz) file with positions and their cdb evals.",
    )
    parser.add_argument(
        "-c",
        "--cutOff",
        help="Cutoff value for the eval distribution plot.",
        type=int,
        default=200,
    )
    parser.add_argument(
        "--absEval",
        action="store_true",
        help="Use absolute evals.",
    )
    parser.add_argument(
        "-b",
        "--bucket",
        type=int,
        default=10,
        help="bucket size for evals",
    )
    parser.add_argument(
        "-p",
        "--plyBucket",
        type=int,
        default=2,
        help="bucket size for min_ply",
    )
    parser.add_argument(
        "--plyCutOff",
        help="Cutoff value for the ply distribution plot.",
        type=int,
        default=60,
    )
    parser.add_argument(
        "--density",
        help="Plot density in histograms (or not).",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show frequency data on stdout.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase output with -v, -vv, -vvv etc.",
    )
    args = parser.parse_args()

    d = data(args.filename, args.debug)
    d.create_evalgraph(args.bucket, args.cutOff, args.absEval, args.density)
    if d.plies:
        d.create_plygraph(args.plyBucket, args.plyCutOff, args.density)
    if d.plydiffs:
        d.create_plydiffgraph(args.plyBucket, args.density)
        if args.verbose:
            print("cdb min_ply - true ply:")
            for k in sorted(d.plydiffs.keys()):
                print(f"{k}: {d.plydiffs[k]}")

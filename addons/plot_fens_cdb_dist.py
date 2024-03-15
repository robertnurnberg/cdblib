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
        with open_file(filename) as f:
            for line in f:
                line = line.strip()
                if line:
                    if line.startswith("#"):  # ignore comments
                        continue
                    _, _, cdb = line.partition(" cdb eval: ")
                    if "ply" in cdb:
                        self.connected += 1
                        cdb, _, ply = cdb.partition(", ply: ")
                        self.plies[int(ply[:-1])] += 1
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
        ax.hist(
            evals.keys(),
            weights=evals.values(),
            range=(rangeMin, rangeMax),
            bins=(rangeMax - rangeMin) // bucketSize,
            density=density,
            alpha=0.5,
            color="blue",
            edgecolor="black",
        )
        fig.suptitle(
            f"Eval distribution for {self.filename}.",
        )
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
        ax.hist(
            plies.keys(),
            weights=plies.values(),
            range=(rangeMin, rangeMax),
            bins=(rangeMax - rangeMin) // bucketSize,
            density=density,
            alpha=0.5,
            color="blue",
            edgecolor="black",
        )
        fig.suptitle(
            f"min_ply distribution for {self.filename}.",
        )
        ax.set_title(
            f"(Ply values > {cutOff} are included in the {cutOff} bucket.)",
            fontsize=6,
            family="monospace",
        )
        prefix, _, _ = self.filename.rpartition(".")
        pgnname = prefix + "_ply.png"
        plt.savefig(pgnname, dpi=300)
        print(f"Saved min_ply distribution plot in file {pgnname}.")


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
    args = parser.parse_args()

    d = data(args.filename, args.debug)
    d.create_evalgraph(args.bucket, args.cutOff, args.absEval, args.density)
    if d.plies:
        d.create_plygraph(args.plyBucket, args.plyCutOff, args.density)

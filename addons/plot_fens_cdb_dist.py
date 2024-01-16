import argparse, gzip
import matplotlib.pyplot as plt
from collections import Counter


def open_file(filename):
    open_func = gzip.open if filename.endswith(".gz") else open
    return open_func(filename, "rt")


class data:
    def __init__(self, filename, debug=False):
        self.connected = 0
        self.evals = []
        self.plies = []
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
                        self.plies.append(int(ply[:-1]))
                    else:
                        cdb, _, _ = cdb.partition(";")
                    if cdb.lstrip("-").isnumeric():
                        self.evals.append(int(cdb))
                    elif cdb.startswith("M"):
                        self.evals.append(30000 - int(cdb[1:]))
                    elif cdb.startswith("-M"):
                        self.evals.append(-30000 + int(cdb[2:]))
        self.filename = filename[:-3] if filename.endswith(".gz") else filename
        print(
            f"Loaded {len(self.evals)} EPDs with evals in [{min(self.evals)}, {max(self.evals)}], {self.connected} of which are connected to root on cdb."
        )
        l = len(self.plies)
        print(
            f"{l} of the EPDs have ply in [{min(self.plies)}, {max(self.plies)}], average = {sum(self.plies)/l:.2f}."
        )
        if debug:
            print("eval frequencies:", end=" ")
            eval_count = sorted(
                Counter(self.evals).items(), key=lambda t: abs(t[0]) + 0.5 * (t[0] < 0)
            )
            print(", ".join([f"{eval}: {frequency}" for eval, frequency in eval_count]))
            print("ply frequencies:", end=" ")
            ply_count = sorted(Counter(self.plies).items(), key=lambda x: x[0])
            print(", ".join([f"{ply}: {frequency}" for ply, frequency in ply_count]))

    def create_evalgraph(self, bucketSize=10, cutOff=200, absEval=False):
        if absEval:
            evals = [min(abs(e), cutOff) for e in self.evals]
        else:
            evals = [min(max(-cutOff, e), cutOff) for e in self.evals]
        rangeMin, rangeMax = min(evals), max(evals)
        fig, ax = plt.subplots()
        ax.hist(
            evals,
            range=(rangeMin, rangeMax),
            bins=(rangeMax - rangeMin) // bucketSize,
            density=True,
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

    def create_plygraph(self, bucketSize=2, cutOff=200):
        plies = [min(p, cutOff) for p in self.plies]
        rangeMin, rangeMax = min(plies), max(plies)
        fig, ax = plt.subplots()
        ax.hist(
            plies,
            range=(rangeMin, rangeMax),
            bins=(rangeMax - rangeMin) // bucketSize,
            density=True,
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
        "--debug",
        action="store_true",
        help="Show frequency data on stdout.",
    )
    args = parser.parse_args()

    d = data(args.filename, args.debug)
    d.create_evalgraph(args.bucket, args.cutOff, args.absEval)
    d.create_plygraph(args.plyBucket, args.plyCutOff)

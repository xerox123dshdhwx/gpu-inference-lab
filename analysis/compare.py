"""Compare runs: p90 TTFT against load, one line per run."""
import re
import sys
import matplotlib.pyplot as plt
import polars as pl

from result_paths import BASELINE_FOLDER, results_directory

runs = ["baseline" if name == BASELINE_FOLDER else name for name in sys.argv[1:]]
for name in runs:
    rows = []
    for path in results_directory(name).glob("users_*.jsonl"):
        users = int(re.search(r"users_(\d+)", path.name).group(1))
        df = pl.read_ndjson(path, infer_schema_length=None).filter(pl.col("ttft").is_not_null())
        rows.append({"users": users, "p90_ms": df["ttft"].quantile(0.9) * 1000})
    s = pl.DataFrame(rows).sort("users")
    label = BASELINE_FOLDER if name == "baseline" else name
    plt.plot(s["users"], s["p90_ms"], marker="o", label=label)
plt.axhline(1000, linestyle="--", color="gray")
plt.xscale("log", base=2)
plt.xlabel("simultaneous users")
plt.ylabel("p90 TTFT (ms)")
plt.legend()
out = "results/compare_" + "_vs_".join(runs) + ".png"
plt.savefig(out, dpi=150)
print("Saved", out)
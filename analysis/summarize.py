"""Summarize one run: latency, throughput and errors per load level, plus a chart."""
import re
import sys

import matplotlib.pyplot as plt
import polars as pl

from result_paths import results_directory

name = sys.argv[1] if len(sys.argv) > 1 else "baseline"
results_dir = results_directory(name)
TARGET_MS = 1000  # your p90 TTFT target
rows = []
for path in results_dir.glob("users_*.jsonl"):
    users = int(re.search(r"users_(\d+)", path.name).group(1))
    df = pl.read_ndjson(path, infer_schema_length=None) if path.stat().st_size else pl.DataFrame()
    errors = df["error"].is_not_null().sum() if "error" in df.columns else 0
    ok = df.filter(pl.col("ttft").is_not_null()) if "ttft" in df.columns else pl.DataFrame()
    row = {
        "users": users,
        "p50_ttft_ms": None,
        "p90_ttft_ms": None,
        "itl_ms": None,
        "tokens_per_s": None,
        "errors": errors,
    }
    if ok.is_empty():
        print(f"{path.name}: no successful timings ({errors} request errors).", file=sys.stderr)
    else:
        span = (ok["start"] + ok["e2e"]).max() - ok["start"].min()
        streamed = ok.filter(pl.col("chunks") > 1)
        itl = ((streamed["e2e"] - streamed["ttft"]) / (streamed["chunks"] - 1)).median()
        row.update(
            p50_ttft_ms=ok["ttft"].quantile(0.5) * 1000,
            p90_ttft_ms=ok["ttft"].quantile(0.9) * 1000,
            itl_ms=itl * 1000 if itl is not None else None,
            tokens_per_s=ok["chunks"].sum() / span if span > 0 else None,
        )
    rows.append(row)

if not rows:
    sys.exit(f"No benchmark timing files found in {results_dir}.")

summary = pl.DataFrame(rows, infer_schema_length=None).sort("users")
print(summary)
if summary["p90_ttft_ms"].is_null().all():
    sys.exit("No load level has successful timings. Check the request errors in the benchmark files.")

fits = summary.filter(pl.col("p90_ttft_ms") < TARGET_MS)
print("Capacity at target:", fits["users"].max() if len(fits) else 0, "users")

plt.plot(summary["users"], summary["p90_ttft_ms"], marker="o")
plt.axhline(TARGET_MS, linestyle="--")
plt.xscale("log", base=2)
plt.xlabel("simultaneous users")
plt.ylabel("p90 TTFT (ms)")
plt.savefig(results_dir / "p90_ttft.png", dpi=150)

#!/usr/bin/env python3
"""Simple analysis/plot script for Experiment 1 DRAM baseline.

- Discovers JSON result files in ../results/raw by default.
- Prints a summary table of key metrics.
- Generates basic plots (recall vs QPS, latency percentiles) if matplotlib is available.

Usage examples (from project root or experiment dir via WSL):

  cd experiments/Experiment1_DRAM_Baseline
  python scripts/analyze_experiment1.py

or:

  python experiments/Experiment1_DRAM_Baseline/scripts/analyze_experiment1.py \
      --glob "results/raw/*.json"  # pattern is interpreted relative to the experiment dir
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List

try:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:  # pragma: no cover - fallback if matplotlib is missing
    HAS_MPL = False


def load_results(paths: List[Path]):
    rows = []
    for p in paths:
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load {p}: {e}", file=sys.stderr)
            continue

        cfg = data.get("config", {})
        agg = data.get("aggregate", {})
        io = agg.get("io", {})

        num_q = agg.get("num_queries") or cfg.get("num_queries") or 0
        search_s = agg.get("search_time_s")

        qps_search = agg.get("qps_search")
        if qps_search is None and num_q and search_s is not None:
            try:
                s = float(search_s)
                if s > 0.0:
                    qps_search = float(num_q) / s
            except Exception:
                qps_search = None

        qps_total = agg.get("qps_total")
        if qps_total is None:
            qps_total = agg.get("qps")

        rows.append(
            {
                "file": p.name,
                "dataset": cfg.get("dataset_name", ""),
                "mode": cfg.get("mode", ""),
                "k": agg.get("k"),
                "num_queries": agg.get("num_queries"),
                "recall_at_k": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "p50": agg.get("latency_us_p50"),
                "p95": agg.get("latency_us_p95"),
                "p99": agg.get("latency_us_p99"),
                "build_time_s": agg.get("build_time_s"),
                "search_time_s": agg.get("search_time_s"),
                "io_num_reads": io.get("num_reads"),
                "io_bytes_read": io.get("bytes_read"),
                "device_time_us": agg.get("device_time_us"),
            }
        )
    return rows


def print_table(rows):
    if not rows:
        print("No results to show.")
        return

    headers = [
        "file",
        "dataset",
        "mode",
        "k",
        "num_q",
        "recall",
        "qps_search",
        "qps_total",
        "eff_qps",
        "p50(us)",
        "p95(us)",
        "p99(us)",
    ]

    print("\n=== Experiment 1 Summary ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    str(r["file"]),
                    str(r["dataset"]),
                    str(r["mode"]),
                    str(r["k"]),
                    str(r["num_queries"]),
                    f"{r['recall_at_k']:.4f}" if r["recall_at_k"] is not None else "",
                    f"{r['qps_search']:.4f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.4f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.4f}" if r["effective_qps"] is not None else "",
                    f"{r['p50']:.1f}" if r["p50"] is not None else "",
                    f"{r['p95']:.1f}" if r["p95"] is not None else "",
                    f"{r['p99']:.1f}" if r["p99"] is not None else "",
                ]
            )
        )


def _format_k(value):
    """Format a numeric value using a compact k-suffix when appropriate."""

    if value is None:
        return ""
    try:
        v = float(value)
    except Exception:
        return str(value)

    if v == 0:
        return "0"

    if abs(v) >= 1000.0:
        return f"{int(round(v / 1000.0))}k"

    # For smaller values (e.g., microsecond latencies), round to the nearest
    # integer to keep labels short.
    return str(int(round(v)))


def _k_formatter(x: float, _pos) -> str:
    return _format_k(x)


def _extract_ef_from_name(base: str):
    """Best-effort extraction of the search expansion factor EF from a filename.

    Handles patterns like:
    - ..._EF_SEARCH-0016.json
    - ..._efs512_...
    - ..._ef256_...
    """

    # Strip extension if present.
    if base.endswith(".json"):
        base = base[:-5]

    tokens = base.split("_")

    # Highest priority: explicit EF + SEARCH-XXXX token pairs, e.g. ..._EF_SEARCH-0016.
    for i, tok in enumerate(tokens):
        if tok.upper() == "EF" and i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if "SEARCH-" in nxt.upper():
                try:
                    part = nxt.split("SEARCH-", 1)[1]
                    # Strip any extension like .json
                    if "." in part:
                        part = part.split(".", 1)[0]
                    return int(part)
                except Exception:
                    continue

    # Also handle compact EF_SEARCH-XXXX tokens if they ever appear.
    for tok in tokens:
        if "EF_SEARCH-" in tok:
            try:
                part = tok.split("EF_SEARCH-", 1)[1]
                if "." in part:
                    part = part.split(".", 1)[0]
                return int(part)
            except Exception:
                continue

    # Next, look for efsNNN tokens (search ef) such as "efs512".
    for tok in tokens:
        t = tok.lower()
        if t.startswith("efs") and t[3:].isdigit():
            try:
                return int(t[3:])
            except Exception:
                continue

    # Finally, plain efNNN tokens such as "ef256".
    for tok in tokens:
        t = tok.lower()
        if t.startswith("ef") and t[2:].isdigit():
            try:
                return int(t[2:])
            except Exception:
                continue

    return None


def _short_param_label(base: str, axis_label: str) -> str:
    """Derive a concise EF-based x-axis label from a filename.

    All runs are labeled as ``EF - <value>`` when we can infer the search
    expansion factor from the filename, regardless of dataset or other
    suffixes like thread count or num-queries.
    """

    ef = _extract_ef_from_name(base)
    if ef is not None:
        # If this is the SIFT1M EF=256 run, add a tiny suffix so it is
        # distinguishable from the synthetic EF=256 point on the same plot.
        base_lower = base.lower()
        if "sift1m" in base_lower and ef == 256:
            return "EF - 256 (SIFT1M)"

        return f"EF - {ef}"

    # Fallback: strip extension and use the base token as-is.
    if base.endswith(".json"):
        base = base[:-5]
    return base or "run"


def make_plots(rows, out_dir: Path):
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Simple bar plot: recall and QPS per run
    labels = [r["file"] for r in rows]
    common_prefix = os.path.commonprefix(labels)

    axis_label = "configuration"
    if labels:
        base_fname = labels[0]
        if base_fname.endswith(".json"):
            base_fname = base_fname[:-5]
        # Expect filenames like ..._EF_SEARCH-0016 or ..._NUM_BASE-10000.
        # Scan underscore-separated tokens; when we find a token containing
        # a dash, optionally combine it with the previous token if both look
        # like identifier segments (e.g., EF + SEARCH -> EF_SEARCH).
        tokens = base_fname.split("_")
        params = []
        for i, tok in enumerate(tokens):
            if "-" not in tok:
                continue
            name_part = tok.split("-", 1)[0]
            candidate = name_part
            if i > 0:
                prev = tokens[i - 1]
                if prev.isalpha() and prev.isupper() and name_part.isalpha() and name_part.isupper():
                    candidate = f"{prev}_{name_part}"
            params.append(candidate.lower())
        if params:
            axis_label = sorted(set(params))[0]

    # Human-friendly display label for the x-axis: we always present this
    # plot as an EF sweep, even if filenames differ between datasets.
    axis_label_display = "Search Expansion Factor (EF)"

    def _short_label(lbl: str) -> str:
        # Remove shared prefix and delegate to a parameter-aware labeler so
        # x-axis text stays compact and focused on the swept parameter.
        s = lbl[len(common_prefix):] if common_prefix else lbl
        return _short_param_label(s, axis_label)

    tick_labels = [_short_label(lbl) for lbl in labels]

    recall = [r["recall_at_k"] for r in rows]
    eff_qps = [r.get("effective_qps") if r.get("effective_qps") is not None else (r.get("qps_search") or 0.0) for r in rows]

    x = range(len(labels))
    # Slightly taller figure plus extra bottom margin so the x-axis label and
    # EF tick labels are not clipped in the report.
    fig, ax1 = plt.subplots(figsize=(8, 4.8))

    # Left axis: recall@k line
    line1 = ax1.plot(x, recall, marker="o", color="C0", label="recall@k")[0]
    ax1.set_ylabel("Recall@k")
    ax1.set_ylim(0.0, 1.05)

    # Right axis: throughput line
    ax2 = ax1.twinx()
    line2 = ax2.plot(x, eff_qps, marker="s", color="C1", label="Effective QPS")[0]
    ax2.set_ylabel("Effective QPS")
    ax2.yaxis.set_major_formatter(FuncFormatter(_k_formatter))

    # Add headroom so the largest QPS value does not clip the top border.
    if eff_qps:
        try:
            ymax = max(float(v) for v in eff_qps)
            if ymax > 0:
                ax2.set_ylim(0, ymax * 1.1)
        except Exception:
            pass

    ax1.set_xticks(list(x))
    ax1.set_xticklabels(tick_labels, rotation=45, ha="right")
    ax1.set_xlabel(axis_label_display)
    ax1.set_title("Experiment 1: Recall and Effective QPS per Run")

    # Combined legend with concise labels, placed to avoid overlapping the curves.
    ax1.legend([line1, line2], [line1.get_label(), line2.get_label()], loc="lower left")

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.35)
    fig.savefig(out_dir / "exp1_recall_qps.png", dpi=150)
    plt.close(fig)

    # Latency percentiles bar plot
    p50 = [r["p50"] for r in rows]
    p95 = [r["p95"] for r in rows]
    p99 = [r["p99"] for r in rows]

    fig, ax = plt.subplots(figsize=(8, 4))
    width = 0.25
    bars_p50 = ax.bar([i - width for i in x], p50, width, label="p50")
    bars_p95 = ax.bar(x, p95, width, label="p95")
    bars_p99 = ax.bar([i + width for i in x], p99, width, label="p99")

    ax.set_xticks(list(x))
    ax.set_xticklabels(tick_labels, rotation=45, ha="right")
    ax.set_xlabel(axis_label_display)
    ax.set_ylabel("Latency (us)")
    ax.set_title("Experiment 1: Latency Percentiles per Run")

    # Use k-style formatting for latency values so large microsecond values
    # remain readable, and add annotations above each bar with a bit of
    # headroom so labels do not clip the top of the plot.
    ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))

    all_vals = [v for arr in (p50, p95, p99) for v in arr if v is not None]
    if all_vals:
        try:
            ymax = max(float(v) for v in all_vals)
            if ymax > 0:
                ax.set_ylim(0, ymax * 1.15)
        except Exception:
            pass

    def _annotate_group(b50_bar, p95_bar, p99_bar):
        """Annotate one (p50, p95, p99) group, staggering labels only if needed.

        If the three bars are very close in height, we use increasing vertical
        offsets to avoid text overlap. Otherwise, we keep a small uniform
        offset so labels stay visually tight to their bars.
        """

        bars = [b50_bar, p95_bar, p99_bar]
        heights = [b.get_height() for b in bars]
        max_h = max(heights)
        min_h = min(heights)

        base_offset = 3
        offsets = [base_offset, base_offset, base_offset]

        # If p50/p95/p99 are within ~15% of each other, they are likely to
        # overlap; in that case, stagger the text more aggressively.
        if max_h > 0 and (max_h - min_h) < 0.15 * max_h:
            offsets = [3, 11, 19]

        for bar, offset in zip(bars, offsets):
            height = bar.get_height()
            ax.annotate(
                _format_k(height),
                xy=(bar.get_x() + bar.get_width() / 2.0, height),
                xytext=(0, offset),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    # Annotate each x-position group, only staggering when the three
    # percentiles are close enough in height that their labels would collide.
    for i in range(len(x)):
        _annotate_group(bars_p50[i], bars_p95[i], bars_p99[i])

    ax.legend()
    fig.tight_layout()
    fig.savefig(out_dir / "exp1_latency_percentiles.png", dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 1 DRAM baseline results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    if args.glob is None:
        pattern = "results/raw/*.json"
    else:
        pattern = args.glob

    # Use a relative glob rooted at the experiment directory to avoid the
    # Python 3.12 restriction on non-relative patterns in Path.glob.
    paths = sorted(exp_dir.glob(pattern))
    if not paths:
        print(f"No JSON files found for pattern: {exp_dir / pattern}")
        return 0

    rows = load_results(paths)
    print_table(rows)

    plots_dir = exp_dir / "results" / "plots"
    make_plots(rows, plots_dir)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

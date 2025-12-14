#!/usr/bin/env python3
"""Analysis/plot script for Experiment 2 (Tiered vs DRAM).

- Discovers JSON result files in ../results/raw by default.
- Prints a summary table of DRAM and tiered runs.
- Generates simple plots for recall, QPS, and I/O vs cache size.

Usage (from project root via WSL):

  wsl bash -lc 'cd /mnt/c/.../Experiment2_Tiered_vs_DRAM && python3 scripts/analyze_experiment2.py'
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List

try:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:  # pragma: no cover
    HAS_MPL = False


def _cache_pct_from_name(name: str, mode: str) -> float:
    """Best-effort cache percentage parsed from filename.

    For filenames like exp2_tiered_cache10_..., returns 10.0.
    For DRAM runs, we return 100.0 to treat them as a full-cache baseline.
    """

    if mode == "dram":
        return 100.0
    m = re.search(r"cache(\d+)", name)
    if not m:
        return 0.0
    return float(m.group(1))


def load_results(paths: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for p in paths:
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:  # pragma: no cover - diagnostics only
            print(f"[WARN] Failed to load {p}: {e}")
            continue

        cfg = data.get("config", {})
        agg = data.get("aggregate", {})
        io = agg.get("io", {})

        mode = cfg.get("mode", "")
        cache_pct = _cache_pct_from_name(p.name, mode)

        num_q = agg.get("num_queries")
        search_s = agg.get("search_time_s")

        qps_search = agg.get("qps_search")
        if qps_search is None and num_q is not None and search_s is not None:
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
                "mode": mode,
                "dataset": cfg.get("dataset_name", ""),
                "num_base": cfg.get("num_vectors"),
                "num_queries": agg.get("num_queries"),
                "ef_search": cfg.get("ef_search"),
                "cache_pct": cache_pct,
                "recall": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "build_time_s": agg.get("build_time_s"),
                "search_time_s": agg.get("search_time_s"),
                "device_time_us": agg.get("device_time_us"),
                "num_reads": io.get("num_reads"),
                "bytes_read": io.get("bytes_read"),
            }
        )
    return rows


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

    return f"{v:g}"


def _k_formatter(x: float, _pos) -> str:
    return _format_k(x)


def print_table(rows: List[Dict[Any, Any]]) -> None:
    if not rows:
        print("No Experiment 2 results to show.")
        return

    headers = [
        "file",
        "mode",
        "cache%",
        "recall",
        "qps_search",
        "qps_total",
        "eff_qps",
        "build_s",
        "search_s",
        "dev_us",
        "reads",
        "bytes_read",
    ]

    print("\n=== Experiment 2 Summary (Tiered vs DRAM) ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    str(r["file"]),
                    str(r["mode"]),
                    f"{r['cache_pct']:.1f}",
                    f"{r['recall']:.5f}" if r["recall"] is not None else "",
                    f"{r['qps_search']:.3f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.3f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.3f}" if r["effective_qps"] is not None else "",
                    f"{r['build_time_s']:.3f}" if r["build_time_s"] is not None else "",
                    f"{r['search_time_s']:.3f}" if r["search_time_s"] is not None else "",
                    f"{r['device_time_us']:.1f}" if r["device_time_us"] is not None else "",
                    str(r["num_reads"]),
                    str(r["bytes_read"]),
                ]
            )
        )


def make_plots(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping Experiment 2 plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Sort by cache_pct so DRAM (100%) and tiered runs line up.
    rows_sorted = sorted(rows, key=lambda r: (r["mode"], r["cache_pct"]))

    # Human-readable x-axis labels: highlight the DRAM baseline and tiered
    # cache fractions without repeating low-level naming.
    labels = []
    for r in rows_sorted:
        if r["mode"] == "dram":
            labels.append("DRAM")
        else:
            pct = int(r["cache_pct"] or 0)
            labels.append(f"Cache - {pct}%")

    x = list(range(len(labels)))

    recall = [r["recall"] for r in rows_sorted]
    eff_qps = [
        r["effective_qps"]
        if r["effective_qps"] is not None
        else (r["qps_search"] or 0.0)
        for r in rows_sorted
    ]

    # Plot 1: Recall + effective QPS vs configuration
    fig, ax1 = plt.subplots(figsize=(8, 4))
    line1 = ax1.plot(x, recall, marker="o", color="C0", label="recall@k")[0]
    ax1.set_ylabel("Recall@k")
    ax1.set_ylim(0.0, 1.05)

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

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=0, ha="center")
    ax1.set_xlabel("Configuration (DRAM Baseline and Tiered Cache Fraction)")
    ax1.set_title("Experiment 2: Recall and Effective QPS vs Configuration")

    # Combined legend with concise labels, placed to avoid overlapping the curves.
    ax1.legend([line1, line2], [line1.get_label(), line2.get_label()], loc="lower left")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.3)
    fig.savefig(out_dir / "exp2_recall_effective_qps.png", dpi=150)
    plt.close(fig)

    # Plot 2: I/O per query vs cache size (tiered only)
    tiered_rows = [r for r in rows_sorted if r["mode"] == "tiered"]
    if tiered_rows:
        tiered_rows = sorted(tiered_rows, key=lambda r: r["cache_pct"])
        tq = [r["num_queries"] or 1 for r in tiered_rows]
        cache_pct = [r["cache_pct"] for r in tiered_rows]
        reads_per_q = [(r["num_reads"] or 0) / tq[i] for i, r in enumerate(tiered_rows)]
        mib_per_q = [((r["bytes_read"] or 0) / tq[i]) / (1024.0 * 1024.0) for i, r in enumerate(tiered_rows)]

        # Use two stacked subplots so reads/query and MiB/query are both
        # clearly visible, even when scales differ.
        fig, (ax_reads, ax_mib) = plt.subplots(2, 1, figsize=(8, 6), sharex=True)

        # Top: reads/query
        ax_reads.plot(cache_pct, reads_per_q, marker="o", color="C0", label="reads/query")
        ax_reads.set_ylabel("reads/query")
        ax_reads.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax_reads.grid(True, alpha=0.3)
        ax_reads.legend(loc="upper right")

        # Bottom: MiB/query
        ax_mib.plot(cache_pct, mib_per_q, marker="s", color="C1", label="MiB/query")
        ax_mib.set_ylabel("MiB/query")
        ax_mib.set_xlabel("Tiered Cache Size (% of Index, by Vector Count)")
        ax_mib.set_xticks(cache_pct)
        ax_mib.set_xticklabels([f"{int(p)}%" for p in cache_pct])
        ax_mib.grid(True, alpha=0.3)
        ax_mib.legend(loc="upper right")

        fig.suptitle("Experiment 2: I/O per Query vs Cache Size\n(Tiered)")
        fig.tight_layout(rect=(0.0, 0.05, 1.0, 1.0))
        fig.savefig(out_dir / "exp2_io_per_query_vs_cache.png", dpi=150)
        plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 2 Tiered vs DRAM results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/exp2_*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/exp2_*.json"
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

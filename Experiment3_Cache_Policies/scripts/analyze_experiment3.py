#!/usr/bin/env python3
"""Analysis/plot script for Experiment 3 (Cache Policies).

- Loads JSON result files from results/raw/exp3_*.json.
- Prints a summary table for LRU vs LFU cache policies.
- Generates simple plots of hit rate and effective QPS vs policy.

Usage (from project root via WSL):

  wsl bash -lc 'cd /mnt/c/.../Experiment3_Cache_Policies && python3 scripts/analyze_experiment3.py'
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

try:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:  # pragma: no cover
    HAS_MPL = False


def load_results(paths: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for p in paths:
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:  # pragma: no cover
            print(f"[WARN] Failed to load {p}: {e}")
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

        hits = agg.get("cache_hits")
        misses = agg.get("cache_misses")
        hit_rate = None
        if hits is not None and misses is not None and (hits + misses) > 0:
            hit_rate = float(hits) / float(hits + misses)

        rows.append(
            {
                "file": p.name,
                "policy": cfg.get("cache_policy", ""),
                "cache_capacity": cfg.get("cache_capacity"),
                "recall": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "build_time_s": agg.get("build_time_s"),
                "search_time_s": agg.get("search_time_s"),
                "device_time_us": agg.get("device_time_us"),
                "num_reads": io.get("num_reads"),
                "bytes_read": io.get("bytes_read"),
                "cache_hits": hits,
                "cache_misses": misses,
                "hit_rate": hit_rate,
            }
        )
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No Experiment 3 results to show.")
        return

    headers = [
        "file",
        "policy",
        "cap",
        "recall",
        "qps_search",
        "qps_total",
        "eff_qps",
        "hit_rate",
        "reads",
        "bytes_read",
        "dev_us",
    ]

    print("\n=== Experiment 3 Summary (Cache Policies) ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    r["file"],
                    str(r["policy"]),
                    str(r["cache_capacity"]),
                    f"{r['recall']:.5f}" if r["recall"] is not None else "",
                    f"{r['qps_search']:.3f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.3f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.3f}" if r["effective_qps"] is not None else "",
                    f"{r['hit_rate']:.3f}" if r["hit_rate"] is not None else "",
                    str(r["num_reads"]),
                    str(r["bytes_read"]),
                    f"{r['device_time_us']:.1f}" if r["device_time_us"] is not None else "",
                ]
            )
        )


def _format_k(value: Any) -> str:
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


def make_plots(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping Experiment 3 plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Sort by policy name for a stable order.
    rows_sorted = sorted(rows, key=lambda r: str(r["policy"]))

    labels = [str(r["policy"]).upper() for r in rows_sorted]
    x = list(range(len(labels)))

    hit_rates = [r["hit_rate"] for r in rows_sorted]
    eff_qps = [r["effective_qps"] for r in rows_sorted]

    # Plot 1: cache hit rate vs policy
    fig, ax = plt.subplots(figsize=(6, 4))
    bars = ax.bar(x, hit_rates, color="C0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_ylim(0.0, 1.05)
    ax.set_ylabel("Cache Hit Rate")
    ax.set_xlabel("Cache Policy")
    ax.set_title("Experiment 3: Cache Hit Rate vs Policy")

    # Annotate bars with hit-rate values so small differences remain visible.
    for bar in bars:
        height = bar.get_height()
        if height is None:
            continue
        ax.annotate(
            f"{height:.3f}",
            xy=(bar.get_x() + bar.get_width() / 2.0, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.3)
    fig.savefig(out_dir / "exp3_hit_rate_vs_policy.png", dpi=150)
    plt.close(fig)

    # Plot 2: effective QPS vs policy
    fig, ax = plt.subplots(figsize=(6, 4))
    bars_qps = ax.bar(x, eff_qps, color="C1")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_ylabel("Effective QPS")
    ax.set_xlabel("Cache Policy")
    ax.set_title("Experiment 3: Effective QPS vs Policy")

    # Use k-style formatting so large QPS values remain readable, and add a
    # bit of headroom to avoid clipping the tallest bar.
    ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
    if eff_qps:
        try:
            ymax = max(float(v) for v in eff_qps if v is not None)
            if ymax > 0:
                ax.set_ylim(0, ymax * 1.15)
        except Exception:
            pass

    for bar in bars_qps:
        height = bar.get_height()
        if height is None:
            continue
        ax.annotate(
            _format_k(height),
            xy=(bar.get_x() + bar.get_width() / 2.0, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.3)
    fig.savefig(out_dir / "exp3_effective_qps_vs_policy.png", dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 3 cache policy results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/exp3_*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/exp3_*.json"
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

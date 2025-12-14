#!/usr/bin/env python3
"""Analysis/plot script for Experiment 0 (hnswlib DRAM upper bound).

- Discovers JSON result files in ../results/raw by default.
- Prints a summary table of key metrics.
- Generates simple plots (recall vs QPS, build/search time) if matplotlib is available.

Usage (from project root via WSL):

  wsl bash -lc 'cd /mnt/c/.../Experiment0_HNSWLIB_Baseline && python3 scripts/analyze_experiment0.py'

You can also override the glob pattern:

  python3 scripts/analyze_experiment0.py --glob 'results/raw/hnswlib_*.json'
"""

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

try:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:  # pragma: no cover
    HAS_MPL = False


def load_results(paths: List[Path]) -> List[Dict[str, Any]]:
    rows = []
    for p in paths:
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:  # pragma: no cover - diagnostics only
            print(f"[WARN] Failed to load {p}: {e}")
            continue

        cfg = data.get("config", {})
        agg = data.get("aggregate", {})

        qps_search = agg.get("qps_search")
        if qps_search is None:
            qps_search = agg.get("search_qps")
        if qps_search is None:
            qps_search = agg.get("qps")

        qps_total = agg.get("qps_total")
        if qps_total is None:
            qps_total = agg.get("total_qps")
        if qps_total is None:
            qps_total = agg.get("qps")

        rows.append(
            {
                "file": p.name,
                "name": data.get("name", p.stem),
                "dataset": cfg.get("dataset_name", ""),
                "num_base": cfg.get("num_base"),
                "num_queries": cfg.get("num_queries"),
                "ef_search": cfg.get("ef_search"),
                "recall": agg.get("recall_at_k"),
                "build_time_s": agg.get("build_time_s"),
                "search_time_s": agg.get("search_time_s"),
                "qps_total": qps_total,
                "qps_search": qps_search,
            }
        )
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No Experiment 0 results to show.")
        return

    headers = [
        "file",
        "dataset",
        "num_base",
        "num_q",
        "ef_search",
        "recall",
        "qps_total",
        "qps_search",
        "build_s",
        "search_s",
    ]

    print("\n=== Experiment 0 Summary (hnswlib) ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    str(r["file"]),
                    str(r["dataset"]),
                    str(r["num_base"]),
                    str(r["num_queries"]),
                    str(r["ef_search"]),
                    f"{r['recall']:.6f}" if r["recall"] is not None else "",
                    f"{r['qps_total']:.3f}" if r["qps_total"] is not None else "",
                    f"{r['qps_search']:.3f}" if r["qps_search"] is not None else "",
                    f"{r['build_time_s']:.4f}" if r["build_time_s"] is not None else "",
                    f"{r['search_time_s']:.4f}" if r["search_time_s"] is not None else "",
                ]
            )
        )


def _format_k(value: Any) -> str:
    """Format a numeric value using a compact k-suffix when appropriate.

    Examples: 0 -> "0", 1200 -> "1k", 25853 -> "26k".
    """
    if value is None:
        return ""
    try:
        v = float(value)
    except Exception:
        return str(value)

    if v == 0:
        return "0"

    abs_v = abs(v)
    if abs_v >= 1000.0:
        return f"{int(round(v / 1000.0))}k"

    return f"{v:g}"


def _k_formatter(x: float, _pos: Any) -> str:
    """Adapter for FuncFormatter using _format_k."""

    return _format_k(x)


def _format_num_k(n: Any) -> str:
    """Format a base-vector count as 20k-style text for labels."""

    if n is None:
        return "?"
    try:
        v = int(n)
    except Exception:
        return str(n)

    if abs(v) >= 1000 and v % 1000 == 0:
        return f"{v // 1000}k"
    return str(v)


def _config_label(r: Dict[str, Any]) -> str:
    """Human-friendly configuration label for x-axis tick labels/titles."""

    dataset = str(r.get("dataset") or "")
    n_str = _format_num_k(r.get("num_base"))
    ef = r.get("ef_search")
    ef_str = str(ef) if ef is not None else "?"
    if dataset:
        return f"{dataset} {n_str}, ef={ef_str}"
    return f"{n_str}, ef={ef_str}"


def make_plots(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping Experiment 0 plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Sort for a stable order: by dataset, then ef_search, then num_base
    rows_sorted = sorted(
        rows,
        key=lambda r: (int(r["num_base"] or 0), int(r["ef_search"] or 0)),
    )

    labels = [r["name"] for r in rows_sorted]
    x = list(range(len(labels)))

    recall = [r["recall"] for r in rows_sorted]
    search_qps = [r["qps_search"] for r in rows_sorted]

    # Plot 1: Recall vs search QPS
    fig, ax1 = plt.subplots(figsize=(8, 4))

    line1 = ax1.plot(x, recall, marker="o", color="C0", label="Recall @ k")[0]
    ax1.set_ylabel("Recall @ k")
    ax1.set_ylim(0.0, 1.05)

    ax2 = ax1.twinx()
    line2 = ax2.plot(x, search_qps, marker="s", color="C1", label="Search QPS")[0]
    ax2.set_ylabel("Search QPS")
    ax2.yaxis.set_major_formatter(FuncFormatter(_k_formatter))

    tick_labels = [_config_label(r) for r in rows_sorted]
    ax1.set_xticks(x)
    ax1.set_xticklabels(tick_labels, rotation=0, ha="center")
    ax1.set_xlabel("Configuration (dataset, ef_search)")
    ax1.set_title("Experiment 0: Recall vs Search QPS\n(HNSWlib)")

    ax1.legend([line1, line2], [line1.get_label(), line2.get_label()], loc="lower left")
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.3)
    fig.savefig(out_dir / "exp0_recall_search_qps.png", dpi=150)
    plt.close(fig)

    # Plot 2: build and search time per configuration
    # Build per-configuration subplots for build/search time so each can
    # use its own y-scale and add value annotations.
    build = [r["build_time_s"] for r in rows_sorted]
    search = [r["search_time_s"] for r in rows_sorted]

    num_cfg = len(rows_sorted)
    if num_cfg == 0:
        return

    fig, axes = plt.subplots(num_cfg, 1, figsize=(8, 3 * num_cfg), sharex=False)
    if num_cfg == 1:
        axes = [axes]  # type: ignore[list-item]

    for ax, r, b_val, s_val in zip(axes, rows_sorted, build, search):
        cfg_label = _config_label(r)
        x_local = [0, 1]
        labels_local = ["Build", "Search"]
        vals = [b_val, s_val]

        bars = ax.bar(x_local, vals, color=["C0", "C1"])
        ax.set_xticks(x_local)
        ax.set_xticklabels(labels_local)
        ax.set_ylabel("Time (s)")
        ax.set_title(cfg_label)

        # Add a bit of headroom so labels do not clip.
        ymax = max(vals) if vals else 0.0
        if ymax > 0:
            ax.set_ylim(0, ymax * 1.15)

        # Annotate each bar with its value.
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.3f}",
                xy=(bar.get_x() + bar.get_width() / 2.0, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    fig.suptitle("Experiment 0: Build vs Search Time\n(HNSWlib)")
    fig.tight_layout(rect=(0.0, 0.03, 1.0, 1.0))
    fig.savefig(out_dir / "exp0_build_search_time.png", dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 0 hnswlib baseline results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/hnswlib_*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/hnswlib_*.json"
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

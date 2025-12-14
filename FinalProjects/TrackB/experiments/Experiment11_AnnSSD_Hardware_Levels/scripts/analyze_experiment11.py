#!/usr/bin/env python3
"""Analysis/plot script for Experiment 11 (ANN-in-SSD hardware levels).

Loads JSON logs from results/raw, prints a summary table, and generates
basic plots (effective_qps vs num_vectors and device_time vs num_vectors).

Usage (from experiment dir, inside WSL):

  cd experiments/Experiment11_AnnSSD_Hardware_Levels
  python scripts/analyze_experiment11.py
"""

import argparse
import json
import math
import sys
from pathlib import Path
from typing import List, Dict, Any

try:
    import matplotlib

    matplotlib.use("Agg")
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
        except Exception as e:
            print(f"[WARN] Failed to load {p}: {e}", file=sys.stderr)
            continue

        cfg = data.get("config", {})
        agg = data.get("aggregate", {})

        qps_search = agg.get("qps_search")
        if qps_search is None:
            qps_search = agg.get("qps")

        qps_total = agg.get("qps_total")
        if qps_total is None:
            qps_total = agg.get("qps")

        # Derive a consistent notion of effective_qps from the analytic
        # search time if available so that faithful and cheated modes line
        # up. This avoids confusion from differing internal definitions of
        # effective_qps across modes.
        num_queries = agg.get("num_queries") or cfg.get("num_queries")
        eff_qps = agg.get("effective_qps")
        analytic_s = agg.get("analytic_search_time_s")
        if eff_qps is None and analytic_s is None:
            analytic_s = agg.get("effective_search_time_s")
        if num_queries and analytic_s and analytic_s > 0.0:
            try:
                eff_qps = float(num_queries) / float(analytic_s)
            except Exception:
                pass

        rows.append(
            {
                "file": p.name,
                "dataset": cfg.get("dataset_name", ""),
                "num_vectors": cfg.get("num_vectors"),
                "level": cfg.get("hardware_level", ""),
                "mode": cfg.get("simulation_mode", ""),
                "k": agg.get("k"),
                "num_queries": agg.get("num_queries"),
                "recall_at_k": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": eff_qps,
                "compute_time_s": agg.get("compute_time_s"),
                "device_time_us": agg.get("device_time_us"),
                "analytic_search_time_s": agg.get("analytic_search_time_s"),
                "avg_blocks_visited": agg.get("avg_blocks_visited"),
                "avg_distances_computed": agg.get("avg_distances_computed"),
            }
        )
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No results to show.")
        return

    headers = [
        "file",
        "num_vec",
        "level",
        "mode",
        "recall",
        "qps_search",
        "qps_total",
        "eff_qps",
        "compute_s",
        "device_s",
    ]

    print("\n=== Experiment 11 Summary ===")
    print("\t".join(headers))
    for r in sorted(rows, key=lambda x: (x["num_vectors"], x["level"], x["mode"])):
        device_s = (r["device_time_us"] or 0.0) * 1e-6
        print(
            "\t".join(
                [
                    str(r["file"]),
                    str(r["num_vectors"]),
                    str(r["level"]),
                    str(r["mode"]),
                    f"{r['recall_at_k']:.4f}" if r["recall_at_k"] is not None else "",
                    f"{r['qps_search']:.1f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.1f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.1f}" if r["effective_qps"] is not None else "",
                    f"{r['compute_time_s']:.3f}" if r["compute_time_s"] is not None else "",
                    f"{device_s:.3f}",
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

    # Fall back to general formatting for small values.
    return f"{v:g}"


def _format_num_vectors(value: Any) -> str:
    """Format num_vectors values like 5000 -> "5k" for axis tick labels."""

    if value is None:
        return ""
    try:
        v = int(value)
    except Exception:
        return str(value)

    if abs(v) >= 1000 and v % 1000 == 0:
        return f"{v // 1000}k"
    return str(v)


def _k_formatter(x: float, _pos: Any) -> str:
    """Adapter for FuncFormatter using _format_k."""

    return _format_k(x)


def make_plots(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Group by hardware level
    levels = sorted({r["level"] for r in rows})

    # Distinct num_vectors values so we can provide consistent, compact
    # tick labels (e.g., 5000 -> "5k").
    num_vec_values = sorted(
        {r["num_vectors"] for r in rows if r["num_vectors"] is not None}
    )

    # Plot effective_qps vs num_vectors for each level (single axes), using
    # the faithful mode as the canonical effective QPS curve. Since faithful
    # and cheated share the same analytic effective_qps, showing both would
    # be redundant.
    fig, ax = plt.subplots(figsize=(8, 4))
    level_order = sorted(levels)
    markers = ["o", "s", "^", "D", "v"]
    linestyles = ["-", "--"]

    for idx, level in enumerate(level_order):
        sub = [r for r in rows if r["level"] == level and r["mode"] == "faithful"]
        if not sub:
            continue
        sub = sorted(sub, key=lambda x: x["num_vectors"] or 0)
        xs = [r["num_vectors"] for r in sub]
        ys = [r["effective_qps"] for r in sub]
        marker = markers[idx % len(markers)]
        linestyle = linestyles[idx % len(linestyles)]
        ax.plot(
            xs,
            ys,
            marker=marker,
            linestyle=linestyle,
            label=str(level),
        )

    # Use compact num_vectors tick labels like 5k/20k/80k.
    if num_vec_values:
        ax.set_xticks(num_vec_values)
        ax.set_xticklabels([_format_num_vectors(v) for v in num_vec_values])

    ax.set_xlabel("Number of Vectors")
    ax.set_ylabel("Effective QPS")
    ax.set_title("Experiment 11: Effective QPS vs Number of Vectors")
    # Show QPS on a k-scaled axis for readability.
    ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
    ax.grid(True, linestyle="--", alpha=0.3)
    if level_order:
        ax.legend(title="Hardware Level", loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "exp11_effective_qps_vs_num_vectors.png", dpi=150)
    plt.close(fig)

    # Also generate a 2x2 grid of per-level effective_qps vs num_vectors
    # plots (one subplot per hardware level) to make the trends easier to
    # see. Each subplot shows the canonical (faithful) effective QPS curve.
    if levels:
        # Share x so the num_vectors ticks align, but let each subplot choose
        # its own y-scale to better show small differences.
        fig, axes = plt.subplots(2, 2, figsize=(10, 8), sharex=True, sharey=False)
        # Ensure deterministic ordering of levels when assigning to subplots.
        level_order = sorted(levels)

        for ax, level in zip(axes.flat, level_order):
            sub = [
                r
                for r in rows
                if r["level"] == level and r["mode"] == "faithful"
            ]
            if not sub:
                continue
            sub = sorted(sub, key=lambda x: x["num_vectors"] or 0)
            xs = [r["num_vectors"] for r in sub]
            ys = [r["effective_qps"] for r in sub]
            ax.plot(xs, ys, marker="o", color="C0")

            ax.set_title(f"Level {level}")
            ax.grid(True, linestyle="--", alpha=0.3)

        # Apply compact num_vectors tick labels on the shared x-axis.
        if num_vec_values:
            for shared_ax in axes[-1, :]:
                shared_ax.set_xticks(num_vec_values)
                shared_ax.set_xticklabels(
                    [_format_num_vectors(v) for v in num_vec_values]
                )

        # Use k-scaled QPS tick labels on each subplot.
        for ax in axes.flat:
            ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))

        # Common axis labels
        fig.supxlabel("Number of Vectors")
        fig.supylabel("Effective QPS")

        fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
        fig.savefig(out_dir / "exp11_effective_qps_vs_num_vectors_by_level.png", dpi=150)
        plt.close(fig)

    # Bar chart: for a fixed num_vectors (20k) and faithful mode, summarize
    # effective_qps and device_time across hardware levels on a dual-axis
    # bar plot. This highlights how hardware capability impacts throughput
    # and modeled device time at a constant dataset size and recall target.
    target_nb = 20000
    faithful_20k = [
        r
        for r in rows
        if r["mode"] == "faithful" and (r["num_vectors"] or 0) == target_nb
    ]
    if faithful_20k:
        faithful_20k = sorted(faithful_20k, key=lambda x: x["level"])
        x_labels = [r["level"] for r in faithful_20k]
        eff = [r["effective_qps"] or 0.0 for r in faithful_20k]
        # Convert device time from microseconds to milliseconds for a more
        # intuitive scale on the plot.
        dev_ms = [(r["device_time_us"] or 0.0) * 1e-3 for r in faithful_20k]

        x = list(range(len(x_labels)))
        width = 0.4

        fig, ax1 = plt.subplots(figsize=(8, 4))
        ax2 = ax1.twinx()

        b1 = ax1.bar(
            [xi - width / 2 for xi in x],
            eff,
            width=width,
            color="C0",
            label="effective QPS",
        )
        b2 = ax2.bar(
            [xi + width / 2 for xi in x],
            dev_ms,
            width=width,
            color="C1",
            label="device time (ms)",
        )

        # Annotate bars with their values so even very small bars remain
        # readable despite axis scaling. Use k-style labels for large values
        # and round smaller QPS values to the nearest integer (e.g., 381.99
        # -> 382).
        for bar in b1:
            height = bar.get_height()
            label_str = _format_k(height)
            if "k" not in label_str:
                try:
                    v = float(height)
                    # Use ceiling-style rounding so small fractional QPS
                    # values (e.g., 381.2 or 381.99) round up to the next
                    # integer for display.
                    label_str = f"{int(math.ceil(v))}"
                except Exception:
                    pass
            ax1.annotate(
                label_str,
                xy=(bar.get_x() + bar.get_width() / 2.0, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        for bar in b2:
            height = bar.get_height()
            ax2.annotate(
                f"{height:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2.0, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        # Add headroom so value labels above the tallest bars do not clip
        # against the top border.
        if eff:
            ax1.set_ylim(0, max(eff) * 1.1)
        if dev_ms:
            ax2.set_ylim(0, max(dev_ms) * 1.1)

        ax1.set_xticks(x)
        ax1.set_xticklabels(x_labels)
        ax1.set_xlabel("Hardware Level")
        ax1.set_ylabel("Effective QPS")
        # Show QPS on a k-scaled axis for readability on the bar chart as well.
        ax1.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax2.set_ylabel("Device Time per Query (ms)")
        ax1.set_title(
            f"Experiment 11: Effective QPS and Device Time per Query vs Hardware Level\n(faithful, num_vectors={target_nb})"
        )

        # Build a combined legend from both axes and place it 
        # below the plot so it does not conflict with the title.
        handles = [b1, b2]
        labels = [h.get_label() for h in handles]
        fig.legend(
            handles,
            labels,
            loc="lower center",
            bbox_to_anchor=(0.5, -0.02),
            ncol=2,
        )

        fig.tight_layout(rect=(0.0, 0.03, 1.0, 1.0))
        fig.savefig(out_dir / "exp11_level_vs_qps_device_time_nb20k.png", dpi=150)
        plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 11 ANN-in-SSD hardware levels.")
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

    # By default, focus on the main hardware-level runs produced by
    # scripts/experiment11.sh. Additional exploratory JSONs (e.g., larger
    # num_base sweeps) can still be analyzed by passing an explicit --glob.
    pattern = args.glob or "results/raw/annssd_nb-*_level-*_mode-*.json"
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

#!/usr/bin/env python3
"""Analysis/plot script for Experiment 5 (SSD Sensitivity).

- Loads JSON result files from results/raw/exp5_*.json.
- Prints a summary table showing device time per query and effective QPS vs SSD parameters.
- Generates simple bar plots vs SSD profile.
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

        num_q = agg.get("num_queries") or cfg.get("num_queries") or 0
        dev_us = agg.get("device_time_us")
        dev_us_per_q = (dev_us / num_q) if dev_us is not None and num_q else None

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
                "mode": cfg.get("mode", ""),
                "ssd_base_latency_us": cfg.get("ssd_base_read_latency_us"),
                "ssd_bw_GBps": cfg.get("ssd_internal_read_bandwidth_GBps"),
                "ssd_num_channels": cfg.get("ssd_num_channels"),
                "ssd_queue_depth": cfg.get("ssd_queue_depth_per_channel"),
                "recall": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "device_time_us": dev_us,
                "device_time_us_per_q": dev_us_per_q,
            }
        )
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No Experiment 5 results to show.")
        return

    headers = [
        "file",
        "mode",
        "lat_us",
        "bw_GBps",
        "ch",
        "qd",
        "recall",
        "qps_search",
        "qps_total",
        "eff_qps",
        "dev_us/q",
    ]

    print("\n=== Experiment 5 Summary (SSD Sensitivity) ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    r["file"],
                    str(r["mode"]),
                    str(r["ssd_base_latency_us"]),
                    str(r["ssd_bw_GBps"]),
                    str(r["ssd_num_channels"]),
                    str(r["ssd_queue_depth"]),
                    f"{r['recall']:.5f}" if r["recall"] is not None else "",
                    f"{r['qps_search']:.3f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.3f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.3f}" if r["effective_qps"] is not None else "",
                    f"{r['device_time_us_per_q']:.2f}" if r["device_time_us_per_q"] is not None else "",
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
        print("[INFO] matplotlib not available; skipping Experiment 5 plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Only tiered runs (SSD-sensitive) for plots.
    tiered = [r for r in rows if r["mode"] == "tiered"]
    if not tiered:
        print("[INFO] No tiered runs to plot.")
        return

    # Sort by base latency (lower latency -> to the right we can interpret as "faster").
    tiered = sorted(tiered, key=lambda r: float(r["ssd_base_latency_us"]))

    labels = [
        f"L={r['ssd_base_latency_us']}µs\nBW={r['ssd_bw_GBps']}GB/s" for r in tiered
    ]
    x = list(range(len(labels)))

    eff_qps = [r["effective_qps"] for r in tiered]
    dev_us_per_q = [r["device_time_us_per_q"] for r in tiered]

    # Plot 1: Effective QPS vs SSD profile
    fig, ax = plt.subplots(figsize=(7, 4))
    bars_qps = ax.bar(x, eff_qps, color="C0")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_ylabel("Effective QPS")
    ax.set_xlabel("SSD Profile (Latency / Bandwidth)")
    ax.set_title("Experiment 5: Effective QPS vs SSD Profile")
    ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
    ax.grid(True, axis="y", alpha=0.3)

    # Add headroom and annotate bars so relative differences remain visible.
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
            f"{height:.1f}",
            xy=(bar.get_x() + bar.get_width() / 2.0, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.35)
    fig.savefig(out_dir / "exp5_effective_qps_vs_ssd_profile.png", dpi=150)
    plt.close(fig)

    # Plot 2: device time per query vs SSD profile
    fig, ax = plt.subplots(figsize=(7, 4))
    bars_dev = ax.bar(x, dev_us_per_q, color="C1")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=0, ha="center")
    ax.set_ylabel("Device Time per Query (µs)")
    ax.set_xlabel("SSD Profile (Latency / Bandwidth)")
    ax.set_title("Experiment 5: Modeled Device Time per Query vs SSD Profile")
    ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
    ax.grid(True, axis="y", alpha=0.3)

    if dev_us_per_q:
        try:
            ymax = max(float(v) for v in dev_us_per_q if v is not None)
            if ymax > 0:
                ax.set_ylim(0, ymax * 1.15)
        except Exception:
            pass

    for bar in bars_dev:
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
    fig.subplots_adjust(bottom=0.35)
    fig.savefig(out_dir / "exp5_device_time_per_query_vs_ssd_profile.png", dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 5 SSD sensitivity results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/exp5_*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/exp5_*.json"
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

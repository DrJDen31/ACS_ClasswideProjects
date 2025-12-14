#!/usr/bin/env python3
"""Analysis/plot script for Experiment 6 (Cost-Performance Trade-off).

- Loads JSON result files from results/raw/exp6_*.json.
- Applies a simple DRAM/SSD cost model.
- Prints a summary table and generates a cost vs effective QPS plot,
  plus an ANN-in-SSD cost-sweep plot.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

try:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:  # pragma: no cover
    HAS_MPL = False

# Simple cost model (can be tuned later).
DRAM_PRICE_PER_GB = 10.0
SSD_PRICE_PER_GB_TIERED = 1.0
ANN_SSD_PRICE_PER_GB_BY_LEVEL = {"L0": 0.8, "L1": 1.0, "L2": 1.5, "L3": 2.0}
ANN_SSD_DRAM_FRACTION = 0.1
BYTES_PER_GB = 1024**3


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

        mode = cfg.get("mode", "")
        num_vec = cfg.get("num_vectors")
        dim = cfg.get("dimension")
        cache_cap = cfg.get("cache_capacity")
        hw_level = cfg.get("hardware_level")

        num_q = agg.get("num_queries")
        build_s = agg.get("build_time_s")
        search_s = agg.get("search_time_s")

        qps_search = agg.get("qps_search")
        if qps_search is None and num_q is not None and search_s is not None:
            try:
                s = float(search_s)
                if s > 0.0:
                    qps_search = float(num_q) / s
            except Exception:
                qps_search = None
        if qps_search is None:
            qps_search = agg.get("qps")

        qps_total = agg.get("qps_total")
        if qps_total is None and num_q is not None and build_s is not None and search_s is not None:
            try:
                t = float(build_s) + float(search_s)
                if t > 0.0:
                    qps_total = float(num_q) / t
            except Exception:
                qps_total = None
        if qps_total is None:
            qps_total = agg.get("qps")

        effective_qps = agg.get("effective_qps")

        approx_index_bytes = None
        if num_vec is not None and dim is not None:
            approx_index_bytes = int(num_vec) * int(dim) * 4  # assume 4 bytes/float

        dram_bytes = None
        ssd_bytes = None
        cache_frac = None

        if approx_index_bytes is not None:
            if mode == "dram":
                dram_bytes = approx_index_bytes
                ssd_bytes = 0
                cache_frac = 1.0
            elif mode == "tiered" and cache_cap is not None:
                cache_frac = float(cache_cap) / float(num_vec) if num_vec else None
                dram_bytes = int(cache_frac * approx_index_bytes) if cache_frac is not None else None
                # Assume full index stored on SSD backing store.
                ssd_bytes = approx_index_bytes
            elif mode == "ann_ssd":
                cache_frac = None
                dram_bytes = int(ANN_SSD_DRAM_FRACTION * approx_index_bytes)
                ssd_bytes = approx_index_bytes

        dram_gb = (dram_bytes / BYTES_PER_GB) if dram_bytes is not None else None
        ssd_gb = (ssd_bytes / BYTES_PER_GB) if ssd_bytes is not None else None

        total_cost = None
        cost_per_qps = None
        ssd_price = None
        if dram_gb is not None and ssd_gb is not None:
            if mode == "tiered":
                ssd_price = SSD_PRICE_PER_GB_TIERED
            elif mode == "ann_ssd":
                level_key = str(hw_level).upper() if hw_level is not None else "L1"
                ssd_price = ANN_SSD_PRICE_PER_GB_BY_LEVEL.get(level_key, ANN_SSD_PRICE_PER_GB_BY_LEVEL["L1"])
            else:
                ssd_price = 0.0
            total_cost = dram_gb * DRAM_PRICE_PER_GB + ssd_gb * ssd_price
            if effective_qps and effective_qps > 0:
                cost_per_qps = total_cost / effective_qps

        rows.append(
            {
                "file": p.name,
                "mode": mode,
                "cache_capacity": cache_cap,
                "cache_frac": cache_frac,
                "hardware_level": hw_level,
                "num_vectors": num_vec,
                "dimension": dim,
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": effective_qps,
                "dram_gb": dram_gb,
                "ssd_gb": ssd_gb,
                "ssd_price_per_gb": ssd_price,
                "total_cost": total_cost,
                "cost_per_qps": cost_per_qps,
            }
        )
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No Experiment 6 results to show.")
        return

    headers = [
        "file",
        "mode",
        "cache_frac",
        "hw_level",
        "dram_gb",
        "ssd_gb",
        "ssd_price_per_gb",
        "total_cost",
        "qps_search",
        "qps_total",
        "eff_qps",
        "cost_per_qps",
    ]

    print("\n=== Experiment 6 Summary (Cost-Performance) ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    r["file"],
                    str(r["mode"]),
                    f"{r['cache_frac']:.3f}" if r["cache_frac"] is not None else "",
                    str(r.get("hardware_level") or ""),
                    f"{r['dram_gb']:.4f}" if r["dram_gb"] is not None else "",
                    f"{r['ssd_gb']:.4f}" if r["ssd_gb"] is not None else "",
                    f"{r['ssd_price_per_gb']:.2f}" if r.get("ssd_price_per_gb") is not None else "",
                    f"{r['total_cost']:.4f}" if r["total_cost"] is not None else "",
                    f"{r['qps_search']:.3f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.3f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.3f}" if r["effective_qps"] is not None else "",
                    f"{r['cost_per_qps']:.6f}" if r["cost_per_qps"] is not None else "",
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


def _dollar_formatter(x: float, _pos) -> str:
    """Format a numeric value as dollars with two decimal places."""

    try:
        v = float(x)
    except Exception:
        return str(x)
    return f"${v:.2f}"


def make_plots(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping Experiment 6 plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Plot cost vs effective QPS for DRAM, tiered, and ANN-in-SSD configurations.
    valid = [r for r in rows if r["total_cost"] is not None and r["effective_qps"] is not None]
    if not valid:
        print("[INFO] No rows with cost and QPS to plot.")
        return

    # Sort by cost for nicer plotting.
    valid = sorted(valid, key=lambda r: float(r["total_cost"]))

    dram_costs: List[float] = []
    dram_qps: List[float] = []
    dram_labels: List[str] = []

    tiered_costs: List[float] = []
    tiered_qps: List[float] = []
    tiered_labels: List[str] = []

    ann_costs: List[float] = []
    ann_qps: List[float] = []
    ann_labels: List[str] = []

    for r in valid:
        total_cost = float(r["total_cost"])
        qps = float(r["effective_qps"])
        mode = str(r["mode"])
        dram_gb = r["dram_gb"]
        ssd_gb = r["ssd_gb"]

        # Interpret the x-axis as an effective media price ($/GB) for the index.
        index_gb = None
        if mode == "dram":
            index_gb = dram_gb
        else:
            index_gb = ssd_gb

        if index_gb is None or index_gb <= 0.0:
            continue

        cost_per_gb = total_cost / float(index_gb)

        if mode == "tiered":
            frac = r["cache_frac"]
            if frac is not None:
                pct = int(round(float(frac) * 100.0))
                label = f"{pct}% Cache"
            else:
                label = "Tiered Cache"
            tiered_costs.append(cost_per_gb)
            tiered_qps.append(qps)
            tiered_labels.append(label)
        elif mode == "ann_ssd":
            lvl = r.get("hardware_level")
            label = str(lvl) if lvl is not None else "ANN-SSD"
            ann_costs.append(cost_per_gb)
            ann_qps.append(qps)
            ann_labels.append(label)
        else:
            label = "DRAM"
            dram_costs.append(cost_per_gb)
            dram_qps.append(qps)
            dram_labels.append(label)

    fig, ax = plt.subplots(figsize=(7, 4))

    handles = []
    if dram_costs:
        h = ax.scatter(dram_costs, dram_qps, color="C0", marker="o", label="DRAM")
        handles.append(h)
    if tiered_costs:
        h = ax.scatter(tiered_costs, tiered_qps, color="C1", marker="s", label="Tiered Cache")
        handles.append(h)
    if ann_costs:
        h = ax.scatter(ann_costs, ann_qps, color="C2", marker="^", label="ANN-in-SSD")
        handles.append(h)

    # Jitter annotation offsets to reduce overlap with points and trend lines.
    offset_patterns = [(6, 6), (6, -10), (-6, 6), (-6, -10), (0, 12), (0, -14)]
    idx = 0

    def _annotate_group(xs: List[float], ys: List[float], texts: List[str], color: str) -> None:
        nonlocal idx
        for x, y, text in zip(xs, ys, texts):
            dx, dy = offset_patterns[idx % len(offset_patterns)]
            idx += 1
            ax.annotate(
                text,
                (x, y),
                textcoords="offset points",
                xytext=(dx, dy),
                fontsize=7,
                color=color,
                bbox={
                    "boxstyle": "round,pad=0.2",
                    "facecolor": "white",
                    "alpha": 0.7,
                    "edgecolor": "none",
                },
            )

    _annotate_group(dram_costs, dram_qps, dram_labels, "C0")
    _annotate_group(tiered_costs, tiered_qps, tiered_labels, "C1")
    _annotate_group(ann_costs, ann_qps, ann_labels, "C2")

    # Simple log-space linear trend per group.
    def _add_trend(xs: List[float], ys: List[float], color: str) -> None:
        if len(xs) < 2:
            return
        if any(y <= 0 for y in ys):
            return
        x_vals = [float(v) for v in xs]
        y_logs = [math.log10(float(v)) for v in ys]
        n = len(x_vals)
        mean_x = sum(x_vals) / n
        mean_y = sum(y_logs) / n
        denom = sum((x - mean_x) ** 2 for x in x_vals)
        if denom <= 0:
            return
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_logs)) / denom
        intercept = mean_y - slope * mean_x
        x_line = [min(x_vals), max(x_vals)]
        y_line = [10 ** (intercept + slope * x) for x in x_line]
        ax.plot(x_line, y_line, linestyle="--", linewidth=1.0, color=color, alpha=0.5)

    _add_trend(dram_costs, dram_qps, "C0")
    _add_trend(tiered_costs, tiered_qps, "C1")
    _add_trend(ann_costs, ann_qps, "C2")

    ax.set_xlabel("Media Price ($/GB)")
    ax.set_ylabel("Effective QPS (log scale)")
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
    ax.xaxis.set_major_formatter(FuncFormatter(_dollar_formatter))
    ax.set_title(
        "Experiment 6: Cost vs Effective QPS\n(DRAM vs Tiered vs ANN-in-SSD)"
    )
    ax.grid(True, which="both", axis="both", alpha=0.3)
    if handles:
        ax.legend(handles=handles, loc="best", fontsize=8, title="Configuration Type")
    fig.tight_layout()
    fig.savefig(out_dir / "exp6_cost_vs_effective_qps.png", dpi=150)
    plt.close(fig)

    # Additional plot: sweep ANN-in-SSD SSD price-per-GB to see when Solution 3 becomes cost-effective.
    ann_rows = [
        r
        for r in rows
        if r["mode"] == "ann_ssd"
        and r["dram_gb"] is not None
        and r["ssd_gb"] is not None
        and r["effective_qps"] is not None
    ]
    if not ann_rows:
        return

    # Baseline best cost-per-QPS across DRAM and tiered runs under fixed pricing.
    baseline_rows = [
        r
        for r in rows
        if r["mode"] != "ann_ssd" and r["cost_per_qps"] is not None
    ]
    baseline_best = None
    if baseline_rows:
        baseline_best = min(r["cost_per_qps"] for r in baseline_rows)

    price_min = 0.5
    price_max = 5.0
    num_points = 100

    # Precompute baseline in cost-per-1k-QPS units.
    baseline_best_1k = baseline_best * 1000.0 if baseline_best is not None else None

    # Simple average SSD media price across the model constants.
    ssd_price_values = [SSD_PRICE_PER_GB_TIERED]
    ssd_price_values.extend(ANN_SSD_PRICE_PER_GB_BY_LEVEL.values())
    avg_ssd_price = sum(ssd_price_values) / float(len(ssd_price_values))

    # Organize ANN-SSD rows by hardware level for per-level subplots.
    rows_by_level: Dict[str, Dict[str, Any]] = {}
    for r in ann_rows:
        lvl_key = str(r.get("hardware_level"))
        rows_by_level[lvl_key] = r

    levels = ["L0", "L1", "L2", "L3"]
    fig2, axes = plt.subplots(2, 2, figsize=(8, 6), sharey=True)
    axes_flat = axes.flatten()

    for idx, lvl in enumerate(levels):
        ax2 = axes_flat[idx]
        row = rows_by_level.get(lvl)
        if row is None:
            ax2.set_visible(False)
            continue

        dram_gb = row["dram_gb"]
        ssd_gb = row["ssd_gb"]
        eff_qps = row["effective_qps"]
        if (
            dram_gb is None
            or ssd_gb is None
            or eff_qps is None
            or eff_qps <= 0.0
        ):
            ax2.set_visible(False)
            continue

        # Linear model: cost_per_1k(p) = m * p + b, where p is media $/GB.
        m = (ssd_gb * 1000.0) / float(eff_qps)
        b = (dram_gb * DRAM_PRICE_PER_GB * 1000.0) / float(eff_qps)

        # Intersection with the best DRAM/tiered baseline, if available.
        p_star = None
        y_star = None
        if baseline_best_1k is not None and m > 0.0:
            if baseline_best_1k > b:
                p_star = (baseline_best_1k - b) / m
                if p_star > 0.0:
                    y_star = baseline_best_1k

        # Choose an x-range and try to place the intersection around 80% of the axis
        # when the intersection is finite and positive.
        x_min = price_min
        x_max = price_max
        if p_star is not None:
            target_x_max = p_star / 0.8
            if target_x_max > x_max:
                x_max = target_x_max

        # Sample the line over this range.
        xs = [x_min + (x_max - x_min) * i / (num_points - 1) for i in range(num_points)]
        ys = [m * x + b for x in xs]
        ax2.plot(xs, ys, color="C2", label=f"ANN-SSD {lvl}")

        # Draw the DRAM/tiered best baseline as a horizontal dashed line.
        if baseline_best_1k is not None:
            ax2.axhline(
                baseline_best_1k,
                color="k",
                linestyle="--",
                linewidth=1.0,
                label="Best DRAM/Tiered",
            )

        # Mark the intersection point when it lies within the visible range, but
        # keep it out of the legend (no text label).
        if p_star is not None and y_star is not None and x_min <= p_star <= x_max:
            ax2.scatter(
                [p_star],
                [y_star],
                color="C3",
                s=20,
                zorder=3,
                label="_nolegend_",
            )

        # Vertical reference lines for DRAM and average SSD prices (slightly darker).
        dram_line = ax2.axvline(
            DRAM_PRICE_PER_GB,
            color="C0",
            linestyle=":",
            linewidth=1.3,
            alpha=0.9,
            label="DRAM Price",
        )
        ssd_line = ax2.axvline(
            avg_ssd_price,
            color="C1",
            linestyle=":",
            linewidth=1.3,
            alpha=0.9,
            label="Avg SSD Price",
        )

        ax2.set_xlim(x_min, x_max)
        if idx % 2 == 0:
            ax2.set_ylabel("Cost per Effective 1k QPS ($)")
        ax2.set_xlabel("Media Price ($/GB)")
        ax2.set_title(f"ANN-SSD {lvl}")
        ax2.xaxis.set_major_formatter(FuncFormatter(_dollar_formatter))
        ax2.yaxis.set_major_formatter(FuncFormatter(_dollar_formatter))

        # Use log x-scale for higher-performance levels where the interesting
        # region may span a wider price range.
        if lvl in ("L2", "L3"):
            ax2.set_xscale("log")

        ax2.grid(True, which="both", axis="both", alpha=0.3)

        # Per-subplot legend including ANN-SSD line, baseline, and vertical
        # reference lines. The break-even marker is excluded via its
        # ``_nolegend_`` label above.
        ax2.legend(fontsize=7, loc="best")
    fig2.tight_layout()
    fig2.savefig(out_dir / "exp6_annssd_cost_sweep.png", dpi=150)
    plt.close(fig2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 6 cost-performance results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/exp6_*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/exp6_*.json"
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

#!/usr/bin/env python3
"""Analysis/plot script for Experiment 4 (I/O Amplification vs Cache Size).

- Loads JSON result files from results/raw/exp4_*.json.
- Prints a summary table showing I/Os per query vs cache size.
- Generates plots of reads/bytes/device_time per query vs cache fraction (tiered runs).
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
        num_vec = cfg.get("num_vectors")
        cache_cap = cfg.get("cache_capacity")

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

        reads = io.get("num_reads")
        bytes_read = io.get("bytes_read")
        dev_us = agg.get("device_time_us")

        reads_per_q = (reads / num_q) if reads is not None and num_q else None
        bytes_per_q = (bytes_read / num_q) if bytes_read is not None and num_q else None
        dev_us_per_q = (dev_us / num_q) if dev_us is not None and num_q else None

        cache_frac = None
        if cache_cap is not None and num_vec:
            cache_frac = float(cache_cap) / float(num_vec)

        rows.append(
            {
                "file": p.name,
                "mode": cfg.get("mode", ""),
                "cache_capacity": cache_cap,
                "cache_frac": cache_frac,
                "num_vectors": num_vec,
                "recall": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "reads": reads,
                "bytes_read": bytes_read,
                "device_time_us": dev_us,
                "reads_per_q": reads_per_q,
                "bytes_per_q": bytes_per_q,
                "device_time_us_per_q": dev_us_per_q,
            }
        )
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No Experiment 4 results to show.")
        return

    headers = [
        "file",
        "mode",
        "cache_cap",
        "cache_frac",
        "recall",
        "qps_search",
        "qps_total",
        "eff_qps",
        "reads/q",
        "bytes/q",
        "dev_us/q",
    ]

    print("\n=== Experiment 4 Summary (I/O Amplification vs Cache Size) ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    r["file"],
                    str(r["mode"]),
                    str(r["cache_capacity"]),
                    f"{r['cache_frac']:.3f}" if r["cache_frac"] is not None else "",
                    f"{r['recall']:.5f}" if r["recall"] is not None else "",
                    f"{r['qps_search']:.3f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.3f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.3f}" if r["effective_qps"] is not None else "",
                    f"{r['reads_per_q']:.1f}" if r["reads_per_q"] is not None else "",
                    f"{r['bytes_per_q']:.1f}" if r["bytes_per_q"] is not None else "",
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
        print("[INFO] matplotlib not available; skipping Experiment 4 plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Only tiered runs with defined cache fraction and I/O make sense for these plots.
    tiered = [
        r
        for r in rows
        if r["mode"] == "tiered" and r["cache_frac"] is not None and r["reads_per_q"] is not None
    ]
    if not tiered:
        print("[INFO] No tiered runs with cache_frac to plot.")
        return

    tiered = sorted(tiered, key=lambda r: float(r["cache_frac"]))
    x = [float(r["cache_frac"]) for r in tiered]
    reads_per_q = [r["reads_per_q"] for r in tiered]
    bytes_per_q = [r["bytes_per_q"] for r in tiered]
    dev_us_per_q = [r["device_time_us_per_q"] for r in tiered]

    # Plot 1: reads per query vs cache fraction
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x, reads_per_q, marker="o", color="C0")
    ax.set_xlabel("Cache Fraction (Capacity / Num Vectors)")
    ax.set_ylabel("Reads per Query")
    ax.set_title("Experiment 4: Reads per Query vs Cache Fraction")
    ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "exp4_reads_per_query_vs_cache_frac.png", dpi=150)
    plt.close(fig)

    # Plot 2: bytes per query vs cache fraction (reported in MiB/query for
    # readability).
    fig, ax = plt.subplots(figsize=(6, 4))
    mib_per_q = [
        (b / (1024.0 * 1024.0)) if b is not None else None
        for b in bytes_per_q
    ]
    ax.plot(x, mib_per_q, marker="o", color="C1")
    ax.set_xlabel("Cache Fraction (Capacity / Num Vectors)")
    ax.set_ylabel("MiB per Query")
    ax.set_title("Experiment 4: MiB per Query vs Cache Fraction")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "exp4_bytes_per_query_vs_cache_frac.png", dpi=150)
    plt.close(fig)

    # Plot 3: device time per query vs cache fraction (if available)
    if any(v is not None for v in dev_us_per_q):
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.plot(x, dev_us_per_q, marker="o", color="C2")
        ax.set_xlabel("Cache Fraction (Capacity / Num Vectors)")
        ax.set_ylabel("Device Time per Query (µs)")
        ax.set_title("Experiment 4: Modeled Device Time per Query vs Cache Fraction")
        ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "exp4_device_time_per_query_vs_cache_frac.png", dpi=150)
        plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 4 I/O amplification results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/exp4_*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/exp4_*.json"
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

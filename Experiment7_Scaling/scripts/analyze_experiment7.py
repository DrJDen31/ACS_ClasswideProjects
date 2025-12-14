#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

try:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:
    HAS_MPL = False

BYTES_PER_GB = 1024**3


def load_results(paths: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for p in paths:
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load {p}: {e}")
            continue

        cfg = data.get("config", {})
        agg = data.get("aggregate", {})

        mode = cfg.get("mode")
        num_vec = cfg.get("num_vectors")
        dim = cfg.get("dimension")
        cache_cap = cfg.get("cache_capacity")

        build_s = agg.get("build_time_s")
        search_s = agg.get("search_time_s")
        num_q = agg.get("num_queries")

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
        recall = agg.get("recall_at_k")

        approx_index_bytes = None
        if num_vec is not None and dim is not None:
            approx_index_bytes = int(num_vec) * int(dim) * 4

        cache_frac = None
        if mode == "tiered" and num_vec and cache_cap is not None:
            cache_frac = float(cache_cap) / float(num_vec)

        rows.append(
            {
                "file": p.name,
                "mode": mode,
                "num_vectors": num_vec,
                "dimension": dim,
                "cache_capacity": cache_cap,
                "cache_frac": cache_frac,
                "build_time_s": build_s,
                "search_time_s": search_s,
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": effective_qps,
                "recall_at_k": recall,
                "approx_index_gb": (approx_index_bytes / BYTES_PER_GB) if approx_index_bytes else None,
            }
        )

    rows.sort(key=lambda r: (int(r["num_vectors"] or 0), str(r["mode"])))
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No Experiment 7 results to show.")
        return

    headers = [
        "file",
        "mode",
        "num_vectors",
        "cache_frac",
        "build_s",
        "qps_search",
        "qps_total",
        "eff_qps",
        "recall",
        "approx_index_gb",
    ]

    print("\n=== Experiment 7 Summary (Scaling) ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    r["file"],
                    str(r["mode"]),
                    str(r["num_vectors"]),
                    f"{r['cache_frac']:.3f}" if r["cache_frac"] is not None else "",
                    f"{r['build_time_s']:.3f}" if r["build_time_s"] is not None else "",
                    f"{r['qps_search']:.3f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.3f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.3f}" if r["effective_qps"] is not None else "",
                    f"{r['recall_at_k']:.5f}" if r["recall_at_k"] is not None else "",
                    f"{r['approx_index_gb']:.3f}" if r["approx_index_gb"] is not None else "",
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


def _mode_label(mode: Any) -> str:
    """Normalize mode labels for legends."""

    m = str(mode).lower()
    if m == "dram":
        return "DRAM"
    if m == "tiered":
        return "Tiered Cache"
    if m in {"ann_ssd", "annssd", "ann-ssd"}:
        return "ANN-in-SSD"
    return str(mode)


def make_plots(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping Experiment 7 plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    valid = [r for r in rows if r["num_vectors"] and r["build_time_s"] is not None]
    if valid:
        fig, ax = plt.subplots(figsize=(7, 4))
        for mode in sorted(set(r["mode"] for r in valid)):
            pts = [r for r in valid if r["mode"] == mode]
            x = [int(r["num_vectors"]) for r in pts]
            y = [float(r["build_time_s"]) for r in pts]
            ax.plot(x, y, marker="o", label=_mode_label(mode))
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("Number of Vectors")
        ax.set_ylabel("Build Time (s)")
        ax.set_title("Experiment 7: Build Time vs Dataset Size")
        ax.xaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax.grid(True, which="both", axis="both", alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_dir / "exp7_build_time_vs_num_vectors.png", dpi=150)
        plt.close(fig)

    valid = [r for r in rows if r["num_vectors"] and r["effective_qps"] is not None]
    if valid:
        fig, ax = plt.subplots(figsize=(7, 4))
        for mode in sorted(set(r["mode"] for r in valid)):
            pts = [r for r in valid if r["mode"] == mode]
            x = [int(r["num_vectors"]) for r in pts]
            y = [float(r["effective_qps"]) for r in pts]
            ax.plot(x, y, marker="o", label=_mode_label(mode))
        ax.set_xscale("log")
        ax.set_xlabel("Number of Vectors")
        ax.set_ylabel("Effective QPS")
        ax.set_title("Experiment 7: Effective QPS vs Dataset Size")
        ax.xaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax.grid(True, which="both", axis="both", alpha=0.3)
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out_dir / "exp7_effective_qps_vs_num_vectors.png", dpi=150)
        plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 7 scaling results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/exp7_*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/exp7_*.json"
    paths = sorted(exp_dir.glob(pattern))
    if not paths:
        print(f"No JSON files found for pattern: {exp_dir / pattern}")
        return 0

    rows = load_results(paths)
    print_table(rows)

    plots_dir = exp_dir / "results" / "plots"
    make_plots(rows, plots_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

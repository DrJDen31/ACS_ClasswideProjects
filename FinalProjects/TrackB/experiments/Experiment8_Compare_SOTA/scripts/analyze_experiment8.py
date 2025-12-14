#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import FuncFormatter

    HAS_MPL = True
except Exception:
    HAS_MPL = False


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


def _k_formatter_precise(x: float, _pos) -> str:
    """Formatter for QPS axes that keeps two decimal places in the k-range.

    Examples: 1426 -> "1.43k".
    """

    try:
        v = float(x)
    except Exception:
        return str(x)

    if abs(v) >= 1000.0:
        return f"{v / 1000.0:.2f}k"

    # For smaller values, keep integer-style labels when possible.
    if abs(v) >= 10.0:
        return f"{v:.0f}"
    return f"{v:g}"


def _mode_label(mode: Any) -> str:
    """Normalize mode labels for legends."""

    m = str(mode).lower()
    if m == "dram":
        return "DRAM"
    if m == "tiered":
        return "Tiered Cache"
    if m in {"ann_ssd", "annssd", "ann-ssd"}:
        return "ANN-in-SSD"
    if m == "hnswlib":
        return "HNSWlib"
    return str(mode)


def _load(paths: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[WARN] Failed to load {p}: {e}")
            continue
        cfg = data.get("config", {})
        agg = data.get("aggregate", {})

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

        rows.append(
            {
                "file": p.name,
                "mode": cfg.get("mode"),
                "num_vectors": cfg.get("num_vectors"),
                "num_queries": num_q,
                "recall_at_k": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "build_time_s": agg.get("build_time_s"),
                "latency_us_p50": agg.get("latency_us_p50"),
                "latency_us_p95": agg.get("latency_us_p95"),
                "latency_us_p99": agg.get("latency_us_p99"),
            }
        )
    rows.sort(key=lambda r: (int(r["num_vectors"] or 0), str(r["mode"])))
    return rows


def _print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No Experiment 8 results to show.")
        return

    headers = [
        "file",
        "mode",
        "num_vectors",
        "num_queries",
        "build_s",
        "qps_search",
        "qps_total",
        "eff_qps",
        "recall",
        "p50_us",
        "p95_us",
        "p99_us",
    ]

    print("\n=== Experiment 8 Summary (Compare SOTA) ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    r["file"],
                    str(r["mode"]),
                    str(r["num_vectors"]),
                    str(r["num_queries"]),
                    f"{r['build_time_s']:.3f}" if r["build_time_s"] is not None else "",
                    f"{r['qps_search']:.3f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.3f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.3f}" if r["effective_qps"] is not None else "",
                    f"{r['recall_at_k']:.5f}" if r["recall_at_k"] is not None else "",
                    f"{r['latency_us_p50']:.2f}" if r["latency_us_p50"] is not None else "",
                    f"{r['latency_us_p95']:.2f}" if r["latency_us_p95"] is not None else "",
                    f"{r['latency_us_p99']:.2f}" if r["latency_us_p99"] is not None else "",
                ]
            )
        )


def _plot_recall_qps(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        return
    pts = [
        r
        for r in rows
        if r["num_vectors"] is not None
        and r["effective_qps"] is not None
        and r["recall_at_k"] is not None
    ]
    if not pts:
        return

    fig, ax_recall = plt.subplots(figsize=(7, 4))
    ax_qps = ax_recall.twinx()

    modes = sorted(set(str(r["mode"]) for r in pts))
    colors = ["C0", "C1", "C2", "C3", "C4"]

    handles: List[Any] = []
    labels: List[str] = []

    for idx, mode in enumerate(modes):
        color = colors[idx % len(colors)]
        mpts = sorted(
            [r for r in pts if str(r["mode"]) == mode],
            key=lambda r: int(r["num_vectors"] or 0),
        )
        x = [int(r["num_vectors"]) for r in mpts]
        y_recall = [float(r["recall_at_k"]) for r in mpts]
        y_qps = [float(r["effective_qps"]) for r in mpts]

        # Draw recall as a line at the true positions, and jitter only the
        # marker x-positions slightly so overlapping series remain visible.
        h1 = ax_recall.plot(
            x,
            y_recall,
            color=color,
            linestyle="-",
            linewidth=1.5,
            label=f"{_mode_label(mode)} – Recall @ k",
        )[0]

        span = max(x) - min(x) if len(x) > 1 else 0.0
        offset_unit = 0.02 * span if span > 0.0 and len(modes) > 1 else 0.0
        offset = (idx - (len(modes) - 1) / 2.0) * offset_unit
        x_markers = [xi + offset for xi in x]

        ax_recall.scatter(
            x_markers,
            y_recall,
            marker="o",
            s=35,
            facecolors="none" if idx % 2 == 1 else color,
            edgecolors=color,
            linewidths=1.0,
            zorder=3 + idx,
            label="_nolegend_",
        )

        h2 = ax_qps.plot(
            x,
            y_qps,
            marker="s",
            color=color,
            linestyle="--",
            label=f"{_mode_label(mode)} – Effective QPS",
        )[0]
        handles.extend([h1, h2])
        labels.extend([h1.get_label(), h2.get_label()])

    ax_recall.set_xlabel("Number of Vectors")
    ax_recall.set_ylabel("Recall @ k")
    ax_qps.set_ylabel("Effective QPS")

    ax_recall.set_ylim(0.0, 1.05)

    ax_recall.xaxis.set_major_formatter(FuncFormatter(_k_formatter))
    ax_qps.yaxis.set_major_formatter(FuncFormatter(_k_formatter_precise))

    ax_recall.set_title("Experiment 8: Recall and Effective QPS vs Dataset Size")
    ax_recall.grid(True, which="both", axis="both", alpha=0.3)

    if handles:
        ax_recall.legend(handles, labels, loc="best", fontsize=8)

    fig.tight_layout()
    fig.savefig(out_dir / "exp8_recall_vs_effective_qps.png", dpi=150)
    plt.close(fig)


def _plot_build_scaling(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        return
    pts = [r for r in rows if r["num_vectors"] is not None and r["build_time_s"] is not None]
    if not pts:
        return

    fig, ax = plt.subplots(figsize=(7, 4))
    for mode in sorted(set(str(r["mode"]) for r in pts)):
        mpts = sorted(
            [r for r in pts if str(r["mode"]) == mode],
            key=lambda r: int(r["num_vectors"] or 0),
        )
        x = [int(r["num_vectors"]) for r in mpts]
        y = [float(r["build_time_s"]) for r in mpts]
        ax.plot(x, y, marker="o", label=_mode_label(mode))

    ax.set_xlabel("Number of Vectors")
    ax.set_ylabel("Build Time (s)")
    ax.set_title("Experiment 8: Build Time vs Dataset Size")

    ax.xaxis.set_major_formatter(FuncFormatter(_k_formatter))
    ax.yaxis.set_major_formatter(FuncFormatter(_k_formatter))

    ax.grid(True, which="both", axis="both", alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "exp8_build_time_vs_num_vectors.png", dpi=150)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 8 SOTA comparison results.")
    parser.add_argument(
        "--glob",
        type=str,
        default=None,
        help=(
            "Glob pattern for JSON files, interpreted relative to the experiment "
            "directory (default: results/raw/exp8_*.json)"
        ),
    )
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/exp8_*.json"
    paths = sorted(exp_dir.glob(pattern))
    if not paths:
        print(f"No JSON files found for pattern: {exp_dir / pattern}")
        return 0

    rows = _load(paths)
    _print_table(rows)

    out_dir = exp_dir / "results" / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    _plot_recall_qps(rows, out_dir)
    _plot_build_scaling(rows, out_dir)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

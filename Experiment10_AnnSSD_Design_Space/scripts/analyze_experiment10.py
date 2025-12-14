#!/usr/bin/env python3
"""Analysis/plot script for Experiment 10 (ANN-SSD design space).

Loads JSON logs from results/raw, prints a summary table, and generates
plots of recall/effective QPS vs design knobs (K, max_steps, portal_degree).

Usage (from experiment dir, inside WSL):

  cd experiments/Experiment10_AnnSSD_Design_Space
  python scripts/analyze_experiment10.py
"""

import argparse
import json
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

        num_q = agg.get("num_queries") or cfg.get("num_queries") or 0
        search_s = agg.get("search_time_s")
        build_s = agg.get("build_time_s")

        qps_search = agg.get("qps_search")
        if qps_search is None and num_q and search_s is not None:
            try:
                s = float(search_s)
                if s > 0.0:
                    qps_search = float(num_q) / s
            except Exception:
                qps_search = None
        if qps_search is None:
            qps_search = agg.get("qps")

        qps_total = agg.get("qps_total")
        if qps_total is None and num_q and build_s is not None and search_s is not None:
            try:
                b = float(build_s)
                s = float(search_s)
                if (b + s) > 0.0:
                    qps_total = float(num_q) / (b + s)
            except Exception:
                qps_total = None
        if qps_total is None:
            qps_total = agg.get("qps")

        rows.append(
            {
                "file": p.name,
                "Kpb": cfg.get("vectors_per_block"),
                "max_steps": cfg.get("max_steps"),
                "portal_degree": cfg.get("portal_degree"),
                "k": agg.get("k"),
                "num_queries": agg.get("num_queries"),
                "recall_at_k": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "avg_blocks_visited": agg.get("avg_blocks_visited"),
                "avg_distances_computed": agg.get("avg_distances_computed"),
                "device_time_us": agg.get("device_time_us"),
            }
        )
    return rows


def print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No results to show.")
        return

    headers = [
        "file",
        "Kpb",
        "max_steps",
        "P",
        "recall",
        "qps_search",
        "qps_total",
        "eff_qps",
        "avg_blocks",
    ]

    print("\n=== Experiment 10 Summary ===")
    print("\t".join(headers))
    for r in sorted(rows, key=lambda x: (x["Kpb"], x["max_steps"], x["portal_degree"])):
        print(
            "\t".join(
                [
                    str(r["file"]),
                    str(r["Kpb"]),
                    str(r["max_steps"]),
                    str(r["portal_degree"]),
                    f"{r['recall_at_k']:.4f}" if r["recall_at_k"] is not None else "",
                    f"{r['qps_search']:.1f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.1f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.1f}" if r["effective_qps"] is not None else "",
                    f"{r['avg_blocks_visited']:.1f}" if r["avg_blocks_visited"] is not None else "",
                ]
            )
        )


def print_recall_matched(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    targets = [0.85, 0.95, 0.99]
    headers = ["target_recall", "Kpb", "max_steps", "P", "recall", "eff_qps", "file"]
    print("\n=== Experiment 10 Recall-Matched Summary (max effective_qps) ===")
    print("\t".join(headers))

    for t in targets:
        best = None
        for r in rows:
            rec = r.get("recall_at_k")
            q = r.get("effective_qps")
            if rec is None or q is None:
                continue
            try:
                if float(rec) < float(t):
                    continue
            except Exception:
                continue
            if best is None or float(q) > float(best.get("effective_qps") or 0.0):
                best = r

        if best is None:
            print("\t".join([f"{t:.2f}", "", "", "", "", "", ""]))
        else:
            print(
                "\t".join(
                    [
                        f"{t:.2f}",
                        str(best.get("Kpb")),
                        str(best.get("max_steps")),
                        str(best.get("portal_degree")),
                        f"{float(best['recall_at_k']):.4f}",
                        f"{float(best['effective_qps']):.1f}",
                        str(best.get("file") or ""),
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
        print("[INFO] matplotlib not available; skipping plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    def _plot_for_subset(sub_rows: List[Dict[str, Any]], P: int, suffix: str) -> None:
        if not sub_rows:
            return

        # Filter rows that have the metrics required for plotting.
        valid_rows = [
            r
            for r in sub_rows
            if r.get("max_steps") is not None
            and r.get("effective_qps") is not None
            and r.get("recall_at_k") is not None
        ]
        if not valid_rows:
            return

        # Build a consistent ordering of max_steps values for this subset,
        # treating max_steps == 0 as a "full scan" configuration that should
        # appear at the *right* of the axis even though its numeric value is 0.
        # We preserve approximate spacing in terms of the underlying step
        # counts by mapping full-scan to a position slightly beyond the largest
        # nonzero max_steps.
        def _step_sort_key(ms: int) -> tuple:
            v = int(ms)
            return (v == 0, v)

        step_values = {int(r["max_steps"] or 0) for r in valid_rows}
        has_full = 0 in step_values
        nonzero_steps = sorted(s for s in step_values if s != 0)
        max_nonzero = nonzero_steps[-1] if nonzero_steps else 1

        def _to_x(ms: int) -> float:
            v = int(ms)
            if v == 0 and has_full:
                # Place full-scan slightly to the right of the largest
                # nonzero step so lines connect monotonically along the
                # horizontal axis while visually indicating "max work".
                return float(max_nonzero) * 1.05
            return float(v)

        unique_steps = sorted(step_values, key=_step_sort_key)
        step_to_x = {ms: _to_x(ms) for ms in unique_steps}

        # For the main P=1/2/4 plots, use two vertically stacked subplots so
        # effective QPS and recall each get their own y-axis. For the dense
        # K=128 sweep (suffix "_K128"), keep a dual-axis layout but still share
        # consistent x-axis semantics.
        if suffix == "_K128":
            fig, ax_qps = plt.subplots(figsize=(8, 4))
            ax_rec = ax_qps.twinx()
        else:
            fig, (ax_qps, ax_rec) = plt.subplots(2, 1, sharex=True, figsize=(8, 6))

        handles = []
        labels = []

        for Kpb in sorted({r["Kpb"] for r in valid_rows}):
            subK = [r for r in valid_rows if r["Kpb"] == Kpb]
            if not subK:
                continue

            # Ensure that lines connect points in increasing work order,
            # with the full-scan configuration (max_steps=0) appearing last.
            subK_sorted = sorted(
                subK, key=lambda r: _step_sort_key(int(r["max_steps"] or 0))
            )

            xs = [step_to_x[int(r["max_steps"] or 0)] for r in subK_sorted]
            ys_qps = [float(r["effective_qps"]) for r in subK_sorted]
            ys_rec = [float(r["recall_at_k"]) for r in subK_sorted]

            # For the dense K=128 sweep plot (suffix '_K128'), fix colors so
            # QPS and recall are visually distinct. For other plots, reuse the
            # color for both curves of a given Kpb.
            if suffix == "_K128":
                qps_color = "C0"
                rec_color = "C1"
            else:
                qps_color = None
                rec_color = None

            line_qps, = ax_qps.plot(
                xs,
                ys_qps,
                marker="o",
                color=qps_color,
                label=f"K={Kpb} eff_qps",
            )
            if rec_color is None:
                rec_color = line_qps.get_color()
            line_rec, = ax_rec.plot(
                xs,
                ys_rec,
                marker="s",
                linestyle="--",
                color=rec_color,
                label=f"K={Kpb} recall",
            )
            handles.extend([line_qps, line_rec])
            labels.extend([f"K={Kpb} eff_qps", f"K={Kpb} recall"])

        if suffix == "_K128":
            ax_qps.set_xlabel("Max Steps (approx. % of full-scan blocks)")
        else:
            ax_rec.set_xlabel("Max Steps")

        ax_qps.set_ylabel("Effective QPS")
        ax_rec.set_ylabel("Recall @ k")

        ax_qps.yaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax_rec.set_ylim(0.0, 1.05)

        ax_qps.set_title(
            f"Experiment 10: Effective QPS and Recall vs Max Steps\n(P={P}{suffix})"
        )
        ax_qps.grid(True, linestyle="--", alpha=0.3)

        # For the K=128 sweep plot, annotate a subset of x ticks with percentage
        # of full-scan blocks using avg_blocks_visited at max_steps=0 as the
        # baseline, and label the full-scan configuration explicitly.
        if suffix == "_K128":
            # Map max_steps -> avg_blocks_visited for this subset
            blocks_by_step = {}
            for r in valid_rows:
                ms = r.get("max_steps")
                ab = r.get("avg_blocks_visited")
                if ms is None or ab is None:
                    continue
                try:
                    ms_i = int(ms)
                    blocks_by_step[ms_i] = float(ab)
                except Exception:
                    continue

            full_blocks = None
            if 0 in blocks_by_step and blocks_by_step[0] > 0.0:
                full_blocks = blocks_by_step[0]
            else:
                # Fallback: use the maximum observed avg_blocks_visited as an
                # approximation of full-scan.
                if blocks_by_step:
                    full_blocks = max(blocks_by_step.values())

            if full_blocks and full_blocks > 0.0:
                xs_all = sorted(blocks_by_step.keys(), key=_step_sort_key)
                # Subsample ticks to avoid overcrowding: aim for at most ~10
                # labeled positions including the smallest step and full scan.
                if len(xs_all) > 10:
                    step = max(1, len(xs_all) // 10)
                    xs_ticks = xs_all[::step]
                    if xs_all[-1] not in xs_ticks:
                        xs_ticks.append(xs_all[-1])
                    xs_ticks = sorted(set(xs_ticks), key=_step_sort_key)
                else:
                    xs_ticks = xs_all

                tick_positions = [step_to_x[ms] for ms in xs_ticks]
                tick_labels = []
                for ms in xs_ticks:
                    frac = blocks_by_step[ms] / full_blocks
                    pct = int(round(frac * 100))
                    if ms == 0:
                        tick_labels.append(f"full\n{pct}%")
                    else:
                        tick_labels.append(f"{ms}\n{pct}%")
                ax_qps.set_xticks(tick_positions)
                ax_qps.set_xticklabels(tick_labels, fontsize=7)
        else:
            # Generic plots: label the x-axis categories by max_steps, with a
            # special label for the full-scan configuration.
            xticks = [step_to_x[ms] for ms in unique_steps]
            tick_labels = ["full" if ms == 0 else str(ms) for ms in unique_steps]
            ax_rec.set_xticks(xticks)
            ax_rec.set_xticklabels(tick_labels, rotation=0, ha="center", fontsize=8)

        if handles:
            if suffix == "_K128":
                # Move legend above the plot area to avoid overlapping lines.
                ax_qps.legend(
                    handles,
                    labels,
                    loc="upper center",
                    bbox_to_anchor=(0.5, 0.98),
                    ncol=2,
                    fontsize=8,
                )
            else:
                ax_qps.legend(handles, labels, loc="best", fontsize=8)

        fig.tight_layout()
        fig.savefig(out_dir / f"exp10_qps_recall_vs_max_steps_P{P}{suffix}.png", dpi=150)
        plt.close(fig)

    portal_degrees = sorted({r["portal_degree"] for r in rows if r.get("portal_degree") is not None})
    for P in portal_degrees:
        sub = [r for r in rows if r["portal_degree"] == P]
        if not sub:
            continue

        # For P=2, split Kpb=128 (100k sweep) into its own plot to avoid clutter
        # and keep comparison plots focused.
        if P == 2:
            sub_k128 = [r for r in sub if r.get("Kpb") == 128]
            sub_other = [r for r in sub if r.get("Kpb") != 128]

            if sub_other:
                _plot_for_subset(sub_other, P, "")
            if sub_k128:
                _plot_for_subset(sub_k128, P, "_K128")
        else:
            _plot_for_subset(sub, P, "")

    # Additional plots: recall vs effective QPS per portal degree, with each
    # point labeled by max_steps. Treat max_steps == 0 (full scan) as the
    # highest-work configuration and place it at the end of each curve.
    for P in portal_degrees:
        subP = [
            r
            for r in rows
            if r.get("portal_degree") == P
            and r.get("effective_qps") is not None
            and r.get("recall_at_k") is not None
            and r.get("max_steps") is not None
        ]
        if not subP:
            continue

        fig, ax = plt.subplots(figsize=(7, 4))

        def _step_sort_key(ms: int) -> tuple:
            v = int(ms)
            return (v == 0, v)

        handles = []
        labels = []

        for Kpb in sorted({r["Kpb"] for r in subP}):
            subK = [r for r in subP if r["Kpb"] == Kpb]
            if not subK:
                continue

            subK_sorted = sorted(
                subK, key=lambda r: _step_sort_key(int(r["max_steps"] or 0))
            )
            xs = [float(r["effective_qps"]) for r in subK_sorted]
            ys = [float(r["recall_at_k"]) for r in subK_sorted]
            steps = [int(r["max_steps"] or 0) for r in subK_sorted]

            line, = ax.plot(
                xs,
                ys,
                marker="o",
                label=f"K={Kpb}",
            )
            handles.append(line)
            labels.append(f"K={Kpb}")

            # Max-steps annotations are disabled to keep the plot uncluttered;
            # max_steps trends are conveyed via the separate QPS-vs-max_steps
            # figures for P=1/2/4.

        ax.set_xlabel("Effective QPS")
        ax.set_ylabel("Recall @ k")
        ax.xaxis.set_major_formatter(FuncFormatter(_k_formatter))
        ax.set_ylim(0.0, 1.05)
        ax.grid(True, alpha=0.3)
        ax.set_title(
            f"Experiment 10: Recall vs Effective QPS\n(P={P})"
        )

        if handles:
            ax.legend(handles, labels, loc="best", fontsize=8)

        fig.tight_layout()
        fig.savefig(out_dir / f"exp10_recall_vs_effective_qps_P{P}.png", dpi=150)
        plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 10 results.")
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

    pattern = args.glob or "results/raw/*.json"
    paths = sorted(exp_dir.glob(pattern))
    if not paths:
        print(f"No JSON files found for pattern: {exp_dir / pattern}")
        return 0

    rows = load_results(paths)
    print_table(rows)
    print_recall_matched(rows)

    plots_dir = exp_dir / "results" / "plots"
    make_plots(rows, plots_dir)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

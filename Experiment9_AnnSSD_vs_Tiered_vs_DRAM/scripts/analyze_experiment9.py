#!/usr/bin/env python3
"""Analysis/plot script for Experiment 9 (DRAM vs Tiered vs ANN-SSD).

Loads JSON logs from results/raw, prints a summary table, and generates
plots comparing recall/QPS/effective QPS across modes and levels.

Usage (from experiment dir, inside WSL):

  cd experiments/Experiment9_AnnSSD_vs_Tiered_vs_DRAM
  python scripts/analyze_experiment9.py
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
        mode = cfg.get("mode") or ("ann_ssd" if cfg.get("hardware_level") else "")

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
                "dataset": cfg.get("dataset_name", ""),
                "mode": mode,
                "level": cfg.get("hardware_level", ""),
                # For ann_ssd, record step-related knobs if present so we can
                # distinguish configurations that share the same level.
                "max_steps": cfg.get("max_steps"),
                "portal_degree": cfg.get("portal_degree"),
                "k": agg.get("k"),
                "num_queries": agg.get("num_queries"),
                "recall_at_k": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "p50": agg.get("latency_us_p50"),
                "p95": agg.get("latency_us_p95"),
                "p99": agg.get("latency_us_p99"),
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
        "dataset",
        "mode",
        "level",
        "recall",
        "qps_search",
        "qps_total",
        "eff_qps",
        "p50_us",
        "p95_us",
        "p99_us",
    ]

    print("\n=== Experiment 9 Summary ===")
    print("\t".join(headers))
    for r in sorted(rows, key=lambda x: (x["dataset"], x["mode"], x["level"])):
        print(
            "\t".join(
                [
                    str(r["file"]),
                    str(r["dataset"]),
                    str(r["mode"]),
                    str(r["level"]),
                    f"{r['recall_at_k']:.4f}" if r["recall_at_k"] is not None else "",
                    f"{r['qps_search']:.1f}" if r["qps_search"] is not None else "",
                    f"{r['qps_total']:.1f}" if r["qps_total"] is not None else "",
                    f"{r['effective_qps']:.1f}" if r["effective_qps"] is not None else "",
                    f"{r['p50']:.1f}" if r["p50"] is not None else "",
                    f"{r['p95']:.1f}" if r["p95"] is not None else "",
                    f"{r['p99']:.1f}" if r["p99"] is not None else "",
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


def _label_row(r: Dict[str, Any]) -> str:
    mode = r.get("mode")
    if mode == "ann_ssd":
        lvl = r.get("level") or ""
        steps = r.get("max_steps")
        # Make full-scan (max_steps == 0 or None) visually distinct.
        if steps in (None, 0):
            return f"annssd-{lvl}_full" if lvl else "annssd_full"
        return f"annssd-{lvl}_steps{steps}" if lvl else f"annssd_steps{steps}"
    return str(mode)


def _pretty_config_label(raw: str) -> str:
    """Convert internal config labels into human-readable x-axis labels.

    Examples:
      dram -> "DRAM"
      tiered -> "Tiered"
      annssd-L0_full -> "L0\n(full)"
      annssd-L3_steps78 -> "L3\n(78 Steps)".
    """

    label = str(raw)
    if label == "dram":
        return "DRAM"
    if label == "tiered":
        return "Tiered"

    if label.startswith("annssd-"):
        body = label[len("annssd-") :]
        level, _, rest = body.partition("_")
        level_disp = level.upper() if level else "ANN-SSD"

        if rest.startswith("full") or rest == "full":
            suffix = "(full)"
        elif rest.startswith("steps"):
            steps_str = rest[len("steps") :]
            steps_str = steps_str.lstrip("_")
            try:
                steps_val = int(steps_str) if steps_str else None
            except Exception:
                steps_val = None
            if steps_val is not None:
                suffix = f"({steps_val}\nSteps)"
            else:
                suffix = "(steps)"
        else:
            suffix = rest

        return f"{level_disp}\n{suffix}"

    if label == "annssd_full":
        return "ANN-SSD\n(full)"
    if label.startswith("annssd_steps"):
        steps_str = label[len("annssd_steps") :].lstrip("_")
        try:
            steps_val = int(steps_str) if steps_str else None
        except Exception:
            steps_val = None
        if steps_val is not None:
            return f"ANN-SSD\n({steps_val}\nSteps)"
        return "ANN-SSD\n(steps)"

    return label


def print_recall_matched(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    targets = [0.85, 0.95, 0.99]
    headers = ["dataset", "target_recall", "label", "recall", "eff_qps", "file"]
    print("\n=== Experiment 9 Recall-Matched Summary (max effective_qps) ===")
    print("\t".join(headers))

    datasets = sorted({str(r.get("dataset")) for r in rows if r.get("dataset")})
    for ds in datasets:
        sub = [r for r in rows if str(r.get("dataset")) == ds]
        labels = sorted({_label_row(r) for r in sub})
        for t in targets:
            for lbl in labels:
                best = None
                for r in sub:
                    if _label_row(r) != lbl:
                        continue
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
                    print("\t".join([ds, f"{t:.2f}", lbl, "", "", ""]))
                else:
                    print(
                        "\t".join(
                            [
                                ds,
                                f"{t:.2f}",
                                lbl,
                                f"{float(best['recall_at_k']):.4f}",
                                f"{float(best['effective_qps']):.1f}",
                                str(best.get("file") or ""),
                            ]
                        )
                    )


def make_plots(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping plots.")
        return
    if not rows:
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    # Focus on a single dataset at a time (usually synthetic).
    datasets = sorted({r["dataset"] for r in rows})
    for dataset in datasets:
        sub = [r for r in rows if r["dataset"] == dataset]
        if not sub:
            continue

        labels: List[str] = []
        recall_values: List[float] = []
        eff_qps_values: List[float] = []

        # Stable sort by mode/level/max_steps so x-axis ordering is readable.
        for r in sorted(
            sub,
            key=lambda rr: (
                str(rr.get("mode")),
                str(rr.get("level")),
                rr.get("max_steps") if rr.get("max_steps") is not None else -1,
            ),
        ):
            lbl = _label_row(r)
            labels.append(lbl)

            rec = r.get("recall_at_k")
            eff = r.get("effective_qps")
            try:
                recall_values.append(float(rec) if rec is not None else 0.0)
            except Exception:
                recall_values.append(0.0)
            try:
                eff_qps_values.append(float(eff) if eff is not None else 0.0)
            except Exception:
                eff_qps_values.append(0.0)

        if not labels:
            continue

        # Use a slightly stretched x-spacing so configurations are separated
        # horizontally, and offset the paired bars within each configuration to
        # leave a small gap between them.
        x = [i * 1.3 for i in range(len(labels))]
        width = 0.35
        left_centers = [xi - width * 0.75 for xi in x]
        right_centers = [xi + width * 0.75 for xi in x]

        fig, ax_recall = plt.subplots(figsize=(8, 4))
        ax_qps = ax_recall.twinx()

        # Recall bars (left y-axis)
        bar_recall = ax_recall.bar(
            left_centers,
            recall_values,
            width=width,
            color="C0",
            label="Recall @ k",
        )
        ax_recall.set_ylabel("Recall @ k")
        ax_recall.set_ylim(0.0, 1.05)

        # Effective QPS bars (right y-axis)
        bar_qps = ax_qps.bar(
            right_centers,
            eff_qps_values,
            width=width,
            color="C1",
            alpha=0.85,
            label="Effective QPS",
        )
        ax_qps.set_ylabel("Effective QPS")
        ax_qps.yaxis.set_major_formatter(FuncFormatter(_k_formatter))

        if eff_qps_values:
            try:
                ymax = max(float(v) for v in eff_qps_values)
                if ymax > 0.0:
                    ax_qps.set_ylim(0.0, ymax * 1.15)
            except Exception:
                pass

        # X-axis labels (human-readable, horizontal, with optional line breaks).
        display_labels = [_pretty_config_label(lbl) for lbl in labels]
        ax_recall.set_xticks(x)
        ax_recall.set_xticklabels(display_labels, rotation=0, ha="center")
        ax_recall.set_xlabel("Configuration")

        # Title with human-readable dataset name. Place any parenthetical
        # details on a second line for consistency across experiments.
        dataset_title = str(dataset).replace("_", " ").title() or "Synthetic Gaussian"
        ax_recall.set_title(
            f"Experiment 9: Recall and Effective QPS\n({dataset_title})"
        )

        # Annotate bars with numeric values.
        for bar, val in zip(bar_recall, recall_values):
            height = bar.get_height()
            ax_recall.annotate(
                f"{val:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2.0, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        for bar, val in zip(bar_qps, eff_qps_values):
            height = bar.get_height()
            label_str = _format_k(height)
            # If this is not a k-suffixed value, round to the nearest tenth.
            if "k" not in label_str:
                try:
                    v = float(height)
                    # Round to the nearest whole-number QPS when not using
                    # k-style formatting.
                    label_str = f"{int(round(v))}"
                except Exception:
                    pass
            ax_qps.annotate(
                label_str,
                xy=(bar.get_x() + bar.get_width() / 2.0, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        # Grid and legend placement
        ax_recall.grid(True, axis="y", alpha=0.3)
        handles = [bar_recall, bar_qps]
        legend_labels = [h.get_label() for h in handles]
        ax_recall.legend(
            handles,
            legend_labels,
            loc="upper left",
            bbox_to_anchor=(0.0, 0.9),
            fontsize=8,
        )

        # Add a bit more headroom so annotations do not touch plot borders.
        ax_recall.set_ylim(0.0, 1.1)
        if eff_qps_values:
            try:
                ymax = max(float(v) for v in eff_qps_values)
                if ymax > 0.0:
                    ax_qps.set_ylim(0.0, ymax * 1.25)
            except Exception:
                pass

        fig.tight_layout()
        fig.subplots_adjust(bottom=0.25)
        fig.savefig(out_dir / f"exp9_{dataset}_recall_qps.png", dpi=150)
        plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze Experiment 9 results.")
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

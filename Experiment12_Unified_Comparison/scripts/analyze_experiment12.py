#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore
    from matplotlib.ticker import FuncFormatter

    HAS_MPL = True
except Exception:
    HAS_MPL = False


def _load(paths: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
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

        mode = cfg.get("mode")
        if mode is None and cfg.get("hardware_level") is not None:
            mode = "ann_ssd"

        rows.append(
            {
                "file": p.name,
                "dataset": cfg.get("dataset_name"),
                "num_vectors": cfg.get("num_vectors"),
                "mode": mode,
                "hardware_level": cfg.get("hardware_level"),
                "simulation_mode": cfg.get("simulation_mode"),
                "cache_capacity": cfg.get("cache_capacity"),
                "recall_at_k": agg.get("recall_at_k"),
                "effective_qps": agg.get("effective_qps"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "p50": agg.get("latency_us_p50"),
                "p95": agg.get("latency_us_p95"),
                "p99": agg.get("latency_us_p99"),
            }
        )

    rows.sort(key=lambda r: (str(r.get("dataset")), int(r.get("num_vectors") or 0), str(r.get("mode")), str(r.get("hardware_level") or "")))
    return rows


def _label(r: Dict[str, Any]) -> str:
    mode = r.get("mode")
    if mode == "ann_ssd":
        lvl = r.get("hardware_level")
        sim = r.get("simulation_mode")
        s = f"annssd-{lvl}" if lvl else "annssd"
        if sim:
            s += f"-{sim}"
        return s
    if mode == "tiered":
        cap = r.get("cache_capacity")
        return f"tiered(cap={cap})" if cap is not None else "tiered"
    return str(mode)


def _print_table(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        print("No Experiment 12 results to show.")
        return

    headers = ["dataset", "num_vectors", "label", "recall", "qps_search", "eff_qps", "p50_us", "file"]
    print("\n=== Experiment 12 Summary ===")
    print("\t".join(headers))
    for r in rows:
        print(
            "\t".join(
                [
                    str(r.get("dataset")),
                    str(r.get("num_vectors")),
                    _label(r),
                    f"{r['recall_at_k']:.5f}" if r.get("recall_at_k") is not None else "",
                    f"{r['qps_search']:.3f}" if r.get("qps_search") is not None else "",
                    f"{r['effective_qps']:.3f}" if r.get("effective_qps") is not None else "",
                    f"{r['p50']:.1f}" if r.get("p50") is not None else "",
                    r.get("file") or "",
                ]
            )
        )


def _print_recall_matched(rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return

    targets = [0.85, 0.95, 0.99]

    grouped: Dict[Tuple[str, int], List[Dict[str, Any]]] = {}
    for r in rows:
        ds = r.get("dataset")
        nv = r.get("num_vectors")
        if ds is None or nv is None:
            continue
        try:
            key = (str(ds), int(nv))
        except Exception:
            continue
        grouped.setdefault(key, []).append(r)

    headers = ["dataset", "num_vectors", "target_recall", "label", "recall", "eff_qps", "file"]
    print("\n=== Experiment 12 Recall-Matched Summary (max effective_qps) ===")
    print("\t".join(headers))

    for (ds, nv), glist in sorted(grouped.items(), key=lambda x: (x[0][0], x[0][1])):
        labels = sorted({_label(r) for r in glist})
        for t in targets:
            for lbl in labels:
                best = None
                for r in glist:
                    if _label(r) != lbl:
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
                    print("\t".join([ds, str(nv), f"{t:.2f}", lbl, "", "", ""]))
                else:
                    print(
                        "\t".join(
                            [
                                ds,
                                str(nv),
                                f"{t:.2f}",
                                lbl,
                                f"{float(best['recall_at_k']):.5f}",
                                f"{float(best['effective_qps']):.3f}",
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


def _pretty_label(raw_label: str) -> str:
    """Map internal config labels to human-readable configuration names."""

    s = str(raw_label)
    if s == "dram":
        return "DRAM"
    if s == "hnswlib":
        return "HNSWlib"
    if s.startswith("tiered"):
        # Show a concise label for the tiered design.
        return "Tiered"

    if s.startswith("annssd-"):
        # Examples: "annssd-L2", "annssd-L2-cheated".
        body = s[len("annssd-") :]
        parts = body.split("-")
        level = parts[0].upper() if parts else "L?"
        # Present ANN-in-SSD levels as compact "L0"/"L1"/"L2"/"L3".
        return level

    return s


def _config_sort_key(raw_label: str) -> tuple:
    """Sort configurations in a sensible order for unified bar charts."""

    s = str(raw_label).lower()
    if s == "hnswlib":
        return (0, s)
    if s == "dram":
        return (1, s)
    if s.startswith("tiered"):
        return (2, s)
    if s.startswith("annssd-l0"):
        return (3, s)
    if s.startswith("annssd-l1"):
        return (4, s)
    if s.startswith("annssd-l2"):
        return (5, s)
    if s.startswith("annssd-l3"):
        return (6, s)
    return (99, s)


def _plot(rows: List[Dict[str, Any]], out_dir: Path) -> None:
    if not HAS_MPL:
        print("[INFO] matplotlib not available; skipping plots.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    datasets = sorted({r.get("dataset") for r in rows if r.get("dataset")})
    for ds in datasets:
        sub = [r for r in rows if r.get("dataset") == ds]
        pts = [
            r
            for r in sub
            if r.get("effective_qps") is not None and r.get("recall_at_k") is not None
        ]
        if not pts:
            continue

        # Focus the unified comparison on the largest num_vectors for this
        # dataset so each bar represents the most demanding scale.
        nv_values = [int(r.get("num_vectors") or 0) for r in pts if r.get("num_vectors")]
        max_nv = max(nv_values) if nv_values else None
        if max_nv is not None:
            pts = [r for r in pts if int(r.get("num_vectors") or 0) == max_nv]
        if not pts:
            continue

        # Group by configuration label (mode + hardware-level/cache params).
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for r in pts:
            groups.setdefault(_label(r), []).append(r)

        # For each configuration, choose a representative point: the run with
        # the highest recall, breaking ties by effective QPS.
        summaries: List[Tuple[str, Dict[str, Any]]] = []
        for raw_lbl, glist in groups.items():
            best = None
            for r in glist:
                rec = r.get("recall_at_k")
                qps = r.get("effective_qps")
                if rec is None or qps is None:
                    continue
                if best is None:
                    best = r
                    continue
                brec = float(best.get("recall_at_k") or 0.0)
                bqps = float(best.get("effective_qps") or 0.0)
                if float(rec) > brec or (
                    abs(float(rec) - brec) < 1e-6 and float(qps) > bqps
                ):
                    best = r
            if best is not None:
                summaries.append((raw_lbl, best))

        if not summaries:
            continue

        summaries.sort(key=lambda pair: _config_sort_key(pair[0]))

        raw_labels = [lbl for (lbl, _r) in summaries]
        display_labels = [_pretty_label(lbl) for lbl in raw_labels]
        recall_vals = [float(r["recall_at_k"]) for (_lbl, r) in summaries]
        eff_qps_vals = [float(r["effective_qps"]) for (_lbl, r) in summaries]

        x = list(range(len(display_labels)))
        width = 0.4

        fig, ax_recall = plt.subplots(figsize=(8, 4))
        ax_qps = ax_recall.twinx()

        # Recall bars (left y-axis)
        bar_recall = ax_recall.bar(
            [i - width / 2.0 for i in x],
            recall_vals,
            width=width,
            color="C0",
            label="Recall @ k",
        )
        ax_recall.set_ylabel("Recall @ k")
        # Add a bit of headroom so labels above the tallest bars do not clip.
        ax_recall.set_ylim(0.0, 1.10)

        # Effective QPS bars (right y-axis)
        bar_qps = ax_qps.bar(
            [i + width / 2.0 for i in x],
            eff_qps_vals,
            width=width,
            color="C1",
            alpha=0.85,
            label="Effective QPS",
        )
        ax_qps.set_ylabel("Effective QPS")
        ax_qps.yaxis.set_major_formatter(FuncFormatter(_k_formatter))

        if eff_qps_vals:
            try:
                ymax = max(float(v) for v in eff_qps_vals)
                if ymax > 0.0:
                    # Extra headroom so QPS value labels clear the top border.
                    ax_qps.set_ylim(0.0, ymax * 1.20)
            except Exception:
                pass

        # X-axis labels
        ax_recall.set_xticks(x)
        ax_recall.set_xticklabels(display_labels, rotation=0, ha="center")
        ax_recall.set_xlabel("Configuration")

        # Title and dataset name in human-readable form.
        ds_title = str(ds)
        if ds_title.lower() == "sift1m":
            pretty_ds = "SIFT1M"
        else:
            pretty_ds = ds_title.replace("_", " ").title()
        ax_recall.set_title(
            f"Experiment 12: Recall and Effective QPS\n({pretty_ds}, num_vectors={max_nv})"
        )

        # Annotate bars with numeric values.
        for bar, val in zip(bar_recall, recall_vals):
            height = bar.get_height()
            ax_recall.annotate(
                f"{val:.3f}",
                xy=(bar.get_x() + bar.get_width() / 2.0, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        for bar, val in zip(bar_qps, eff_qps_vals):
            height = bar.get_height()
            label_str = _format_k(height)
            # For non-k values, round to the nearest integer so we do not show
            # long decimal strings on the bar labels.
            if "k" not in label_str:
                try:
                    v = float(height)
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
            bbox_to_anchor=(0.0, 0.92),
            fontsize=8,
        )

        fig.tight_layout()
        fig.subplots_adjust(bottom=0.25)
        safe = str(ds).replace("/", "_")
        fig.savefig(out_dir / f"exp12_{safe}_recall_vs_effective_qps.png", dpi=150)
        plt.close(fig)


def main() -> int:
    p = argparse.ArgumentParser(description="Analyze Experiment 12 results")
    p.add_argument("--glob", type=str, default=None)
    args = p.parse_args()

    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent

    pattern = args.glob or "results/raw/exp12_*.json"
    paths = sorted(exp_dir.glob(pattern))
    if not paths:
        print(f"No JSON files found for pattern: {exp_dir / pattern}")
        return 0

    rows = _load(paths)
    _print_table(rows)
    _print_recall_matched(rows)
    _plot(rows, exp_dir / "results" / "plots")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

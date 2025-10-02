#!/usr/bin/env python3
"""
Plot GFLOP/s and (optional) speedup from P1 CSV results.

Usage:
  # Plot vs N (aligned-only by default)
  python3 scripts/p1/plot_p1.py --in data/raw/p1_saxpy.csv --out plots/p1/saxpy_vs_n.png --xaxis n

  # Plot vs stride at fixed N (aligned-only by default)
  python3 scripts/p1/plot_p1.py --in data/raw/p1_saxpy_stride.csv --out plots/p1/saxpy_vs_stride.png --xaxis stride --fixed_n 1048576

Notes:
- CSV columns: variant,n,reps,misaligned,median_ms,best_ms,gflops,max_abs_err
- Optional columns: stride, dtype
- Aligned-only by default (misaligned==0). Use --include_misaligned to overlay misaligned throughput.
- Speedup is computed vs the aligned scalar baseline at matching dtype (and matching stride if present).
"""

import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input CSV file")
    ap.add_argument("--out", dest="outp", required=True, help="Output PNG path")
    ap.add_argument("--xaxis", choices=["n", "stride"], default="n", help="X-axis: n (size) or stride")
    ap.add_argument("--fixed_n", type=int, default=None, help="When plotting vs stride, filter to this N")
    ap.add_argument("--include_misaligned", action="store_true", help="Overlay misaligned series in throughput plot")

    args = ap.parse_args()

    df = pd.read_csv(args.inp)
    # Strip BOM and whitespace from column names
    df.columns = df.columns.str.replace('\ufeff', '', regex=False).str.strip()

    # Normalize optional columns
    if "misaligned" not in df.columns:
        df["misaligned"] = 0
    if "stride" not in df.columns:
        df["stride"] = 1
    if "dtype" not in df.columns:
        df["dtype"] = "f32"

    # Required column check
    if "variant" not in df.columns:
        raise SystemExit("Missing required column: variant")

    # Derive variant labels
    df["variant_name"] = df["variant"].apply(lambda v: os.path.basename(str(v)))
    df["variant_kind"] = df["variant_name"].str.replace(r".*/", "", regex=True)

    # Select x-axis and filter
    if args.xaxis == "n":
        xcol = "n"
    else:
        xcol = "stride"
        if args.fixed_n is None:
            args.fixed_n = int(df["n"].max())
        df = df[df["n"] == args.fixed_n]

    # Throughput view: include misaligned if requested
    if args.include_misaligned:
        view_df = df.copy()
    else:
        view_df = df[df["misaligned"] == 0].copy()

    # For vs-N plots, prefer unit stride if present
    if xcol == "n" and "stride" in view_df.columns:
        view_df = view_df[view_df["stride"] == 1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    # Throughput plot (GFLOP/s)
    has_dtype = "dtype" in view_df.columns
    has_misaligned = "misaligned" in view_df.columns
    group_keys = ["variant_kind"] + (["dtype"] if has_dtype else [])
    if args.include_misaligned and has_misaligned:
        group_keys += ["misaligned"]
    for keys, grp in view_df.groupby(group_keys):
        grp_sorted = grp.sort_values(xcol)
        vk = keys[0]
        label_parts = []
        if has_dtype:
            dtype_val = keys[1] if len(keys) >= 2 else None
            if dtype_val is not None:
                label_parts.append(f"dtype={dtype_val}")
        if args.include_misaligned and has_misaligned:
            mis_val = keys[-1]
            label_parts.append(f"misaligned={int(mis_val)}")
        series_label = vk + (" (" + ", ".join(label_parts) + ")" if label_parts else "")
        ax1.plot(grp_sorted[xcol], grp_sorted["gflops"], marker="o", label=series_label)

    ax1.set_xscale("log", base=2)
    ax1.set_xlabel("N (elements)" if xcol == "n" else "Stride (elements)")
    ax1.set_ylabel("GFLOP/s")
    ax1.set_title("Throughput")
    ax1.grid(True, which="both", linestyle="--", alpha=0.4)
    ax1.legend(fontsize=8)

    # Speedup vs scalar (aligned-only baseline)
    aligned = df[df["misaligned"] == 0].copy()
    if xcol == "n" and "stride" in aligned.columns:
        aligned = aligned[aligned["stride"] == 1]

    if not aligned.empty and aligned["variant_kind"].str.contains("scalar").any():
        scal = aligned[aligned["variant_kind"].str.contains("scalar")]
        has_dtype_al = "dtype" in aligned.columns

        if xcol == "n":
            # Baseline maps per dtype: n -> median_ms
            base_maps = {}
            for dtype_val, grp_d in (scal.groupby("dtype") if has_dtype_al else [(None, scal)]):
                base_maps[dtype_val] = (
                    grp_d[["n", "median_ms"]].drop_duplicates().set_index("n")["median_ms"].to_dict()
                )
            for keys, grp in aligned.groupby(["variant_kind"] + (["dtype"] if has_dtype_al else [])):
                dtype_val = keys[1] if has_dtype_al else None
                base = base_maps[dtype_val]
                grp_sorted = grp.sort_values("n")
                xs, ys = [], []
                for _, row in grp_sorted.iterrows():
                    n = row["n"]
                    if n in base and row["median_ms"] > 0:
                        xs.append(n)
                        ys.append(base[n] / row["median_ms"])
                if xs:
                    lbl = f"{keys[0]}" + ((f" (dtype={dtype_val})") if has_dtype_al else "")
                    ax2.plot(xs, ys, marker="o", label=lbl)
        else:
            # xaxis=stride at fixed N: baseline per dtype: stride -> median_ms
            base_maps = {}
            for dtype_val, grp_d in (scal.groupby("dtype") if has_dtype_al else [(None, scal)]):
                base_maps[dtype_val] = (
                    grp_d[["stride", "median_ms"]].drop_duplicates().set_index("stride")["median_ms"].to_dict()
                )
            for keys, grp in aligned.groupby(["variant_kind"] + (["dtype"] if has_dtype_al else [])):
                dtype_val = keys[1] if has_dtype_al else None
                base = base_maps[dtype_val]
                grp_sorted = grp.sort_values("stride")
                xs, ys = [], []
                for _, row in grp_sorted.iterrows():
                    s = row["stride"]
                    if s in base and row["median_ms"] > 0:
                        xs.append(s)
                        ys.append(base[s] / row["median_ms"])
                if xs:
                    lbl = (
                        f"{keys[0]} (dtype={dtype_val}, N={int(args.fixed_n)})"
                        if has_dtype_al
                        else f"{keys[0]} (N={int(args.fixed_n)})"
                    )
                    ax2.plot(xs, ys, marker="o", label=lbl)
        ax2.set_xscale("log", base=2)
        ax2.set_xlabel("N (elements)" if xcol == "n" else "Stride (elements)")
        ax2.set_ylabel("Speedup vs scalar (aligned)")
        ax2.set_title(
            "Speedup vs Scalar (aligned)"
            if xcol == "n"
            else f"Speedup vs Scalar (aligned, N={int(args.fixed_n)})"
        )
        ax2.grid(True, which="both", linestyle="--", alpha=0.4)
        ax2.legend(fontsize=8)
    else:
        ax2.text(0.5, 0.5, "No scalar baseline found", ha="center", va="center")
        ax2.axis("off")

    out_dir = os.path.dirname(args.outp)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.tight_layout()
    plt.savefig(args.outp, dpi=150)
    print(f"Wrote: {args.outp}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd, cwd: Path) -> None:
    print("\n[run_experiment6] exec:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            sys.stderr.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    if proc.stdout:
        sys.stdout.write(proc.stdout)


def main() -> int:
    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent
    project_dir = exp_dir.parent.parent

    bin_path = project_dir / "bin" / "benchmark_recall"
    if not bin_path.exists():
        raise SystemExit(f"benchmark_recall not found at {bin_path}; build benchmarks first.")

    results_raw = exp_dir / "results" / "raw"
    results_raw.mkdir(parents=True, exist_ok=True)

    # Common configuration: synthetic Gaussian, 20k base, 2k queries.
    num_base = 20000
    num_queries = 2000
    dim = 128
    k = 10
    ef_search = 256
    M = 24
    ef_construction = 300
    seed = 42

    # SSD profile: reuse the NVMe Gen3-like config from Experiment 5.
    ssd_base_latency_us = 80.0
    ssd_bw_GBps = 3.0
    ssd_num_channels = 4
    ssd_queue_depth = 64

    runs = []

    # DRAM baseline (no SSD cost, full DRAM budget).
    runs.append(
        {
            "name": "exp6_dram_nb20k_q2k_efs256",
            "mode": "dram",
            "cache_capacity": None,
        }
    )

    # Tiered runs with different cache capacities (DRAM budgets).
    cache_fracs = [0.1, 0.25, 0.5, 0.75, 1.0]
    for frac in cache_fracs:
        cap = max(1, int(num_base * frac))
        label = int(frac * 100)
        runs.append(
            {
                "name": f"exp6_tiered_cache{label}_nb20k_q2k_efs256",
                "mode": "tiered",
                "cache_capacity": cap,
            }
        )

    # ANN-in-SSD runs at each hardware level (Solution 3).
    ann_levels = ["L0", "L1", "L2", "L3"]
    for level in ann_levels:
        runs.append(
            {
                "name": f"exp6_annssd_level-{level}_nb20k_q2k_efs256",
                "mode": "ann_ssd",
                "hardware_level": level,
            }
        )

    for cfg in runs:
        json_out = results_raw / f"{cfg['name']}.json"
        cmd = [
            str(bin_path),
            "--mode",
            cfg["mode"],
            "--num-base",
            str(num_base),
            "--num-queries",
            str(num_queries),
            "--dim",
            str(dim),
            "--k",
            str(k),
            "--ef-search",
            str(ef_search),
            "--M",
            str(M),
            "--ef-construction",
            str(ef_construction),
            "--seed",
            str(seed),
            "--json-out",
            str(json_out),
        ]

        if cfg["mode"] == "tiered" and cfg["cache_capacity"] is not None:
            cmd.extend(
                [
                    "--cache-capacity",
                    str(cfg["cache_capacity"]),
                    "--ssd-base-latency-us",
                    str(ssd_base_latency_us),
                    "--ssd-internal-bw-GBps",
                    str(ssd_bw_GBps),
                    "--ssd-num-channels",
                    str(ssd_num_channels),
                    "--ssd-queue-depth",
                    str(ssd_queue_depth),
                ]
            )
        elif cfg["mode"] == "ann_ssd":
            level = cfg.get("hardware_level", "L0")
            cmd.extend(
                [
                    "--dataset-name",
                    "synthetic_gaussian",
                    "--ann-ssd-mode",
                    "cheated",
                    "--ann-hw-level",
                    level,
                    "--ann-vectors-per-block",
                    "128",
                    "--ann-max-steps",
                    "20",
                    "--ann-portal-degree",
                    "2",
                ]
            )

        _run(cmd, project_dir)

    # Quick sanity summary: print recall/QPS for the new JSONs.
    print("\n[run_experiment6] Summary of new JSON results:")
    for p in sorted(results_raw.glob("exp6_*.json")):
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        cfg = data.get("config", {})
        agg = data.get("aggregate", {})

        num_q = agg.get("num_queries") or cfg.get("num_queries") or 0
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

        print(
            f"  {p.name}: mode={cfg.get('mode')}, cache_capacity={cfg.get('cache_capacity')}, "
            f"recall@k={agg.get('recall_at_k')}, qps_search={qps_search}, qps_total={qps_total}, effective_qps={agg.get('effective_qps')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

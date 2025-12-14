#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd, cwd: Path) -> None:
    print("\n[run_experiment5] exec:", " ".join(cmd))
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

    # Fix cache capacity at 50% of base to keep meaningful SSD I/O.
    cache_capacity = num_base // 2  # 10000 for 20k base

    # SSD profiles: rough "slow SATA" to "future NVMe" spectrum.
    profiles = [
        {
            "name": "sata_like",
            "ssd_base_read_latency_us": 100.0,
            "ssd_internal_read_bandwidth_GBps": 0.5,
            "ssd_num_channels": 2,
            "ssd_queue_depth_per_channel": 32,
        },
        {
            "name": "nvme_gen3",
            "ssd_base_read_latency_us": 80.0,
            "ssd_internal_read_bandwidth_GBps": 3.0,
            "ssd_num_channels": 4,
            "ssd_queue_depth_per_channel": 64,
        },
        {
            "name": "nvme_fast",
            "ssd_base_read_latency_us": 40.0,
            "ssd_internal_read_bandwidth_GBps": 6.0,
            "ssd_num_channels": 8,
            "ssd_queue_depth_per_channel": 64,
        },
        {
            "name": "nvme_ultra",
            "ssd_base_read_latency_us": 20.0,
            "ssd_internal_read_bandwidth_GBps": 8.0,
            "ssd_num_channels": 16,
            "ssd_queue_depth_per_channel": 128,
        },
    ]

    # Optional DRAM reference.
    runs = [
        {
            "name": "exp5_dram_nb20k_q2k_efs256",
            "mode": "dram",
            "profile": None,
        }
    ]

    for prof in profiles:
        runs.append(
            {
                "name": f"exp5_tiered_{prof['name']}_nb20k_q2k_efs256",
                "mode": "tiered",
                "profile": prof,
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

        prof = cfg["profile"]
        if cfg["mode"] == "tiered" and prof is not None:
            cmd.extend(
                [
                    "--cache-capacity",
                    str(cache_capacity),
                    "--ssd-base-latency-us",
                    str(prof["ssd_base_read_latency_us"]),
                    "--ssd-internal-bw-GBps",
                    str(prof["ssd_internal_read_bandwidth_GBps"]),
                    "--ssd-num-channels",
                    str(prof["ssd_num_channels"]),
                    "--ssd-queue-depth",
                    str(prof["ssd_queue_depth_per_channel"]),
                ]
            )

        _run(cmd, project_dir)

    # Quick sanity summary: print recall/QPS and modeled device time per query.
    print("\n[run_experiment5] Summary of new JSON results:")
    for p in sorted(results_raw.glob("exp5_*.json")):
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
        dev_us = agg.get("device_time_us")
        dev_us_per_q = (dev_us / num_q) if dev_us is not None and num_q else None
        print(
            f"  {p.name}: mode={cfg.get('mode')}, "
            f"ssd_base_latency_us={cfg.get('ssd_base_read_latency_us')}, "
            f"ssd_bw_GBps={cfg.get('ssd_internal_read_bandwidth_GBps')}, "
            f"recall@k={agg.get('recall_at_k')}, qps_search={qps_search}, qps_total={qps_total}, "
            f"effective_qps={agg.get('effective_qps')}, dev_us/q={dev_us_per_q}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

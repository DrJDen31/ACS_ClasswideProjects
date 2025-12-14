#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd, cwd: Path) -> None:
    print("\n[run_experiment2] exec:", " ".join(cmd))
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

    runs = []

    # DRAM baseline.
    runs.append(
        {
            "name": "exp2_dram_nb20k_q2k_efs256",
            "mode": "dram",
            "cache_capacity": None,
        }
    )

    # Tiered runs with different cache capacities (approximate fractions of num_base).
    cache_fracs = [0.1, 0.25, 0.5, 1.0]
    for frac in cache_fracs:
        cap = max(1, int(num_base * frac))
        label = int(frac * 100)
        runs.append(
            {
                "name": f"exp2_tiered_cache{label}_nb20k_q2k_efs256",
                "mode": "tiered",
                "cache_capacity": cap,
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
            cmd.extend(["--cache-capacity", str(cfg["cache_capacity"])])

        _run(cmd, project_dir)

    # Quick sanity summary: print recall/QPS from the new JSONs.
    print("\n[run_experiment2] Summary of new JSON results:")
    for p in sorted(results_raw.glob("*.json")):
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        agg = data.get("aggregate", {})
        cfg = data.get("config", {})

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
            f"  {p.name}: mode={cfg.get('mode')}, recall@k={agg.get('recall_at_k')}, "
            f"qps_search={qps_search}, qps_total={qps_total}, effective_qps={agg.get('effective_qps')}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

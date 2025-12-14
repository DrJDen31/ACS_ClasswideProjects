#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path


def _run(cmd, cwd: Path) -> str:
    print("\n[run_experiment3] exec:", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)
    if proc.returncode != 0:
        if proc.stdout:
            sys.stderr.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    return proc.stdout or ""


def _inject_cache_stats(json_path: Path, stdout: str) -> None:
    """Parse Tiered cache stats from stdout and inject into JSON aggregate."""
    m = re.search(r"Tiered cache: hits=(\d+), misses=(\d+)", stdout)
    if not m:
        return
    hits = int(m.group(1))
    misses = int(m.group(2))

    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return

    agg = data.setdefault("aggregate", {})
    agg["cache_hits"] = hits
    agg["cache_misses"] = misses

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main() -> int:
    script_path = Path(__file__).resolve()
    exp_dir = script_path.parent.parent
    project_dir = exp_dir.parent.parent

    bin_path = project_dir / "bin" / "benchmark_recall"
    if not bin_path.exists():
        raise SystemExit(f"benchmark_recall not found at {bin_path}; build benchmarks first.")

    results_raw = exp_dir / "results" / "raw"
    results_raw.mkdir(parents=True, exist_ok=True)

    # Match Experiment 2 synthetic workload for comparability.
    num_base = 20000
    num_queries = 2000
    dim = 128
    k = 10
    ef_search = 256
    M = 24
    ef_construction = 300
    seed = 42
    cache_capacity = 5000  # 25% of 20k base vectors

    policies = [
        {"name": "lru", "cache_policy": "lru"},
        {"name": "lfu", "cache_policy": "lfu"},
    ]

    summaries = []

    for cfg in policies:
        run_name = f"exp3_tiered_{cfg['name']}_nb20k_q2k_efs256"
        json_out = results_raw / f"{run_name}.json"

        cmd = [
            str(bin_path),
            "--mode",
            "tiered",
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
            "--cache-capacity",
            str(cache_capacity),
            "--cache-policy",
            cfg["cache_policy"],
            "--json-out",
            str(json_out),
        ]

        stdout = _run(cmd, project_dir)
        _inject_cache_stats(json_out, stdout)

        # Quick one-line summary from JSON
        try:
            with json_out.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
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

        summaries.append(
            {
                "name": run_name,
                "policy": cfg["cache_policy"],
                "recall": agg.get("recall_at_k"),
                "qps_search": qps_search,
                "qps_total": qps_total,
                "effective_qps": agg.get("effective_qps"),
                "cache_hits": agg.get("cache_hits"),
                "cache_misses": agg.get("cache_misses"),
            }
        )

    print("\n[run_experiment3] Summary of new JSON results:")
    for s in summaries:
        print(
            f"  {s['name']}: policy={s['policy']}, "
            f"recall@k={s['recall']}, qps_search={s['qps_search']}, qps_total={s['qps_total']}, "
            f"effective_qps={s['effective_qps']}, "
            f"hits={s['cache_hits']}, misses={s['cache_misses']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

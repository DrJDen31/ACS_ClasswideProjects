#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path


def _parse(label: str, text: str, pattern: str) -> float:
    m = re.search(pattern, text)
    if not m:
        raise RuntimeError(f"Failed to parse {label} from output")
    return float(m.group(1))


def _run_one(cfg, project_dir: Path, experiment_dir: Path):
    script = project_dir / "scripts" / "compare_hnswlib_sift.py"
    data_dir = project_dir / "data" / "SIFT1M" / "sift"
    base = data_dir / "sift_base.fvecs"
    query = data_dir / "sift_query.fvecs"
    groundtruth = data_dir / "sift_groundtruth.ivecs"

    out_dir = experiment_dir / "results" / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"hnswlib_{cfg['name']}.json"

    cmd = [
        "python3",
        str(script),
        "--base",
        str(base),
        "--query",
        str(query),
        "--num-base",
        str(cfg["num_base"]),
        "--num-queries",
        str(cfg["num_queries"]),
        "--dim",
        "128",
        "--k",
        "10",
        "--M",
        "24",
        "--ef-construction",
        "300",
        "--ef-search",
        str(cfg["ef_search"]),
    ]

    # For SIFT20k subset runs, let compare_hnswlib_sift.py compute
    # brute-force ground truth on the 20k subset by *omitting*
    # --groundtruth. For full SIFT1M, use the provided 1M groundtruth
    # file to avoid an expensive brute-force pass.
    if cfg.get("use_groundtruth", True):
        cmd.extend([
            "--groundtruth",
            str(groundtruth),
        ])

    print("\n=== Running", cfg["name"], "===")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise SystemExit(proc.returncode)

    stdout = proc.stdout
    recall = _parse("recall", stdout, r"recall@\d+ = ([0-9.]+)")
    build_time = _parse("build_time_s", stdout, r"build_time_s = ([0-9.]+)")
    search_time = _parse("search_time_s", stdout, r"search_time_s = ([0-9.]+)")
    total_qps = _parse("total_QPS", stdout, r"total_QPS = ([0-9.]+)")
    search_qps = _parse("search_QPS", stdout, r"search_QPS = ([0-9.]+)")

    result = {
        "name": cfg["name"],
        "config": {
            "dataset_name": cfg["dataset"],
            "base_path": str(base),
            "query_path": str(query),
            "groundtruth_path": str(groundtruth),
            "num_base": cfg["num_base"],
            "num_queries": cfg["num_queries"],
            "dim": 128,
            "k": 10,
            "M": 24,
            "ef_construction": 300,
            "ef_search": cfg["ef_search"],
        },
        "aggregate": {
            "recall_at_k": recall,
            "build_time_s": build_time,
            "search_time_s": search_time,
            "qps": search_qps,
            "qps_search": search_qps,
            "qps_total": total_qps,
        },
    }

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result


def main() -> int:
    script_path = Path(__file__).resolve()
    experiment_dir = script_path.parent.parent
    project_dir = experiment_dir.parent.parent

    runs = [
        {
            "name": "sift20k_M24_efc300_efs256",
            "dataset": "SIFT20k",
            "num_base": 20000,
            "num_queries": 2000,
            "ef_search": 256,
            "use_groundtruth": False,
        },
        {
            "name": "sift20k_M24_efc300_efs512",
            "dataset": "SIFT20k",
            "num_base": 20000,
            "num_queries": 2000,
            "ef_search": 512,
            "use_groundtruth": False,
        },
        {
            "name": "sift1m_M24_efc300_efs512",
            "dataset": "SIFT1M",
            "num_base": 1000000,
            "num_queries": 10000,
            "ef_search": 512,
            "use_groundtruth": True,
        },
    ]

    results = []
    for cfg in runs:
        res = _run_one(cfg, project_dir, experiment_dir)
        results.append(res)

    print("\n=== Experiment 0: hnswlib summary ===")
    header = [
        "name",
        "dataset",
        "num_base",
        "num_queries",
        "recall",
        "qps_total",
        "qps_search",
        "build_s",
        "search_s",
    ]
    print("\t".join(header))
    for r, cfg in zip(results, runs):
        agg = r["aggregate"]
        row = [
            cfg["name"],
            cfg["dataset"],
            str(cfg["num_base"]),
            str(cfg["num_queries"]),
            f"{agg['recall_at_k']:.6f}",
            f"{agg['qps_total']:.3f}",
            f"{agg['qps_search']:.3f}",
            f"{agg['build_time_s']:.4f}",
            f"{agg['search_time_s']:.4f}",
        ]
        print("\t".join(row))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

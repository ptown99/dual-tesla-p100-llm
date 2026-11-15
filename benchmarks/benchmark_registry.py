#!/usr/bin/env python3
"""
Master Benchmark Registry Manager for Dual Tesla P100 Cluster.
Maintains BENCHMARK_REGISTRY.json and BENCHMARK_REGISTRY.md.
Consults cached results before executing benchmarks to avoid redundant re-runs.
"""

import json
import os
import sys
from datetime import datetime

DEFAULT_REGISTRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BENCHMARK_REGISTRY.json")
DEFAULT_MD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "BENCHMARK_REGISTRY.md")

def load_registry(path=None):
    if path is None:
        path = DEFAULT_REGISTRY_PATH
    if not os.path.exists(path):
        raise FileNotFoundError(f"Registry not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_registry(data, json_path=None, md_path=None):
    if json_path is None:
        json_path = DEFAULT_REGISTRY_PATH
    if md_path is None:
        md_path = DEFAULT_MD_PATH

    data["metadata"]["last_updated"] = datetime.utcnow().isoformat() + "Z"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Regenerate markdown
    from build_benchmark_registry import generate_markdown
    md_content = generate_markdown(data)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

def lookup_benchmark(category, criteria_func=None, registry_path=None):
    """
    Look up if a benchmark matching category and criteria already exists.
    Returns matching result or None.
    """
    data = load_registry(registry_path)
    benches = data.get("benchmarks", {})
    if category not in benches:
        return None
    cat_data = benches[category]
    if criteria_func is None:
        return cat_data
    if isinstance(cat_data, list):
        matches = [item for item in cat_data if criteria_func(item)]
        return matches if matches else None
    elif isinstance(cat_data, dict):
        return cat_data if criteria_func(cat_data) else None
    return None

def append_benchmark(category, entry, registry_path=None, md_path=None):
    """
    Appends a new benchmark entry to a category (or replaces dict) and saves both JSON & MD.
    """
    data = load_registry(registry_path)
    benches = data.setdefault("benchmarks", {})
    if category in benches and isinstance(benches[category], list):
        benches[category].append(entry)
    else:
        benches[category] = entry
    save_registry(data, registry_path, md_path)
    print(f"Benchmark registered under category '{category}'.")

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help"]:
        print("Usage:")
        print("  python benchmark_registry.py summary")
        print("  python benchmark_registry.py list-categories")
        print("  python benchmark_registry.py get <category>")
        sys.exit(0)

    cmd = sys.argv[1]
    data = load_registry()

    if cmd == "summary":
        champ = data["benchmarks"].get("p5_megakernel_champion_deployed", {})
        s = champ.get("summary", {})
        print("=== Champion Benchmark Configuration ===")
        print(f"Model: {champ.get('model')} | Commit: {champ.get('commit')}")
        print(f"Engine Eval: {s.get('avg_engine_eval_tps')} tok/s (Peak: {s.get('peak_engine_eval_tps')} tok/s)")
        print(f"Sustained STEM E2E: {s.get('avg_e2e_tps')} tok/s | Draft Acceptance: {s.get('draft_acceptance_pct')}%")
        print(f"Active Memory Bus Throughput: {s.get('physical_bus_throughput_gb_s')} GB/s")
        print(f"Free VRAM Cushion: GPU1={s.get('gpu1_free_vram_mb')}MB, GPU2={s.get('gpu2_free_vram_mb')}MB")
    elif cmd == "list-categories":
        print("Available Benchmark Categories:")
        for cat in data.get("benchmarks", {}):
            print(f" - {cat}")
    elif cmd == "get" and len(sys.argv) > 2:
        cat = sys.argv[2]
        res = data.get("benchmarks", {}).get(cat)
        print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()

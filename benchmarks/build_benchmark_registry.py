#!/usr/bin/env python3
import json
import os
from datetime import datetime

registry = {
    "metadata": {
        "title": "Dual Tesla P100 LLM Master Benchmark Registry",
        "description": "Historical, cached, and validated benchmark results across all optimization milestones, kernels, models, and parameter sweeps on Dual Tesla P100 sm_60.",
        "created_at": "2026-11-14T20:10:00Z",
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "node": "mimi@192.168.1.67",
        "hardware": {
            "gpus": [
                {"id": 0, "model": "NVIDIA Quadro M2000 4GB", "role": "Host display only", "limit_w": 25, "active_pwr_w": 11, "compute_allocated": False},
                {"id": 1, "model": "NVIDIA Tesla P100-PCIE-16GB", "arch": "Pascal sm_60", "vram_mb": 16384, "bus_bw_gb_s": 732, "power_limit_w": 210},
                {"id": 2, "model": "NVIDIA Tesla P100-PCIE-16GB", "arch": "Pascal sm_60", "vram_mb": 16384, "bus_bw_gb_s": 732, "power_limit_w": 210}
            ],
            "aggregate_hbm2_bw_gb_s": 1464,
            "host_cpu": "Intel Xeon E5-2623 v3 (4 Cores, 8 Threads @ 3.00 GHz)",
            "host_ram_gb": 64,
            "os": "Debian 12 / Ubuntu Linux",
            "cuda_version": "12.4",
            "driver_version": "550.163.01"
        }
    },
    "benchmarks": {
        "p5_megakernel_champion_deployed": {
            "timestamp": "2026-11-14T23:16:32Z",
            "model": "Qwen3.8-27B-UD-IQ4_XS.gguf",
            "service": "llama-qwen38-27b-fast.service",
            "commit": "bfe6bc1",
            "optimizations": [
                "P5 Option A Persistent Cooperative Megakernel (nodes 60..66 fused)",
                "MTP 3-Draft Speculation (re-tuned from 4)",
                "Physical CPU affinity (threads-batch 4)",
                "PCIe P2P ACS bypass"
            ],
            "parameters": {
                "split_mode": "tensor",
                "ngl": 999,
                "context_window": 215040,
                "ctk": "q8_0",
                "ctv": "q8_0",
                "b": 32768,
                "ub": 1024,
                "spec_type": "draft-mtp",
                "spec_draft_n_max": 3,
                "spec_draft_p_min": 0.12,
                "threads": 4,
                "threads_batch": 4
            },
            "summary": {
                "avg_e2e_tps": 31.81,
                "avg_engine_eval_tps": 44.41,
                "peak_engine_eval_tps": 50.26,
                "draft_acceptance_pct": 58.2,
                "physical_bus_throughput_gb_s": 368.64,
                "bus_saturation_pct": 25.2,
                "gpu_core_util_avg_pct": 79.8,
                "gpu_core_util_peak_pct": 99.0,
                "gpu1_free_vram_mb": 3469,
                "gpu2_free_vram_mb": 3467,
                "gpu1_avg_power_w": 135.5,
                "gpu2_avg_power_w": 128.3
            },
            "prompts": [
                {"name": "Navier-Stokes momentum equation derivation", "tokens": 128, "elapsed_s": 3.73, "e2e_tps": 34.28, "engine_tps": 45.50, "draft_acc_pct": 60.0},
                {"name": "FEM Galerkin vs Petrov-Galerkin", "tokens": 128, "elapsed_s": 4.22, "e2e_tps": 30.36, "engine_tps": 42.48, "draft_acc_pct": 52.0},
                {"name": "Eigenvalues 3x3 symmetric stress tensor", "tokens": 128, "elapsed_s": 3.78, "e2e_tps": 33.89, "engine_tps": 50.26, "draft_acc_pct": 68.0},
                {"name": "Python SymPy 4th-order Runge-Kutta stiff ODE", "tokens": 128, "elapsed_s": 4.46, "e2e_tps": 28.71, "engine_tps": 39.39, "draft_acc_pct": 45.6}
            ]
        },
        "megakernel_parameter_tuning_sweep_refined": [
            {"id": "MTP3_p0.12_ub1024_tb4", "n_max": 3, "p_min": 0.12, "ub": 1024, "tb": 4, "avg_engine_tps": 46.13, "avg_e2e_tps": 32.41, "draft_acc_pct": 58.2, "eigenvalues_engine_tps": 55.48, "vram_free_mb": 3354},
            {"id": "MTP3_p0.15_ub1024_tb4", "n_max": 3, "p_min": 0.15, "ub": 1024, "tb": 4, "avg_engine_tps": 46.33, "avg_e2e_tps": 32.37, "draft_acc_pct": 58.0, "eigenvalues_engine_tps": 57.64, "vram_free_mb": 3354},
            {"id": "MTP2_p0.10_ub1024_tb4", "n_max": 2, "p_min": 0.10, "ub": 1024, "tb": 4, "avg_engine_tps": 45.09, "avg_e2e_tps": 32.68, "draft_acc_pct": 67.8, "eigenvalues_engine_tps": 51.22, "vram_free_mb": 3428},
            {"id": "MTP3_p0.10_ub1024_tb4", "n_max": 3, "p_min": 0.10, "ub": 1024, "tb": 4, "avg_engine_tps": 43.50, "avg_e2e_tps": 31.39, "draft_acc_pct": 54.2, "eigenvalues_engine_tps": 49.14, "vram_free_mb": 3354}
        ],
        "megakernel_parameter_tuning_sweep_broad": [
            {"id": "MTP3_p0.10_ub1024_tb6", "n_max": 3, "p_min": 0.10, "ub": 1024, "tb": 6, "avg_engine_tps": 43.17, "avg_e2e_tps": 31.15, "draft_acc_pct": 51.4, "vram_free_mb": 3354},
            {"id": "BestDraft_ub1024_tb4",  "n_max": 4, "p_min": 0.10, "ub": 1024, "tb": 4, "avg_engine_tps": 40.35, "avg_e2e_tps": 29.74, "draft_acc_pct": 49.4, "vram_free_mb": 3278},
            {"id": "Base_MTP4_p0.10_ub1024_tb6", "n_max": 4, "p_min": 0.10, "ub": 1024, "tb": 6, "avg_engine_tps": 39.65, "avg_e2e_tps": 29.36, "draft_acc_pct": 45.3, "vram_free_mb": 3278},
            {"id": "MTP4_p0.05_ub1024_tb6", "n_max": 4, "p_min": 0.05, "ub": 1024, "tb": 6, "avg_engine_tps": 39.41, "avg_e2e_tps": 29.21, "draft_acc_pct": 44.6, "vram_free_mb": 3278},
            {"id": "MTP4_p0.15_ub1024_tb6", "n_max": 4, "p_min": 0.15, "ub": 1024, "tb": 6, "avg_engine_tps": 39.09, "avg_e2e_tps": 29.03, "draft_acc_pct": 46.1, "vram_free_mb": 3278},
            {"id": "BestDraft_ub2048_tb6",  "n_max": 4, "p_min": 0.10, "ub": 2048, "tb": 6, "avg_engine_tps": 38.73, "avg_e2e_tps": 28.28, "draft_acc_pct": 43.2, "vram_free_mb": 2056},
            {"id": "MTP5_p0.10_ub1024_tb6", "n_max": 5, "p_min": 0.10, "ub": 1024, "tb": 6, "avg_engine_tps": 36.75, "avg_e2e_tps": 28.00, "draft_acc_pct": 40.6, "vram_free_mb": 3204},
            {"id": "MTP5_p0.15_ub1024_tb6", "n_max": 5, "p_min": 0.15, "ub": 1024, "tb": 6, "avg_engine_tps": 36.69, "avg_e2e_tps": 27.04, "draft_acc_pct": 39.9, "vram_free_mb": 3204},
            {"id": "MTP5_p0.05_ub1024_tb6", "n_max": 5, "p_min": 0.05, "ub": 1024, "tb": 6, "avg_engine_tps": 34.49, "avg_e2e_tps": 26.06, "draft_acc_pct": 37.4, "vram_free_mb": 3204}
        ],
        "p5_option_a_megakernel_raw_dense_decode": {
            "timestamp": "2026-11-14T21:45:00Z",
            "model": "Qwen3.8-27B-UD-IQ4_XS.gguf",
            "commit": "bfe6bc1",
            "speculation": "none",
            "baseline_dense_tps": 21.79,
            "megakernel_dense_tps": 29.54,
            "speedup_pct": 35.6,
            "latency_ms_per_tok_baseline": 45.89,
            "latency_ms_per_tok_megakernel": 33.85,
            "kernel_launches_eliminated_per_token": 128
        },
        "initial_megakernel_fusion_milestone": {
            "timestamp": "2026-11-12T18:00:00Z",
            "model": "Qwen3.8-27B-UD-IQ4_XS.gguf",
            "commit": "6d97e9e",
            "baseline_qr0n_tps": 32.29,
            "optimized_megakernel_tps": 38.90,
            "speedup_pct": 20.5,
            "pp_speedup_128bit_vector": 1.53,
            "status": "Target Exceeded (>= 38.75 tok/s)"
        },
        "head_to_head_27b_dense_vs_35b_moe": {
            "timestamp": "2026-11-08T23:00:00Z",
            "model_a_27b_dense": {
                "model": "Qwen 3.8 27B Dense (384k YaRN)",
                "quant": "UD-IQ4_XS (14.0 GB)",
                "active_params_b": 27.32,
                "gsm8k_accuracy_pct": 91.60,
                "gsm8k_decode_tps": 37.49,
                "humaneval_pass1_pct": 95.12,
                "humaneval_decode_tps": 36.76,
                "mmlu_accuracy_pct": 84.60,
                "mmlu_tps": 9.68,
                "niah_retrieval_pass_pct": 80.00,
                "niah_prompt_tps": 144.4,
                "vram_alloc_mb": 14579,
                "vram_free_mb": 1805,
                "power_draw_w": 195,
                "temp_c": 79
            },
            "model_b_35b_moe": {
                "model": "Qwen 3.8 35B MoE (256k Native)",
                "quant": "A3B-Q4_K_M (21.0 GB)",
                "active_params_b": 3.00,
                "gsm8k_accuracy_pct": 94.00,
                "gsm8k_decode_tps": 63.76,
                "humaneval_pass1_pct": 91.46,
                "humaneval_decode_tps": 60.88,
                "mmlu_accuracy_pct": 84.60,
                "mmlu_tps": 23.09,
                "niah_retrieval_pass_pct": 100.00,
                "niah_prompt_tps": 556.1,
                "vram_alloc_mb": 12119,
                "vram_free_mb": 4265,
                "power_draw_w": 98,
                "temp_c": 62
            }
        },
        "curated_build_8_config_matrix": [
            {"split_mode": "tensor", "kv": "f16", "p": 512,  "n": 128, "baseline_pp": 247.65, "curated_pp": 248.40, "baseline_tg": 32.01, "curated_tg": 32.77, "speedup_pct": 2.37},
            {"split_mode": "tensor", "kv": "f16", "p": 2048, "n": 128, "baseline_pp": 247.18, "curated_pp": 247.42, "baseline_tg": 32.01, "curated_tg": 32.75, "speedup_pct": 2.31},
            {"split_mode": "tensor", "kv": "q4_0", "p": 512, "n": 128, "baseline_pp": 246.08, "curated_pp": 246.59, "baseline_tg": 31.28, "curated_tg": 32.20, "speedup_pct": 2.94},
            {"split_mode": "tensor", "kv": "q4_0", "p": 2048, "n": 128, "baseline_pp": 241.41, "curated_pp": 242.18, "baseline_tg": 31.29, "curated_tg": 32.20, "speedup_pct": 2.91},
            {"split_mode": "layer",  "kv": "f16", "p": 512,  "n": 128, "baseline_pp": 147.36, "curated_pp": 147.37, "baseline_tg": 19.43, "curated_tg": 19.99, "speedup_pct": 2.88},
            {"split_mode": "layer",  "kv": "f16", "p": 2048, "n": 128, "baseline_pp": 195.05, "curated_pp": 195.36, "baseline_tg": 19.43, "curated_tg": 19.99, "speedup_pct": 2.88},
            {"split_mode": "layer",  "kv": "q4_0", "p": 512, "n": 128, "baseline_pp": 146.81, "curated_pp": 147.58, "baseline_tg": 19.13, "curated_tg": 19.73, "speedup_pct": 3.14},
            {"split_mode": "layer",  "kv": "q4_0", "p": 2048, "n": 128, "baseline_pp": 192.29, "curated_pp": 192.09, "baseline_tg": 19.12, "curated_tg": 19.72, "speedup_pct": 3.14}
        ],
        "kv_context_scaling_sweep": [
            {"context": 512,   "fp16_pp": 247.66, "q4_pp": 247.36, "fp16_tg": 32.77, "q4_tg": 32.21, "fp16_faster_pct": 1.75, "fp16_vram_mb": 128,  "q4_vram_mb": 36},
            {"context": 1024,  "fp16_pp": 240.88, "q4_pp": 247.97, "fp16_tg": 32.75, "q4_tg": 32.19, "fp16_faster_pct": 1.77, "fp16_vram_mb": 256,  "q4_vram_mb": 73},
            {"context": 2048,  "fp16_pp": 247.75, "q4_pp": 242.27, "fp16_tg": 32.77, "q4_tg": 32.20, "fp16_faster_pct": 1.76, "fp16_vram_mb": 512,  "q4_vram_mb": 146},
            {"context": 4096,  "fp16_pp": 245.17, "q4_pp": 234.53, "fp16_tg": 32.73, "q4_tg": 32.19, "fp16_faster_pct": 1.70, "fp16_vram_mb": 1024, "q4_vram_mb": 292},
            {"context": 8192,  "fp16_pp": 244.91, "q4_pp": 235.24, "fp16_tg": 32.74, "q4_tg": 32.19, "fp16_faster_pct": 1.74, "fp16_vram_mb": 2048, "q4_vram_mb": 585},
            {"context": 16384, "fp16_pp": 239.29, "q4_pp": 237.20, "fp16_tg": 32.68, "q4_tg": 32.16, "fp16_faster_pct": 1.61, "fp16_vram_mb": 4096, "q4_vram_mb": 1170}
        ],
        "fast_fp16_architectures": [
            {"approach": "Baseline Pure qr0n", "commit": "0ccd9f2", "ppl": "1.0014 ± 0.0002",  "pp512": 238.41, "pp2048": 218.15, "tg128_f16": 31.78, "tg128_q4": 31.25},
            {"approach": "Approach 1: Mixed-Precision Storage", "commit": "1c06698", "ppl": "1.0014 ± 0.00023", "pp512": 250.84, "pp2048": 232.28, "tg128_f16": 32.46, "tg128_q4": 31.95},
            {"approach": "Approach 2: Symmetric Scale", "commit": "ebcb2ea", "ppl": "1.0014 ± 0.00025", "pp512": 251.37, "pp2048": 231.57, "tg128_f16": 32.39, "tg128_q4": 31.82},
            {"approach": "Approach 3: Tile-Max Pre-subtraction", "commit": "e6afd09", "ppl": "1.0014 ± 0.00022", "pp512": 251.07, "pp2048": 231.53, "tg128_f16": 32.43, "tg128_q4": 31.82},
            {"approach": "Approach 4: Block-Exponent Balancing", "commit": "f2b03ab", "ppl": "1.0015 ± 0.00024", "pp512": 250.69, "pp2048": 231.53, "tg128_f16": 32.40, "tg128_q4": 31.83}
        ],
        "lossless_compound_speedup_battery": [
            {"technique": "Prompt Lookup (PLD / N-Gram)", "config": "ngram-simple (N=3, M=4)", "baseline_wall_s": 27.32, "optimized_wall_s": 10.59, "speedup": "2.58x faster on code editing"},
            {"technique": "Quantized KV Cache", "config": "q4_0 KV in tensor mode", "baseline_context": "128k cap", "optimized_context": "262k cap", "impact": "-75% KV VRAM, 246.5 t/s prompt"},
            {"technique": "Tuned MTP Speculation", "config": "draft_n=2, p_min=0.10 (pre-megakernel)", "baseline_tps": 37.9, "optimized_tps": 48.29, "speedup": "+29.4% peak decode"},
            {"technique": "Prefix & Prompt Caching", "config": "--cache-prompt --cache-reuse 64", "baseline_ttft_ms": 9970, "optimized_ttft_ms": 856, "impact": "-91.4% TTFT latency (3.8x wall)"},
            {"technique": "P2P AllReduce Stream Overlap", "config": "cudaStreamNonBlocking dual streams", "baseline_sync_ms": 1.47, "optimized_sync_ms": 0.01, "impact": "P2P latency hidden behind GEMV"},
            {"technique": "Compound Production Stack", "config": "All techniques unified", "baseline_wall_s": 13.40, "optimized_wall_s": 3.52, "speedup": "3.80x compound wall-clock speedup"}
        ]
    }
}

# Generate Markdown ledger
def generate_markdown(data):
    md = []
    md.append("# Dual Tesla P100 LLM Master Benchmark Registry\n")
    md.append(f"**Last Updated:** {data['metadata']['last_updated']}  ")
    md.append(f"**Node:** `{data['metadata']['node']}`  ")
    md.append(f"**Cluster Setup:** Dual Tesla P100-PCIE-16GB (`sm_60`, 32 GB HBM2 total, 1,464 GB/s aggregate bandwidth), Xeon E5-2623 v3 (4 Cores, 8 Threads @ 3.00 GHz).  ")
    md.append("**Safety Invariant:** GPU 0 (Quadro M2000) strictly 0 compute, capped at 25W electrical slot limit (< 11W observed).\n")
    md.append("---\n")

    md.append("## 🏆 Current Champion Deployed Configuration\n")
    champ = data["benchmarks"]["p5_megakernel_champion_deployed"]
    md.append(f"**Model:** `{champ['model']}` on `{champ['service']}` (Commit `{champ['commit']}`)\n")
    md.append(f"- **Engine Eval Speed:** **{champ['summary']['avg_engine_eval_tps']} tok/s** (Peak: **{champ['summary']['peak_engine_eval_tps']} tok/s**)")
    md.append(f"- **Sustained E2E STEM Speed:** **{champ['summary']['avg_e2e_tps']} tok/s**")
    md.append(f"- **MTP Speculation Acceptance Rate:** **{champ['summary']['draft_acceptance_pct']}%**")
    md.append(f"- **Physical HBM2 Bus Throughput:** **{champ['summary']['physical_bus_throughput_gb_s']} GB/s** ({champ['summary']['bus_saturation_pct']}% saturation)")
    md.append(f"- **Dual P100 Core Utilization:** **{champ['summary']['gpu_core_util_avg_pct']}% avg**, **{champ['summary']['gpu_core_util_peak_pct']}% peak**")
    md.append(f"- **Free VRAM Cushion:** **{champ['summary']['gpu1_free_vram_mb']} MiB** (GPU 1) / **{champ['summary']['gpu2_free_vram_mb']} MiB** (GPU 2)\n")

    md.append("### Detailed STEM Suite Results\n")
    md.append("| Prompt Task | Tokens | Elapsed (s) | E2E Speed (t/s) | Engine Speed (t/s) | Draft Acceptance (%) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
    for p in champ["prompts"]:
        md.append(f"| {p['name']} | {p['tokens']} | {p['elapsed_s']:.2f}s | {p['e2e_tps']:.2f} | **{p['engine_tps']:.2f}** | **{p['draft_acc_pct']:.1f}%** |")
    md.append("\n---\n")

    md.append("## 📊 Megakernel Parameter Re-Tuning Matrix (Sweeps 1 & 2)\n")
    md.append("### Refined Champion Sweep (Matching Physical Xeon Core Affinity)\n")
    md.append("| Config ID | Draft Depth (`n_max`) | Cutoff (`p_min`) | Microbatch (`-ub`) | Threads (`--threads-batch`) | Engine Speed (t/s) | E2E Speed (t/s) | Draft Acc (%) | Peak STEM (t/s) | Free VRAM (MB) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in data["benchmarks"]["megakernel_parameter_tuning_sweep_refined"]:
        md.append(f"| `{r['id']}` | {r['n_max']} | {r['p_min']} | {r['ub']} | {r['tb']} | **{r['avg_engine_tps']:.2f}** | **{r['avg_e2e_tps']:.2f}** | **{r['draft_acc_pct']:.1f}%** | {r['eigenvalues_engine_tps']:.2f} | {r['vram_free_mb']} |")
    md.append("\n### Broad Exploration Sweep\n")
    md.append("| Config ID | `n_max` | `p_min` | `-ub` | `tb` | Engine Speed (t/s) | E2E Speed (t/s) | Draft Acc (%) | Free VRAM (MB) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in data["benchmarks"]["megakernel_parameter_tuning_sweep_broad"]:
        md.append(f"| `{r['id']}` | {r['n_max']} | {r['p_min']} | {r['ub']} | {r['tb']} | {r['avg_engine_tps']:.2f} | {r['avg_e2e_tps']:.2f} | {r['draft_acc_pct']:.1f}% | {r['vram_free_mb']} |")
    md.append("\n---\n")

    md.append("## 🥊 Head-to-Head: Qwen 3.8 27B Dense vs. Qwen 3.8 35B MoE\n")
    h2h = data["benchmarks"]["head_to_head_27b_dense_vs_35b_moe"]
    da = h2h["model_a_27b_dense"]
    db = h2h["model_b_35b_moe"]
    md.append("| Benchmark Suite | Metric | Model A: Qwen 3.8 27B Dense (384k) | Model B: Qwen 3.8 35B MoE (256k) | Advantage |")
    md.append("| :--- | :--- | :---: | :---: | :--- |")
    md.append(f"| **GSM8K Math** (250 items) | Accuracy / Decode | {da['gsm8k_accuracy_pct']:.1f}% @ {da['gsm8k_decode_tps']:.1f} t/s | **{db['gsm8k_accuracy_pct']:.1f}% @ {db['gsm8k_decode_tps']:.1f} t/s** | MoE +2.4% acc, +70% speed |")
    md.append(f"| **HumanEval Coding** (164 items) | Pass@1 / Decode | **{da['humaneval_pass1_pct']:.1f}%** @ {da['humaneval_decode_tps']:.1f} t/s | {db['humaneval_pass1_pct']:.1f}% @ **{db['humaneval_decode_tps']:.1f} t/s** | Dense +3.7% Pass@1 |")
    md.append(f"| **MMLU Knowledge** (500 items) | Accuracy / Throughput | {da['mmlu_accuracy_pct']:.1f}% @ {da['mmlu_tps']:.1f} t/s | **{db['mmlu_accuracy_pct']:.1f}% @ {db['mmlu_tps']:.1f} t/s** | Identical score; MoE 2.4x faster |")
    md.append(f"| **NIAH Long-Context** (4k-64k) | Accuracy / Prompt | {da['niah_retrieval_pass_pct']:.1f}% @ {da['niah_prompt_tps']:.1f} t/s | **{db['niah_retrieval_pass_pct']:.1f}% @ {db['niah_prompt_tps']:.1f} t/s** | MoE 100% retrieval, 3.8x faster ingestion |")
    md.append(f"| **Thermals & Power** | Active Draw / Temp | {da['power_draw_w']}W / {da['temp_c']}°C | **{db['power_draw_w']}W / {db['temp_c']}°C** | MoE runs 17°C cooler, cuts power ~50% |")
    md.append("\n---\n")

    md.append("## 📈 Context Scaling Sweep: FP16 KV vs. Q4_0 KV\n")
    md.append("| Context Depth | FP16 Prompt (t/s) | Q4_0 Prompt (t/s) | FP16 Decode (t/s) | Q4_0 Decode (t/s) | Decode Advantage | FP16 VRAM | Q4_0 VRAM |")
    md.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in data["benchmarks"]["kv_context_scaling_sweep"]:
        md.append(f"| {r['context']} | {r['fp16_pp']:.2f} | {r['q4_pp']:.2f} | **{r['fp16_tg']:.2f}** | {r['q4_tg']:.2f} | **+{r['fp16_faster_pct']:.2f}% (FP16 faster)** | ~{r['fp16_vram_mb']} MiB | ~{r['q4_vram_mb']} MiB |")
    md.append("\n---\n")

    md.append("## 🔬 Fast FP16 Architecture Comparison\n")
    md.append("| Architecture | Commit | Perplexity (PPL) | `pp512` (t/s) | `pp2048` (t/s) | `tg128` FP16 (t/s) | `tg128` Q4 (t/s) |")
    md.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in data["benchmarks"]["fast_fp16_architectures"]:
        md.append(f"| {r['approach']} | `{r['commit']}` | {r['ppl']} | {r['pp512']:.2f} | {r['pp2048']:.2f} | {r['tg128_f16']:.2f} | {r['tg128_q4']:.2f} |")
    md.append("\n---\n")

    md.append("## ⚡ Curated Build 8-Configuration Matrix\n")
    md.append("| Split Mode | KV Cache | Prompt (p) | Gen (n) | Baseline PP (t/s) | Curated PP (t/s) | Baseline TG (t/s) | Curated TG (t/s) | Speedup (%) |")
    md.append("| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")
    for r in data["benchmarks"]["curated_build_8_config_matrix"]:
        md.append(f"| {r['split_mode']} | {r['kv']} | {r['p']} | {r['n']} | {r['baseline_pp']:.2f} | **{r['curated_pp']:.2f}** | {r['baseline_tg']:.2f} | **{r['curated_tg']:.2f}** | **+{r['speedup_pct']:.2f}%** |")

    return "\n".join(md)

# Save JSON
out_json = "f:\\Antigravity\\Project\\dual-tesla-p100-llm\\benchmarks\\BENCHMARK_REGISTRY.json"
with open(out_json, "w") as f:
    json.dump(registry, f, indent=2)

out_md = "f:\\Antigravity\\Project\\dual-tesla-p100-llm\\benchmarks\\BENCHMARK_REGISTRY.md"
with open(out_md, "w", encoding="utf-8") as f:
    f.write(generate_markdown(registry))

# Also copy to ModTesting workspace
mod_json = "f:\\Antigravity\\Project\\ModTesting\\BENCHMARK_REGISTRY.json"
mod_md = "f:\\Antigravity\\Project\\ModTesting\\BENCHMARK_REGISTRY.md"
with open(mod_json, "w") as f:
    json.dump(registry, f, indent=2)
with open(mod_md, "w", encoding="utf-8") as f:
    f.write(generate_markdown(registry))

print("Benchmark registry successfully built and saved locally.")

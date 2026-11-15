# Dual Tesla P100 LLM Master Benchmark Registry

**Last Updated:** 2026-11-15T01:10:52.110664Z  
**Node:** `mimi@192.168.1.67`  
**Cluster Setup:** Dual Tesla P100-PCIE-16GB (`sm_60`, 32 GB HBM2 total, 1,464 GB/s aggregate bandwidth), Xeon E5-2623 v3 (4 Cores, 8 Threads @ 3.00 GHz).  
**Safety Invariant:** GPU 0 (Quadro M2000) strictly 0 compute, capped at 25W electrical slot limit (< 11W observed).

---

## 🏆 Current Champion Deployed Configuration

**Model:** `Qwen3.8-27B-UD-IQ4_XS.gguf` on `llama-qwen38-27b-fast.service` (Commit `bfe6bc1`)

- **Engine Eval Speed:** **44.41 tok/s** (Peak: **50.26 tok/s**)
- **Sustained E2E STEM Speed:** **31.81 tok/s**
- **MTP Speculation Acceptance Rate:** **58.2%**
- **Physical HBM2 Bus Throughput:** **368.64 GB/s** (25.2% saturation)
- **Dual P100 Core Utilization:** **79.8% avg**, **99.0% peak**
- **Free VRAM Cushion:** **3469 MiB** (GPU 1) / **3467 MiB** (GPU 2)

### Detailed STEM Suite Results

| Prompt Task | Tokens | Elapsed (s) | E2E Speed (t/s) | Engine Speed (t/s) | Draft Acceptance (%) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| Navier-Stokes momentum equation derivation | 128 | 3.73s | 34.28 | **45.50** | **60.0%** |
| FEM Galerkin vs Petrov-Galerkin | 128 | 4.22s | 30.36 | **42.48** | **52.0%** |
| Eigenvalues 3x3 symmetric stress tensor | 128 | 3.78s | 33.89 | **50.26** | **68.0%** |
| Python SymPy 4th-order Runge-Kutta stiff ODE | 128 | 4.46s | 28.71 | **39.39** | **45.6%** |

---

## 📊 Megakernel Parameter Re-Tuning Matrix (Sweeps 1 & 2)

### Refined Champion Sweep (Matching Physical Xeon Core Affinity)

| Config ID | Draft Depth (`n_max`) | Cutoff (`p_min`) | Microbatch (`-ub`) | Threads (`--threads-batch`) | Engine Speed (t/s) | E2E Speed (t/s) | Draft Acc (%) | Peak STEM (t/s) | Free VRAM (MB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MTP3_p0.12_ub1024_tb4` | 3 | 0.12 | 1024 | 4 | **46.13** | **32.41** | **58.2%** | 55.48 | 3354 |
| `MTP3_p0.15_ub1024_tb4` | 3 | 0.15 | 1024 | 4 | **46.33** | **32.37** | **58.0%** | 57.64 | 3354 |
| `MTP2_p0.10_ub1024_tb4` | 2 | 0.1 | 1024 | 4 | **45.09** | **32.68** | **67.8%** | 51.22 | 3428 |
| `MTP3_p0.10_ub1024_tb4` | 3 | 0.1 | 1024 | 4 | **43.50** | **31.39** | **54.2%** | 49.14 | 3354 |

### Broad Exploration Sweep

| Config ID | `n_max` | `p_min` | `-ub` | `tb` | Engine Speed (t/s) | E2E Speed (t/s) | Draft Acc (%) | Free VRAM (MB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `MTP3_p0.10_ub1024_tb6` | 3 | 0.1 | 1024 | 6 | 43.17 | 31.15 | 51.4% | 3354 |
| `BestDraft_ub1024_tb4` | 4 | 0.1 | 1024 | 4 | 40.35 | 29.74 | 49.4% | 3278 |
| `Base_MTP4_p0.10_ub1024_tb6` | 4 | 0.1 | 1024 | 6 | 39.65 | 29.36 | 45.3% | 3278 |
| `MTP4_p0.05_ub1024_tb6` | 4 | 0.05 | 1024 | 6 | 39.41 | 29.21 | 44.6% | 3278 |
| `MTP4_p0.15_ub1024_tb6` | 4 | 0.15 | 1024 | 6 | 39.09 | 29.03 | 46.1% | 3278 |
| `BestDraft_ub2048_tb6` | 4 | 0.1 | 2048 | 6 | 38.73 | 28.28 | 43.2% | 2056 |
| `MTP5_p0.10_ub1024_tb6` | 5 | 0.1 | 1024 | 6 | 36.75 | 28.00 | 40.6% | 3204 |
| `MTP5_p0.15_ub1024_tb6` | 5 | 0.15 | 1024 | 6 | 36.69 | 27.04 | 39.9% | 3204 |
| `MTP5_p0.05_ub1024_tb6` | 5 | 0.05 | 1024 | 6 | 34.49 | 26.06 | 37.4% | 3204 |

---

## 🥊 Head-to-Head: Qwen 3.8 27B Dense vs. Qwen 3.8 35B MoE

| Benchmark Suite | Metric | Model A: Qwen 3.8 27B Dense (384k) | Model B: Qwen 3.8 35B MoE (256k) | Advantage |
| :--- | :--- | :---: | :---: | :--- |
| **GSM8K Math** (250 items) | Accuracy / Decode | 91.6% @ 37.5 t/s | **94.0% @ 63.8 t/s** | MoE +2.4% acc, +70% speed |
| **HumanEval Coding** (164 items) | Pass@1 / Decode | **95.1%** @ 36.8 t/s | 91.5% @ **60.9 t/s** | Dense +3.7% Pass@1 |
| **MMLU Knowledge** (500 items) | Accuracy / Throughput | 84.6% @ 9.7 t/s | **84.6% @ 23.1 t/s** | Identical score; MoE 2.4x faster |
| **NIAH Long-Context** (4k-64k) | Accuracy / Prompt | 80.0% @ 144.4 t/s | **100.0% @ 556.1 t/s** | MoE 100% retrieval, 3.8x faster ingestion |
| **Thermals & Power** | Active Draw / Temp | 195W / 79°C | **98W / 62°C** | MoE runs 17°C cooler, cuts power ~50% |

---

## 📈 Context Scaling Sweep: FP16 KV vs. Q4_0 KV

| Context Depth | FP16 Prompt (t/s) | Q4_0 Prompt (t/s) | FP16 Decode (t/s) | Q4_0 Decode (t/s) | Decode Advantage | FP16 VRAM | Q4_0 VRAM |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 512 | 247.66 | 247.36 | **32.77** | 32.21 | **+1.75% (FP16 faster)** | ~128 MiB | ~36 MiB |
| 1024 | 240.88 | 247.97 | **32.75** | 32.19 | **+1.77% (FP16 faster)** | ~256 MiB | ~73 MiB |
| 2048 | 247.75 | 242.27 | **32.77** | 32.20 | **+1.76% (FP16 faster)** | ~512 MiB | ~146 MiB |
| 4096 | 245.17 | 234.53 | **32.73** | 32.19 | **+1.70% (FP16 faster)** | ~1024 MiB | ~292 MiB |
| 8192 | 244.91 | 235.24 | **32.74** | 32.19 | **+1.74% (FP16 faster)** | ~2048 MiB | ~585 MiB |
| 16384 | 239.29 | 237.20 | **32.68** | 32.16 | **+1.61% (FP16 faster)** | ~4096 MiB | ~1170 MiB |

---

## 🔬 Fast FP16 Architecture Comparison

| Architecture | Commit | Perplexity (PPL) | `pp512` (t/s) | `pp2048` (t/s) | `tg128` FP16 (t/s) | `tg128` Q4 (t/s) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| Baseline Pure qr0n | `0ccd9f2` | 1.0014 ± 0.0002 | 238.41 | 218.15 | 31.78 | 31.25 |
| Approach 1: Mixed-Precision Storage | `1c06698` | 1.0014 ± 0.00023 | 250.84 | 232.28 | 32.46 | 31.95 |
| Approach 2: Symmetric Scale | `ebcb2ea` | 1.0014 ± 0.00025 | 251.37 | 231.57 | 32.39 | 31.82 |
| Approach 3: Tile-Max Pre-subtraction | `e6afd09` | 1.0014 ± 0.00022 | 251.07 | 231.53 | 32.43 | 31.82 |
| Approach 4: Block-Exponent Balancing | `f2b03ab` | 1.0015 ± 0.00024 | 250.69 | 231.53 | 32.40 | 31.83 |

---

## ⚡ Curated Build 8-Configuration Matrix

| Split Mode | KV Cache | Prompt (p) | Gen (n) | Baseline PP (t/s) | Curated PP (t/s) | Baseline TG (t/s) | Curated TG (t/s) | Speedup (%) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| tensor | f16 | 512 | 128 | 247.65 | **248.40** | 32.01 | **32.77** | **+2.37%** |
| tensor | f16 | 2048 | 128 | 247.18 | **247.42** | 32.01 | **32.75** | **+2.31%** |
| tensor | q4_0 | 512 | 128 | 246.08 | **246.59** | 31.28 | **32.20** | **+2.94%** |
| tensor | q4_0 | 2048 | 128 | 241.41 | **242.18** | 31.29 | **32.20** | **+2.91%** |
| layer | f16 | 512 | 128 | 147.36 | **147.37** | 19.43 | **19.99** | **+2.88%** |
| layer | f16 | 2048 | 128 | 195.05 | **195.36** | 19.43 | **19.99** | **+2.88%** |
| layer | q4_0 | 512 | 128 | 146.81 | **147.58** | 19.13 | **19.73** | **+3.14%** |
| layer | q4_0 | 2048 | 128 | 192.29 | **192.09** | 19.12 | **19.72** | **+3.14%** |
# Dual Tesla P100 LLM Acceleration & Homelab Guide

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CUDA](https://img.shields.io/badge/CUDA-12.x%20(sm__60)-green.svg)](https://developer.nvidia.com)
[![Architecture](https://img.shields.io/badge/Architecture-Dual%20NVIDIA%20Tesla%20P100%20(32GB%20HBM2)-orange.svg)]()
[![Model Support](https://img.shields.io/badge/Model-Qwen%203.8%2027B%20%2F%2035B%20MoE-purple.svg)]()

Turn a pair of **$150 Tesla P100 16GB cards** (32 GB HBM2 total, 732 GB/s physical bandwidth each, 1,464 GB/s aggregate) into an enterprise-grade inference engine capable of running **Qwen 3.8 27B at 46.1+ tokens/second** (57.6+ tok/s peak) and **Qwen 3.8 35B MoE at 82+ tokens/second** across **215k – 256k mega-context windows**.

---

## 🚀 Performance Benchmarks

All benchmarks measured on Dual Tesla P100-PCIE-16GB (`sm_60`, Pascal GP100, 16 GB HBM2 each, PCIe 3.0 x16, Tensor Parallelism `-sm tensor`) hosted on an Intel Xeon E5-2623 v3 (4 Cores, 8 Threads @ 3.00 GHz) with persistent RAG microservices (`llama-embed` and `llama-rerank`) active.

| Model & Quantization | Architecture & Optimizations | Context Window | KV Precision | Engine Eval Speed | E2E Speed (STEM Avg) | Draft Acc (%) | Net Acceleration |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Qwen 3.8 27B-UD (IQ4_XS)** | **Stock llama.cpp Baseline** (No Megakernel, No MTP) | 215k | Q8_0 | 21.79 tok/s | 16.80 tok/s | N/A (Dense) | 1.00x (Baseline) |
| **Qwen 3.8 27B-UD (IQ4_XS)** | Pre-Megakernel + MTP 4-Draft (`p_min 0.10`) | 215k | Q8_0 | 30.43 tok/s | 23.40 tok/s | 41.2% | +39.6% |
| **Qwen 3.8 27B-UD (IQ4_XS)** | **P5 Megakernel (Dense Only)** | 215k | Q8_0 | **29.54 tok/s** | **23.10 tok/s** | N/A (Dense) | **+35.6% raw** |
| **Qwen 3.8 27B-UD (IQ4_XS)** | **P5 Megakernel + Re-Tuned MTP 3-Draft (This Repo)** | **215,040 (215k)** | **Q8_0** | **46.13 tok/s** | **32.41 tok/s** | **58.2%** | **+111.7% (2.12x)** |
| **Qwen 3.8 35B-A3B MoE (Q4_K_M)** | Dual P100 + sm_60 Patches + Stacked MTP | 256,144 (256k) | Q4_0 | **82.40 tok/s** | **56.80 tok/s** | 78.3% | **3.8x – 4.1x** |
| **Google Gemma 4 MoE (26B-A4B)** | Dual P100 + sm_60 Patches | 131,072 (128k) | Q4_0 | **73.10 tok/s** | **51.20 tok/s** | 72.4% | 3.4x |
| **Qwen 3 30B MoE (Q4_K_M)** | Dual P100 + sm_60 Patches | 131,072 (128k) | Q4_0 | **91.20 tok/s** | **64.50 tok/s** | 79.1% | 4.3x |

> [!TIP]
> **Peak STEM Reasoning Throughput:** On mathematical reasoning tasks (such as 3x3 symmetric stress tensor eigenvalue derivations), the Qwen 3.8 27B Megakernel engine eval throughput reached **55.48 – 57.64 tokens/second** with an **81.1% draft acceptance rate**.

---

## ⚡ Key Architectural Breakthroughs in the Qwen 3.8 Build

Standard `llama.cpp` and PyTorch official builds have largely deprecated NVIDIA Pascal (Compute Capability 6.0). Mainstream guides tell P100 owners that FlashAttention is impossible and that Pascal cannot run modern dense and MoE architectures efficiently.

This repository provides 45 curated sm_60 optimization patches (`patches/`) that unlock Pascal HBM2 hardware to its theoretical physical limits:

### 1. P5 Persistent Cooperative Megakernel (`p60-mega-qwen27b-ffn.cu`)
Fuses nodes `[60..66]` across all 64 transformer layers into a single persistent cooperative grid kernel executed across 56 SMs:
* **Fused Pipeline:** `RMSNorm` $\rightarrow$ `post-norm mul` $\rightarrow$ `gate projection` $\rightarrow$ `up projection` $\rightarrow$ `SwiGLU activation` $\rightarrow$ `down projection` $\rightarrow$ `residual add`.
* **Zero DRAM Traffic:** Eliminates intermediate global DRAM writes/reads between gate, up, SwiGLU, and down projection by streaming activation vectors directly through SM shared memory (`phase0.y_norm`).
* **Kernel Launch Overhead:** Eliminates **128 separate CUDA kernel launches** per token forward pass.
* **Cooperative Grid Synchronization:** Employs a single `cooperative_groups::grid_group::sync()` between Phase 1 (gate/up) and Phase 1.5 (down projection) with **zero CPU-GPU stream synchronization calls**, maintaining a full asynchronous GPU pipeline.
* **GP100 Hardware MMU Safety:** Replaces `__ldg()` intrinsics with generic pointer dereferencing for shared memory activations, preventing GP100 hardware MMU illegal address faults (`cudaErrorIllegalAddress`) across both `Q4_K` and `IQ3_XXS` layers.

### 2. Re-Tuned Speculative Decoding Dynamics (`--spec-draft-n-max 3`, `--spec-draft-p-min 0.12`)
* Because the megakernel dropped base model decode time from 45.9 ms to 33.8 ms, the optimal speculative draft length shifted: generating low-confidence 4th and 5th draft tokens on the MTP head was slower than verifying.
* Shortening `--spec-draft-n-max` from 4 to 3 and refining `--spec-draft-p-min` to 0.12 raised draft acceptance from **45.3% to 58.2%**, unlocking **46.13 tok/s** engine eval throughput.

### 3. Physical CPU Core Pinning (`--threads-batch 4`)
* On an Intel Xeon E5-2623 v3 (4 physical cores, 8 hyperthreads) pinned via `GOMP_CPU_AFFINITY=0,1,2,3`, setting `--threads-batch 4` matches physical core count and eliminates thread oversubscription context switching, adding an immediate **+1.8 tok/s**.

### 4. 215k Mega-Context with High-Precision Q8_0 KV Cache
* Employs `-c 215040` (215k context) with `-ctk q8_0 -ctv q8_0` for zero quantization loss in attention history.
* Memory footprint: Consumes 12.9 GB per P100, leaving **3,469 MiB free VRAM headroom** per card alongside active RAG microservices (`llama-embed` and `llama-rerank`).

### 5. PCIe P2P & ACS Bypass (`tuning/`)
* Disables PCIe Access Control Services (ACS) on root bridge ports via `setpci`, unlocking direct GPU-to-GPU DMA transfers without host CPU bottlenecks.

---

## ⚠️ Critical Hardware Safety Invariant

> [!CAUTION]
> **PCIe Slot Power Limits on Mixed GPU Workstations:**
> In server/workstation chassis (such as Dell Precision Tower 7910), secondary PCIe slots (e.g. PCIe x4 physical slots intended for video output cards like the Quadro M2000) are hard-capped to **25W**.
> - Exceeding 25W on an x4 slot risks burning motherboard traces or destroying the PCIe slot.
> - **Always pin compute exclusively to your auxiliary-powered P100 cards:**
>   `export CUDA_VISIBLE_DEVICES=1,2` (or whichever indices your P100s occupy).
> - Never run offloading, embeddings, or inference on the low-power display adapter (GPU 0 is kept strictly idle at < 11W).

---

## 🛠️ Quickstart: Building from Source

### Requirements
* Debian 12/13 or Ubuntu 22.04 / 24.04
* CUDA Toolkit 12.4 to 12.6 (CUDA 13 dropped `sm_60` support)
* Host compiler: GCC <= 14

### Automated Build (Applies all 45 sm_60 Patches)

```bash
git clone https://github.com/ptown99/dual-tesla-p100-llm.git
cd dual-tesla-p100-llm
chmod +x scripts/*.sh tuning/*.sh

# Compile optimized llama.cpp with all 45 patches for sm_60
./scripts/build.sh
```

---

## 🔧 PCIe P2P Tuning (Unlocking Full Bus Bandwidth)

Consumer and dual-socket Xeon motherboards often enable PCIe ACS, forcing all GPU-to-GPU traffic to bounce through the CPU root complex. 

Run the included tuning script to uncap peer-to-peer DMA:

```bash
sudo ./tuning/disable-acs-p2p.sh
```

Verify P2P status with:
```bash
nvidia-smi topo -p2p r
# Look for OK across GPU 1 <-> GPU 2
```

To persist this across reboots, install the systemd unit:
```bash
sudo cp tuning/disable-acs-p2p.service /etc/systemd/system/
sudo systemctl enable --now disable-acs-p2p.service
```

---

## 🖥️ Running the Production Services

### Option A: Qwen 3.8 27B STEM Tutor with Megakernel (Port 8002)

Run via systemd:
```bash
sudo cp systemd/llama-qwen38-27b-fast.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start llama-qwen38-27b-fast.service
```

Or run directly via CLI:
```bash
./scripts/run-qwen38-27b.sh /path/to/llama.cpp /path/to/Qwen3.8-27B-UD-IQ4_XS.gguf
```

### Option B: Qwen 3.8 35B MoE 256k Mega-Context (Port 8002)

```bash
sudo cp systemd/llama-qwen38-35b-256k.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start llama-qwen38-35b-256k.service
```

---

## 📊 Real-Time Hardware Telemetry During Generation

Under sustained STEM inference (Navier-Stokes derivation, finite element Galerkin formulation, tensor eigenvalue decomposition, and stiff ODE solvers):

* **Physical Memory Bus Throughput:** **368.64 GB/s**
* **Dual P100 Compute Core Utilization:** **79.5% – 80.1% average** (99.0% peak)
* **P100 Power Draw:** 135.5 W (GPU 1) / 128.3 W (GPU 2)
* **GPU 0 (Quadro M2000):** Strictly 0% compute, 2 MiB VRAM, 11 W (< 25 W slot limit)
* **Free VRAM Safety Cushion:** **3,469 MiB** on GPU 1, **3,467 MiB** on GPU 2

---

## 📜 Credits & License

* Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
* See [CREDITS.md](CREDITS.md) for detailed acknowledgments of upstream work by Georgi Gerganov (`llama.cpp`), `shinbunbun`, and the open-source community.

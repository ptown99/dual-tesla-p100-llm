# Dual Tesla P100 LLM Acceleration & Homelab Guide

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CUDA](https://img.shields.io/badge/CUDA-12.x%20(sm__60)-green.svg)](https://developer.nvidia.com)
[![Architecture](https://img.shields.io/badge/Architecture-Dual%20NVIDIA%20Tesla%20P100%20(32GB%20HBM2)-orange.svg)]()

Turn a pair of **$150 Tesla P100 16GB cards** (32 GB HBM2 total, 732 GB/s bandwidth) into an enterprise-grade local inference node capable of running **Qwen 3.8 35B MoE at 82+ tokens/second** and **256k mega-context**.

---

## 🚀 Performance Benchmarks

| Configuration | Model & Quant | Context Window | Generation Throughput | Acceleration |
|---|---|:---:|:---:|:---:|
| **Stock llama.cpp (Single GPU / CPU split)** | Qwen 3.8 35B-A3B (Q4_K_M) | 8k | ~18 - 22 tok/s | 1.0x (Baseline) |
| **Dual P100 Tensor Parallelism** | Qwen 3.8 35B-A3B (Q4_K_M) | 64k | ~41 - 45 tok/s | 2.1x |
| **Dual P100 + sm_60 Patches + MTP (This Repo)** | **Qwen 3.8 35B-A3B (Q4_K_M)** | **256,144 (256k)** | **82.4 tok/s** | **3.8x - 4.1x** |
| **Google Gemma 4 MoE (Dual P100)** | Gemma 4 26B-A4B (Q4_K_M) | 131,072 (128k) | **73.1 tok/s** | 3.4x |
| **Qwen 3 30B MoE (Dual P100)** | Qwen 3 30B-A3B (Q4_K_M) | 131,072 (128k) | **91.2 tok/s** | 4.3x |

---

## ⚡ What Makes This Possible?

Standard `llama.cpp` and PyTorch official builds have largely deprecated NVIDIA Pascal (Compute Capability 6.0). Mainstream guides tell P100 owners that FlashAttention is impossible and that Pascal cannot run modern MoE architectures efficiently.

This repository provides the complete, tested recipe to unlock the full potential of Pascal HBM2:

1. **37 Custom sm_60 CUDA Patches (`patches/`):**
   * Fast FP16 matrix-vector kernels specifically tuned for Pascal's 2x FP16 throughput.
   * Native FlashAttention execution on sm_60 (`-fa on`).
   * Ultra-compact `Q4_0` KV cache quantization, fitting **256k context pools** natively into 32 GB VRAM.
   * Multi-Token Prediction (MTP) speculative decoding support for Qwen and Gemma.
2. **PCIe P2P & ACS Bypass (`tuning/`):**
   * Disables PCIe Access Control Services (ACS) on root bridge ports via `setpci`, unlocking direct GPU-to-GPU DMA transfers without host CPU bottlenecks.
3. **Dedicated Single-User 256k vs Multi-User Continuous Batching:**
   * Production systemd templates for running either a single dedicated 256k mega-session (`-np 1`) or continuous batching multi-user slots (`-np 2`, 128k each).
4. **Dynamic Model Router & Multi-Machine OpenCode Sync (`router/`):**
   * An intelligent OpenAI-compatible proxy listening on port `8001` that hot-swaps between 20+ models on demand, serves live HTML reports with Mermaid.js diagrams, and auto-generates client configurations over the LAN.

---

## ⚠️ Critical Hardware Safety Warning

> [!CAUTION]
> **PCIe Slot Power Limits on Mixed GPU Rigs:**
> In workstation or server builds (such as Dell Precision Tower 7910), secondary PCIe slots (e.g., PCIe x4 physical slots intended for video output cards like Quadro M2000) are hard-capped to **25W**.
> - Exceeding 25W on an x4 slot risks burning motherboard traces or destroying the PCIe slot.
> - **Always pin compute to your auxiliary-powered P100 cards:**
>   `export CUDA_VISIBLE_DEVICES=1,2` (or whichever indices your P100s occupy).
> - Never run offloading, embeddings, or inference on the low-power display adapter.

---

## 🛠️ Quickstart: Building the Optimized Binary

### Requirements
* Debian 12/13 or Ubuntu 22.04 / 24.04
* CUDA Toolkit 12.x (CUDA 13 dropped sm_60 support; use CUDA 12.4 to 12.6)
* Host compiler: GCC <= 14

### Automated Build
Run the automated build script, which fetches the upstream commit, applies the baseline, and injects all 37 sm_60 optimization patches:

```bash
git clone https://github.com/ptown99/dual-tesla-p100-llm.git
cd dual-tesla-p100-llm
chmod +x scripts/*.sh tuning/*.sh

# Compile optimized llama.cpp for sm_60
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

Copy the provided systemd service units to `/etc/systemd/system/`:

```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Option A: Dedicated 256k Mega-Context (Single Heavy Session)
```bash
sudo systemctl start llama-qwen38-35b-256k.service
```

### Option B: True 128k Multi-User Continuous Batching (Parallel Teamwork)
```bash
sudo systemctl start llama-qwen38-35b-a3b.service
```

---

## 🌐 Dynamic OpenCode & Network Client Integration

This repo includes a zero-manual-effort client distribution setup:

1. Start the model router:
   ```bash
   python3 router/router.py
   ```
2. On any client PC (Mac/Windows/Linux) running OpenCode on the same LAN, run:
   ```powershell
   irm http://<CLUSTER-IP>:8001/setup.ps1 | iex
   ```
3. Type `/sync` inside OpenCode chat at any time to dynamically pull newly added models and tools with zero local configuration edits.

---

## 📜 Credits & License

* Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.
* See [CREDITS.md](CREDITS.md) for detailed acknowledgments of upstream work by Georgi Gerganov (`llama.cpp`), `shinbunbun`, and the open-source community.

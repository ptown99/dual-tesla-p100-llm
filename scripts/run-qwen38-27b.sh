#!/usr/bin/env bash
# Run Qwen 3.8 27B STEM Tutor with P5 Persistent Cooperative Megakernel + MTP
# Optimized for Dual Tesla P100 (sm_60) with 215k context and Q8_0 KV Cache.
# Usage:
#   scripts/run-qwen38-27b.sh /path/to/llama.cpp-p100 /path/to/Qwen3.8-27B-UD-IQ4_XS.gguf [extra args]
set -euo pipefail

LLAMA=${1:-/opt/p100-llama-cpp/llama.cpp}
MODEL=${2:-/opt/models/phase4/Qwen3.8-27B-UD-IQ4_XS.gguf}
shift 2 || true

export CUDA_DEVICE_ORDER=PCI_BUS_ID
export CUDA_VISIBLE_DEVICES=1,2
export GOMP_CPU_AFFINITY=0,1,2,3
export GGML_CUDA_GRAPHS_PRE_VOLTA=3
export LLAMA_SPEC_SAMPLE_TEMP=1.0
export LLAMA_SPEC_DRAFT_TOPK=20

exec "$LLAMA/build/bin/llama-server" \
  --model "$MODEL" \
  --alias mae-engineering-tutor \
  --fit off \
  --host 0.0.0.0 --port 8002 \
  -sm tensor \
  -ngl 999 \
  -fa on \
  -c 215040 \
  -ctk q8_0 -ctv q8_0 \
  -b 32768 -ub 1024 -np 1 \
  --spec-type draft-mtp --spec-draft-n-max 3 --spec-draft-p-min 0.12 \
  -ngld 999 -ctkd q8_0 -ctvd q8_0 \
  --jinja --temp 1.0 --top-k 20 --top-p 0.95 --min-p 0.0 \
  --slots --slot-save-path /var/cache/llama-kv \
  --threads 4 --threads-batch 4 \
  --no-mmap \
  --cont-batching --no-warmup "$@"

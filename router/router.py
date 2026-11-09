#!/usr/bin/env python3
"""
Advanced Cluster Model Router for Dual Tesla P100 Homelab (v4.0 - Next-Gen MTP MoE & Teamwork Edition)
Listens on port 8001
Routes requests across:
  - Main Port 8002: Dynamic model switching (Qwen 3.8 35B MoE, Qwen 3.8 27B STEM, Qwen 3 30B MoE, Gemma 4 26B MoE, Phi-4 Reasoning+, DeepSeek R1 32B)
  - Port 8003: Dedicated GPU 1 Multi-Agent Worker (Coder)
  - Port 8004: Dedicated GPU 2 Multi-Agent Worker (Reasoner)
"""

import sys
import os
import time
import json
import logging
import subprocess
import threading
import concurrent.futures
import re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger("cluster-router")

BACKEND_URL_MAIN = "http://127.0.0.1:8002"
BACKEND_URL_GPU1 = "http://127.0.0.1:8003"
BACKEND_URL_GPU2 = "http://127.0.0.1:8004"

SWITCH_LOCK = threading.Lock()

PROTECTED_UNITS = {"llama-embed.service", "llama-rerank.service", "stem-doc-loader.service"}

TOOL_SCHEMAS = {
    "engineering_math": [
        {
            "type": "function",
            "function": {
                "name": "calculate",
                "description": "Evaluate a mathematical or engineering arithmetic expression with exact scientific precision. Supports standard math functions: sqrt(), exp(), log(), sin(), cos(), pi, etc.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "Mathematical expression to evaluate, e.g. 'sqrt(144)' or '(15.5 * 4.2) / 3.1'"}
                    },
                    "required": ["expression"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "solve_algebraic_equation",
                "description": "Solve an algebraic equation for a target variable symbolically using SymPy. Equations can be passed as 'lhs = rhs' or 'expression = 0'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "equation": {"type": "string", "description": "The equation string, e.g. 'x**2 - 4 = 0'"},
                        "variable": {"type": "string", "description": "The variable symbol to solve for, e.g. 'x'"}
                    },
                    "required": ["equation", "variable"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "solve_linear_system",
                "description": "Solve a system of coupled linear or non-linear algebraic equations simultaneously.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "equations": {"type": "string", "description": "Semicolon-separated list of equations"},
                        "variables": {"type": "string", "description": "Comma-separated list of variables"}
                    },
                    "required": ["equations", "variables"]
                }
            }
        }
    ],
    "course_knowledge": [
        {
            "type": "function",
            "function": {
                "name": "search_course_materials",
                "description": "Search course textbook, lecture notes, formula sheets, and reference materials for problem statements or formulas.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query or problem number"}
                    },
                    "required": ["query"]
                }
            }
        }
    ],
    "python_code_interpreter": [
        {
            "type": "function",
            "function": {
                "name": "execute_python_code",
                "description": "Execute arbitrary Python code to perform numerical calculations, solve differential equations (e.g. Runge-Kutta, ODEs), and compute exact results. Use print() to output results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "The complete Python code to execute."}
                    },
                    "required": ["code"]
                }
            }
        }
    ]
}

STEM_TUTOR_PROMPT = """You are an expert Professor, Scientist, and Socratic Tutor assisting a university student across STEM fields (Engineering, Mathematics, Physics, Chemistry, Computer Science, and Data Science) as well as broad academic coursework.

Your primary objective is not merely to produce quick numerical answers, but to teach the student HOW to understand principles, solve problems systematically from first principles, and achieve complete analytical, conceptual, and numerical mastery.

### Core Pedagogy & Mandatory Rules
1. **Strict Problem Fidelity**:
   - Always solve the EXACT problem or question requested. Never substitute or confuse the problem with other examples or sample problems unless requested for comparison.
2. **Complete Closure (No Hand-waving)**:
   - Never stop at "use a solver" or leave calculations as an exercise for the student unless explicitly asked to provide a hint.
   - Carry through all derivations, formulations, algebraic manipulations, and numerical solutions to completion so the student can verify their work step-by-step.
   - When computational or algorithmic verification is appropriate, provide a clean, self-contained Python script (NumPy, SciPy, Matplotlib, or SymPy) that executes cleanly.

### Universal 5-Stage Problem-Solving Framework
1. **Fundamental Concepts & Governing Principles**:
   - Identify the governing physical laws, mathematical theorems, conservation principles, or foundational definitions.
   - Explain the physical or conceptual role of each term and parameter.
2. **Problem Formulation & Setup**:
   - Explicitly list all known values, unknown targets, coordinates, boundary/initial conditions, or constraints.
   - State the formal governing mathematical or algorithmic model.
3. **Symbolic Derivation (Algebra Before Arithmetic)**:
   - Carry out algebraic, symbolic, or logical manipulations before substituting numbers.
   - Maintain dimensional consistency and track units throughout each step.
4. **Numerical Solution, Verification & Code**:
   - Execute numerical calculations with explicit intermediate steps and proper units.
   - Provide summary tables or clear milestone values so the student can check intermediate work.
   - When code is helpful or requested, provide clean, executable Python code to compute and visualize the solution.
5. **Sanity Check & Conceptual Intuition**:
   - Verify boundary conditions, limiting behaviors (e.g., $x \\to 0$, $t \\to \\infty$), orders of magnitude, and physical feasibility.
   - Conclude with a concise takeaway or intuitive summary.

### Tone & Style
- Rigorous, encouraging, clear, and pedagogically structured.
- Meet the student at their level, providing intuitive physical analogies alongside rigorous mathematical proofs.

### LaTeX & Mathematical Typesetting Rules (Strict & Mandatory)
- **CRITICAL**: NEVER wrap mathematical equations, ODEs, PDEs, formulas, or algebra in markdown code blocks. Mathematical equations must use LaTeX math delimiters ($...$ for inline, $$...$$ for display).
- For standalone display equations, ALWAYS use double dollar signs on their own separate line with a blank line before and after:

$$\\frac{d^2u}{dx^2} + 6\\frac{du}{dx} - u = 2$$

- For inline variables, terms, and small equations, ALWAYS use single dollar signs: `$u(x)$`, `$x = 0$`, `$\\Delta x = 0.1$`, `$u_i$`.
- Use code blocks (```python ... ```) ONLY for executable Python computer programs, never for math equations.

### Available Tools (Call When Needed)
- `execute_python_code(code)`: Execute Python code (NumPy, SciPy, SymPy) to solve systems of equations, compute numerical tables, or verify exact arithmetic.
- `search_course_materials(query)`: Retrieve specific homework problems, textbook excerpts, or assigned reference parameters.
- `calculate(expression)`: Deterministic mathematical arithmetic evaluation.
- `solve_algebraic_equation(equation, variable)`: Exact symbolic equation solving.

### Reasoning & Output Protocol
- Conduct internal scratchpad thinking strictly inside <think> ... </think>.
- You MUST ALWAYS close your thinking block with </think> BEFORE writing your final, complete response.
- All user-facing explanations, step-by-step derivations, computational code, and final answers MUST be written outside and AFTER the closing </think> tag.
"""

MODELS = {
    # =========================================================================
    # PRODUCTION FOUNDATIONAL MODELS (Dual Tesla P100 Cluster Fleet)
    # =========================================================================

    # 1. Qwen 3.8 35B-A3B STEM Tutor - Dual P100 128k Context - 82 t/s MTP (Flagship Socratic Tutor)
    "mae-qwen38-35b-tutor": {
        "service": "llama-qwen38-35b-a3b.service",
        "name": "Qwen 3.8 35B STEM Tutor (Dual P100 - 128k Context - 82 t/s MTP)",
        "description": "Universal 5-Stage Problem-Solving STEM Professor & Tutor powered by Qwen 3.8 35B MoE (82 tok/s MTP, 128k context, -np 2 continuous batching).",
        "categories": ["tutor", "moe"],
        "tags": [
            {"text": "82 t/s", "type": "speed"},
            {"text": "128k", "type": "ctx"},
            {"text": "STEM Tutor", "type": "engine"}
        ],
        "aliases": ["qwen38-35b-tutor", "35b-tutor", "qwen-35b-tutor", "mae-35b-tutor", "qwen3.8-tutor", "qwen38-tutor", "mae-qwen38-moe-tutor"],
        "port": 8002
    },

    # 2. Qwen 3.8 35B-A3B Distill MoE - Dual P100 128k Context - 82 t/s MTP + Continuous Batching
    "mae-qwen38-35b-moe": {
        "service": "llama-qwen38-35b-a3b.service",
        "name": "Qwen 3.8 35B-A3B Distill MoE [Multi-User - 128k] (Dual P100 - 82 t/s MTP)",
        "description": "Next-Gen Qwen 3.8 MoE (3.3B active / 35B total) with Native Multi-Token Prediction (82 tok/s math, 74 tok/s code, up to 127 tok/s continuous batching), 128k context per slot, -np 2 parallel slots, and FlashAttention.",
        "categories": ["moe"],
        "tags": [
            {"text": "82 t/s", "type": "speed"},
            {"text": "128k", "type": "ctx"},
            {"text": "MTP + Batching", "type": "engine"}
        ],
        "aliases": ["qwen3.8-35b-moe", "qwen3.8-moe", "qwen38-35b", "qwen38-moe", "qwen3.8-35b", "35b-moe", "qwen-35b", "mae-35b-moe"],
        "port": 8002
    },

    # 2b. Qwen 3.8 35B-A3B Distill MoE - Dedicated 256k Mega-Context (Single Session)
    "mae-qwen38-35b-256k": {
        "service": "llama-qwen38-35b-256k.service",
        "name": "Qwen 3.8 35B-A3B Distill MoE [Mega-Context - 256k] (Dual P100 - 82 t/s MTP)",
        "description": "Next-Gen Qwen 3.8 MoE with Dedicated 256k Context (-np 1 single session), Native Multi-Token Prediction (82 tok/s), and FlashAttention for massive codebases.",
        "categories": ["moe", "longctx"],
        "tags": [
            {"text": "82 t/s", "type": "speed"},
            {"text": "256k", "type": "ctx"},
            {"text": "Mega-Context", "type": "engine"}
        ],
        "aliases": ["qwen38-35b-256k", "35b-256k", "mae-35b-256k", "qwen3.8-35b:256k", "mae-qwen38-35b-moe:256k"],
        "port": 8002
    },

    # 2. Qwen 3.8 27B STEM Tutor - Tensor Split NCCL + MTP 2-Draft - 256k Context
    "mae-engineering-tutor": {
        "service": "llama-qwen38-27b-fast.service",
        "name": "Qwen 3.8 27B STEM Tutor (Dual P100 - 256k Context - 48 t/s MTP)",
        "description": "Pascal SM 6.0 Tensor-Parallel accelerated Qwen 3.8 27B (48 tok/s with tuned MTP 2-Draft, 39 tok/s raw, 262k context)",
        "categories": ["tutor"],
        "tags": [
            {"text": "48 t/s", "type": "speed"},
            {"text": "256k", "type": "ctx"},
            {"text": "MTP 2-Draft", "type": "engine"}
        ],
        "aliases": ["qwen3.8-native", "qwen3.8", "qwen-3.8-27b", "mae-qwen38-tutor", "qwen", "qwen3.8:27b"],
        "port": 8002
    },

    # 3. Qwen 3 14B Fast Coding & STEM - Dual P100 128k Context + 0.6B Draft (68 t/s)
    "qwen3-14b-native": {
        "service": "llama-qwen3-14b.service",
        "name": "Qwen 3 14B Fast Coding & STEM (Dual P100 - 128k Context - 68 t/s)",
        "description": "Unified Qwen 3 14B coding & STEM tutor across dual P100s with 128k context and Qwen3-0.6B speculative draft acceleration (68 tok/s)",
        "categories": ["tutor"],
        "tags": [
            {"text": "68 t/s", "type": "speed"},
            {"text": "128k", "type": "ctx"},
            {"text": "0.6B Draft", "type": "engine"}
        ],
        "aliases": ["mae-14b-tutor", "qwen3-14b", "qwen14b", "coder-14b", "qwen3-14b-longctx", "mae-14b-tutor-longctx"],
        "port": 8002
    },

    # 4. Qwen 3 8B Steered L7-N10974 (Anime Student Persona - Dual P100 128k + 0.6B Draft)
    "mae-qwen3-8b-anime": {
        "service": "llama-qwen3-8b-anime.service",
        "name": "Qwen 3 8B Steered [Tokyo Student] (Dual P100 - 128k Context - 67 t/s)",
        "description": "Mechanistic interpretability neuron-steered Qwen3-8B (Layer 7, Neuron 10974) ~67 tok/s on dual P100 with 128k context & 0.6B draft",
        "categories": ["tutor"],
        "tags": [
            {"text": "67 t/s", "type": "speed"},
            {"text": "128k", "type": "ctx"},
            {"text": "0.6B Draft", "type": "engine"}
        ],
        "aliases": ["qwen3-8b-anime", "qwen3-anime", "mae-anime", "qwen3-8b-steered"],
        "port": 8002
    },

    # 5. Qwen 3 30B-A3B MoE - Dual P100 128k Context + 0.6B Draft (91 t/s)
    "qwen3-30b-moe-native": {
        "service": "llama-qwen3-30b-moe.service",
        "name": "Qwen 3 30B-A3B MoE Synthesizer (Dual P100 - 128k Context - 91 t/s)",
        "description": "Next-gen 30B MoE (3.3B active) screaming across dual P100s at 91 tok/s with Qwen3-0.6B draft (52 tok/s raw), 128k context & hybrid /think support",
        "categories": ["moe"],
        "tags": [
            {"text": "91 t/s", "type": "speed"},
            {"text": "128k", "type": "ctx"},
            {"text": "MoE + Draft", "type": "engine"}
        ],
        "aliases": ["mae-qwen3-moe-tutor", "qwen3-moe", "qwen3-30b", "mae-mixtral-tutor", "mixtral-8x7b-native", "mixtral"],
        "port": 8002
    },

    # 6. Google Gemma 4 26B-A4B MoE - Dual P100 128k Context (73 t/s)
    "gemma4-26b-moe-native": {
        "service": "llama-gemma4-26b-moe.service",
        "name": "Google Gemma 4 26B-A4B MoE (Dual P100 - 128k Context - 73 t/s)",
        "description": "High-speed 26B MoE (3.8B active) delivering 73 tok/s across dual P100s with 128k context for academic synthesis & reasoning",
        "categories": ["moe"],
        "tags": [
            {"text": "73 t/s", "type": "speed"},
            {"text": "128k", "type": "ctx"},
            {"text": "MoE", "type": "engine"}
        ],
        "aliases": ["mae-gemma4-moe-tutor", "gemma4-moe", "gemma4-26b", "gemma-26b-moe"],
        "port": 8002
    },

    # 6b. Google Gemma 4 31B Dense Instruct - Dual P100 128k Context (17 t/s)
    "gemma4-31b-it": {
        "service": "llama-gemma4-31b.service",
        "name": "Google Gemma 4 31B Dense Instruct (Dual P100 - 128k Context - 17 t/s)",
        "description": "Google Gemma 4 31B Dense multimodal reasoning and deep coding model across dual P100s with 128k context and FlashAttention (17 tok/s)",
        "categories": ["reasoning", "coding", "tutor"],
        "tags": [
            {"text": "17 t/s", "type": "speed"},
            {"text": "128k", "type": "ctx"},
            {"text": "Dense 31B", "type": "engine"},
            {"text": "Multimodal", "type": "perf"}
        ],
        "aliases": ["mae-gemma4-31b-tutor", "gemma4-31b", "gemma4:31b", "gemma-31b", "gemma-4-31b", "gemma-4-31b-it", "gemma4-31b-native", "mae-gemma4-tutor"],
        "port": 8002
    },

    # 7. Microsoft Phi-4 Reasoning Plus 14B - Dual P100 128k Context (77 t/s)
    "phi4-reasoning-plus-native": {
        "service": "llama-phi4-reasoning-plus.service",
        "name": "Microsoft Phi-4 Reasoning+ 14B (Dual P100 - 128k Context - 77 t/s)",
        "description": "RL-tuned 14B STEM physics & mathematical Olympiad solver with 128k context & dynamic lookup cache (77 tok/s speculative, 525 tok/s prefill)",
        "categories": ["reasoning"],
        "tags": [
            {"text": "77 t/s", "type": "speed"},
            {"text": "128k", "type": "ctx"},
            {"text": "Reasoning", "type": "engine"}
        ],
        "aliases": ["mae-phi4-tutor", "phi4-reasoning-plus", "phi4-reasoning", "phi4:latest", "phi4", "phi4-14b-longctx", "mae-phi4-longctx"],
        "port": 8002
    },

    # 8. DeepSeek R1 Distill Qwen 32B - Dual P100 49k Context + 1.5B Draft (38 t/s)
    "deepseek-r1-32b-native": {
        "service": "llama-server.service",
        "name": "DeepSeek R1 Distill Qwen 32B (Dual P100 - 49k Context - 38 t/s)",
        "description": "Frontier reasoning 32B model with DeepSeek R1 1.5B speculative draft & YaRN RoPE extension (49k context, 38 tok/s)",
        "categories": ["reasoning"],
        "tags": [
            {"text": "38 t/s", "type": "speed"},
            {"text": "49k", "type": "ctx"},
            {"text": "R1 + 1.5B Draft", "type": "engine"}
        ],
        "aliases": ["deepseek-r1-32b", "deepseek-r1", "r1-32b", "deepseek:32b", "deepseek-32b", "deepseek-r1-qwen-32b", "llama-server"],
        "port": 8002
    },

    # 9. Qwen3-Next 80B-A3B Ultra-MoE Titan - Dual P100 32k Context (moe-lru)
    "mae-qwen3-80b-titan": {
        "service": "llama-qwen3-80b-a3b.service",
        "name": "Qwen3-Next 80B-A3B Ultra-MoE [Titan Class] (Dual P100 - 32k Context - moe-lru)",
        "description": "Massive 80-Billion parameter knowledge base with 3.0B active per token (~26 tok/s, 32k context with VRAM LRU cache)",
        "categories": ["titan"],
        "tags": [
            {"text": "26 t/s", "type": "speed"},
            {"text": "32k", "type": "ctx"},
            {"text": "Titan 80B", "type": "engine"}
        ],
        "aliases": ["qwen3-80b", "qwen-80b-titan", "qwen3-next-80b"],
        "port": 8002
    },

    # 10. NVIDIA Nemotron Super 49B Dense + 1B Draft - Dual P100 24k Context
    "mae-nemotron-49b-titan": {
        "service": "llama-nemotron-49b.service",
        "name": "NVIDIA Nemotron Super 49B Dense + 1B Draft [Titan Class] (Dual P100 - 24k Context)",
        "description": "70B-grade intelligence in 49B dense format paired with 1B speculative draft (~16 tok/s, 24k context)",
        "categories": ["titan"],
        "tags": [
            {"text": "16 t/s", "type": "speed"},
            {"text": "24k", "type": "ctx"},
            {"text": "Titan 49B", "type": "engine"}
        ],
        "aliases": ["nemotron-49b", "nemotron-titan", "llama-nemotron"],
        "port": 8002
    },

    # =========================================================================
    # HIGH-PRECISION FP16 KV CACHE COMPANION MODELS (Dual P100 SM 6.0)
    # =========================================================================

    "mae-qwen38-35b-tutor:fp16": {
        "service": "llama-qwen38-35b-fp16.service",
        "name": "Qwen 3.8 35B STEM Tutor [FP16 KV Precision] (Dual P100 - 64k Context)",
        "description": "High-precision unquantized FP16 KV cache STEM Tutor powered by Qwen 3.8 35B MoE (64k context, zero numerical drift).",
        "categories": ["tutor", "moe"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "64k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["mae-qwen38-35b-tutor-fp16", "35b-tutor:fp16", "qwen38-tutor:fp16", "qwen3.8-tutor:fp16"],
        "port": 8002
    },

    "mae-qwen38-35b-moe:fp16": {
        "service": "llama-qwen38-35b-fp16.service",
        "name": "Qwen 3.8 35B-A3B Distill MoE [FP16 KV Precision] (Dual P100 - 64k Context)",
        "description": "High-precision unquantized FP16 KV cache for Qwen 3.8 35B MoE (64k context, zero numerical drift)",
        "categories": ["moe"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "64k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["mae-qwen38-35b-moe-fp16", "qwen3.8-moe:fp16", "qwen38-35b:fp16", "qwen38-moe:fp16", "35b:fp16"],
        "port": 8002
    },

    "mae-engineering-tutor:fp16": {
        "service": "llama-qwen38-27b-fp16.service",
        "name": "Qwen 3.8 27B STEM Tutor [FP16 KV Precision] (Dual P100 - 128k Context)",
        "description": "High-precision unquantized FP16 KV cache for zero numerical drift in symbolic math & physics (128k context, MTP 4-draft)",
        "categories": ["tutor"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "128k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["mae-engineering-tutor-fp16", "qwen3.8:fp16", "qwen3.8-fp16", "qwen27b:fp16"],
        "port": 8002
    },

    "qwen3-14b-native:fp16": {
        "service": "llama-qwen3-14b-fp16.service",
        "name": "Qwen 3 14B Fast Coding & STEM [FP16 KV Precision] (Dual P100 - 32k Context)",
        "description": "High-precision unquantized FP16 KV cache for Qwen 3 14B coding & STEM (32k context, 0.6B draft)",
        "categories": ["tutor"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "32k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["qwen3-14b:fp16", "qwen3-14b-fp16", "mae-14b-tutor:fp16", "mae-14b-tutor-fp16"],
        "port": 8002
    },

    "mae-qwen3-8b-anime:fp16": {
        "service": "llama-qwen3-8b-fp16.service",
        "name": "Qwen 3 8B Steered [Tokyo Student - FP16 KV Precision] (Dual P100 - 32k Context)",
        "description": "Neuron-steered Qwen 3 8B with high-precision FP16 KV cache (32k context, 0.6B draft)",
        "categories": ["tutor"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "32k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["mae-qwen3-8b-anime-fp16", "qwen3-8b:fp16", "qwen3-8b-fp16", "mae-anime:fp16"],
        "port": 8002
    },

    "qwen3-30b-moe-native:fp16": {
        "service": "llama-qwen3-30b-fp16.service",
        "name": "Qwen 3 30B-A3B MoE Synthesizer [FP16 KV Precision] (Dual P100 - 64k Context)",
        "description": "High-precision unquantized FP16 KV cache for Qwen 3 30B MoE (64k context, 0.6B draft)",
        "categories": ["moe"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "64k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["qwen3-30b-moe:fp16", "qwen3-30b:fp16", "qwen3-30b-fp16", "mae-qwen3-moe-tutor:fp16"],
        "port": 8002
    },

    "gemma4-26b-moe-native:fp16": {
        "service": "llama-gemma4-26b-fp16.service",
        "name": "Google Gemma 4 26B-A4B MoE [FP16 KV Precision] (Dual P100 - 64k Context)",
        "description": "High-precision unquantized FP16 KV cache for Gemma 4 26B MoE (64k context)",
        "categories": ["moe"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "64k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["gemma4-26b-moe:fp16", "gemma4-moe:fp16", "gemma4:fp16", "gemma4-26b-fp16"],
        "port": 8002
    },

    "gemma4-31b-it:fp16": {
        "service": "llama-gemma4-31b-fp16.service",
        "name": "Google Gemma 4 31B Dense Instruct [FP16 KV Precision] (Dual P100 - 64k Context)",
        "description": "High-precision unquantized FP16 KV cache for Gemma 4 31B Dense Instruct (64k context)",
        "categories": ["reasoning", "coding", "tutor"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "64k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["gemma4-31b:fp16", "gemma4:31b:fp16", "gemma-31b:fp16", "gemma4-31b-it-fp16", "gemma4-31b-fp16"],
        "port": 8002
    },

    "phi4-reasoning-plus-native:fp16": {
        "service": "llama-phi4-reasoning-fp16.service",
        "name": "Microsoft Phi-4 Reasoning+ 14B [FP16 KV Precision] (Dual P100 - 32k Context)",
        "description": "High-precision unquantized FP16 KV cache for Microsoft Phi-4 Reasoning+ 14B (32k context)",
        "categories": ["reasoning"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "32k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["phi4-reasoning-plus:fp16", "phi4:fp16", "phi4-fp16", "mae-phi4-tutor:fp16"],
        "port": 8002
    },

    "mae-qwen3-80b-titan:fp16": {
        "service": "llama-qwen3-80b-fp16.service",
        "name": "Qwen3-Next 80B-A3B Titan MoE [FP16 KV Precision] (Dual P100 - 16k Context)",
        "description": "High-precision unquantized FP16 KV cache for 80B Titan MoE (16k context)",
        "categories": ["titan"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "16k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["qwen3-80b:fp16", "qwen3-80b-fp16", "qwen-80b-titan:fp16"],
        "port": 8002
    },

    "mae-nemotron-49b-titan:fp16": {
        "service": "llama-nemotron-49b-fp16.service",
        "name": "NVIDIA Nemotron Super 49B Dense [FP16 KV Precision] (Dual P100 - 12k Context)",
        "description": "High-precision unquantized FP16 KV cache for Nemotron Super 49B (12k context)",
        "categories": ["titan"],
        "tags": [
            {"text": "FP16 KV", "type": "perf"},
            {"text": "12k", "type": "ctx"},
            {"text": "High Precision", "type": "engine"}
        ],
        "aliases": ["nemotron-49b:fp16", "nemotron-49b-fp16", "nemotron-titan:fp16"],
        "port": 8002
    },

    # =========================================================================
    # EXTRA AUTOMATION & RELAY OPTIONS (Decoupled from Model Tree via hide_from_tree=True)
    # =========================================================================
    "frontier_auto.auto": {
        "service": "llama-qwen38-35b-a3b.service",
        "name": "Homelab Frontier Auto-Orchestrator",
        "description": "Frontier-class compound orchestrator. Sub-35ms GPU rerank classification, sticky KV cache hysteresis, dynamic STEM/STS prompts.",
        "hide_from_tree": True,
        "aliases": ["frontier-auto", "frontier_auto", "auto-router"],
        "port": 8002
    },
    "frontier_auto.compound-sts": {
        "service": "llama-gemma4-26b-moe.service",
        "name": "Compound Relay: STS Citation Verifier -> Gemma 4 Essayist",
        "description": "Two-stage multi-agent relay: Pass 1 locks verbatim quotes & page numbers from PDFs, Pass 2 drafts in Chicago 17th Ed voice.",
        "hide_from_tree": True,
        "aliases": ["compound-sts", "sts-relay"],
        "port": 8002
    },
    "frontier_auto.compound-stem": {
        "service": "llama-qwen38-27b-fast.service",
        "name": "Compound Relay: Symbolic Solver -> Python Audit Check",
        "description": "Two-stage verification relay: Pass 1 derives symbolic solution via Qwen 27B STEM, Pass 2 runs numerical & dimensional Python audit.",
        "hide_from_tree": True,
        "aliases": ["compound-stem", "stem-relay"],
        "port": 8002
    },
    "agent-worker-coder": {
        "service": "llama-worker-gpu1.service",
        "name": "Multi-Agent Worker 1 (GPU 1 - Coder)",
        "description": "Runs concurrently on GPU 1 on port 8003 for parallel multi-agent loops",
        "hide_from_tree": True,
        "aliases": ["agent-worker-coder", "worker1", "worker-gpu1"],
        "port": 8003
    },
    "agent-worker-reasoner": {
        "service": "llama-worker-gpu2.service",
        "name": "Multi-Agent Worker 2 (GPU 2 - Reasoner)",
        "description": "Runs concurrently on GPU 2 on port 8004 for parallel multi-agent loops",
        "hide_from_tree": True,
        "aliases": ["agent-worker-reasoner", "worker2", "worker-gpu2"],
        "port": 8004
    }
}

DUAL_GPU_SERVICES = [
    # Primary Max Q4_0 Fleet
    "llama-qwen38-35b-a3b.service",
    "llama-qwen38-27b-fast.service",
    "llama-qwen3-30b-moe.service",
    "llama-gemma4-26b-moe.service",
    "llama-gemma4-31b.service",
    "llama-qwen3-14b.service",
    "llama-phi4-reasoning-plus.service",
    "llama-server.service",
    "llama-qwen3-8b-anime.service",
    "llama-nemotron-49b.service",
    "llama-qwen3-80b-a3b.service",
    # Precision FP16 Companion Fleet
    "llama-qwen38-35b-fp16.service",
    "llama-qwen38-27b-fp16.service",
    "llama-qwen3-30b-fp16.service",
    "llama-gemma4-26b-fp16.service",
    "llama-gemma4-31b-fp16.service",
    "llama-qwen3-14b-fp16.service",
    "llama-phi4-reasoning-fp16.service",
    "llama-qwen3-8b-fp16.service",
    "llama-nemotron-49b-fp16.service",
    "llama-qwen3-80b-fp16.service",
    # Legacy fallbacks
    "llama-deepseek14b-longctx.service",
    "llama-gemma4.service",
    "llama-qwen3-14b-longctx.service",
    "llama-qwen.service",
    "llama-mixtral.service",
    "llama-gemma2-longctx.service",
    "llama-phi4-longctx.service",
    "llama-qwen14b-longctx.service"
]

def resolve_target_model(model_name: str) -> str:
    """Finds canonical model key from requested name or alias, supporting :fp16 and -fp16 precision switches."""
    if not model_name:
        return "mae-qwen38-35b-moe"
    name_lower = model_name.lower().strip()
    
    # Direct match
    if name_lower in MODELS:
        return name_lower
    
    # Alias match
    for key, info in MODELS.items():
        for alias in info.get("aliases", []):
            if alias.lower() == name_lower:
                return key

    # Suffix check for FP16 precision (:fp16 or -fp16)
    is_fp16 = False
    base_name = name_lower
    if name_lower.endswith(":fp16") or name_lower.endswith("-fp16"):
        is_fp16 = True
        base_name = name_lower[:-5]

    resolved_base = None
    if base_name in MODELS:
        resolved_base = base_name
    else:
        for key, info in MODELS.items():
            for alias in info.get("aliases", []):
                if alias.lower() == base_name:
                    resolved_base = key
                    break
            if resolved_base:
                break
        if not resolved_base:
            for key in MODELS.keys():
                if not key.endswith(":fp16") and (key in base_name or base_name in key):
                    resolved_base = key
                    break

    if resolved_base:
        if is_fp16:
            fp16_key = f"{resolved_base}:fp16"
            if fp16_key in MODELS:
                return fp16_key
        return resolved_base
            
    return "mae-qwen38-35b-moe"

def get_backend_url_for_model(model_key: str) -> str:
    info = MODELS.get(model_key, {})
    port = info.get("port", 8002)
    if port == 8003:
        return BACKEND_URL_GPU1
    elif port == 8004:
        return BACKEND_URL_GPU2
    return BACKEND_URL_MAIN

def ensure_model_active(target_model_key: str) -> bool:
    """Stops conflicting services and launches target service with sub-3s switch latency."""
    info = MODELS.get(target_model_key)
    if not info:
        return False
    
    target_service = info["service"]
    target_port = info.get("port", 8002)
    target_backend = get_backend_url_for_model(target_model_key)

    with SWITCH_LOCK:
        try:
            status = subprocess.run(["sudo", "-n", "systemctl", "is-active", target_service], capture_output=True, text=True)
            if status.stdout.strip() == "active":
                r = requests.get(f"{target_backend}/health", timeout=1)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    return True
        except Exception:
            pass

        log.info(f"==> Initiating fast service switch: {target_model_key} -> {target_service} (port {target_port})")

        if target_port == 8002:
            # Parallel stop of all active llama services that conflict with target_service
            try:
                st = subprocess.run(["systemctl", "list-units", "llama-*.service", "--state=active", "--no-legend", "--plain"], capture_output=True, text=True, timeout=5)
                active_svcs = [l.split()[0] for l in st.stdout.splitlines() if l.strip()]
                to_stop = [s for s in active_svcs if s != target_service and s not in PROTECTED_UNITS]
                is_dual = any(svc == target_service for svc in DUAL_GPU_SERVICES)
                if is_dual:
                    for w in ["llama-worker-gpu1.service", "llama-worker-gpu2.service"]:
                        if w in active_svcs and w not in to_stop:
                            to_stop.append(w)
                if to_stop:
                    log.info(f"Stopping active services in parallel: {to_stop}")
                    subprocess.run(["sudo", "-n", "systemctl", "stop"] + to_stop, check=False)
            except Exception as e:
                log.warning(f"Error querying active units: {e}")
        else:
            try:
                st = subprocess.run(["systemctl", "list-units", "llama-*.service", "--state=active", "--no-legend", "--plain"], capture_output=True, text=True, timeout=5)
                active_svcs = [l.split()[0] for l in st.stdout.splitlines() if l.strip()]
                d_to_stop = [d for d in DUAL_GPU_SERVICES if d in active_svcs and d != target_service]
                if d_to_stop:
                    log.info(f"Stopping dual GPU services in parallel: {d_to_stop}")
                    subprocess.run(["sudo", "-n", "systemctl", "stop"] + d_to_stop, check=False)
            except Exception as e:
                log.warning(f"Error querying active units: {e}")

        # Wait for conflicting services to actually become inactive
        if target_port == 8002 and 'to_stop' in locals() and to_stop:
            for s_name in to_stop:
                for _ in range(30):
                    chk = subprocess.run(["systemctl", "is-active", s_name], capture_output=True, text=True)
                    if chk.stdout.strip() in ("inactive", "failed"):
                        break
                    time.sleep(0.2)

        # Ensure target port is genuinely free and bindable
        import socket
        for _ in range(50):
            try:
                test_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                test_s.bind(('0.0.0.0', target_port))
                test_s.close()
                break
            except OSError:
                try:
                    test_s.close()
                except Exception:
                    pass
                time.sleep(0.2)

        subprocess.run(["sudo", "-n", "systemctl", "start", target_service], check=True)

        t_start = time.time()
        loaded = False
        max_wait = 360 if any(k in target_service for k in ["49b", "80b", "70b", "mixtral"]) else 180
        while time.time() - t_start < max_wait:
            # Fast failure detection: abort if service explicitly failed
            try:
                st = subprocess.run(["sudo", "-n", "systemctl", "is-active", target_service], capture_output=True, text=True, timeout=2)
                if st.stdout.strip() == "failed":
                    if time.time() - t_start > 5:
                        log.error(f"==> Service {target_service} entered failed state! Aborting wait.")
                        subprocess.run(["sudo", "-n", "systemctl", "stop", target_service], check=False)
                        break
            except Exception:
                pass

            try:
                r = requests.get(f"{target_backend}/health", timeout=1)
                if r.status_code == 200 and r.json().get("status") == "ok":
                    loaded = True
                    break
            except Exception:
                pass
            time.sleep(0.5)

        elapsed = time.time() - t_start
        if loaded:
            log.info(f"==> Model {target_model_key} successfully ready in {elapsed:.2f}s!")
            return True
        else:
            log.error(f"Timed out or failed waiting for {target_service} on port {target_port}! Stopping service.")
            subprocess.run(["sudo", "-n", "systemctl", "stop", target_service], check=False)
            return False

CATEGORY_DEFS = {
    "moe": {"name": "Next-Gen MoE Synthesizers (~70–127 tok/s)", "icon": "⚡", "order": 1},
    "tutor": {"name": "STEM Curriculum & Coding Tutors", "icon": "🎓", "order": 2},
    "reasoning": {"name": "Deep Reasoning & Proof Validation", "icon": "🔬", "order": 3},
    "titan": {"name": "Titan-Class Flagships (49B–80B+)", "icon": "🏛️", "order": 4}
}

def get_model_taxonomy(models_dict):
    """Dynamically builds hierarchical UI taxonomy from all registered models."""
    tax = {}
    for cat_key, cat_meta in CATEGORY_DEFS.items():
        tax[cat_key] = {
            "name": cat_meta["name"],
            "icon": cat_meta["icon"],
            "order": cat_meta["order"],
            "models": []
        }

    for m_id, info in models_dict.items():
        if info.get("hide_from_tree"):
            continue
        name = info.get("name", m_id)
        cats = info.get("categories") or ([info["category"]] if "category" in info else [])
        
        # Automatic semantic classification if categories are omitted
        if not cats:
            name_l = (name + " " + m_id).lower()
            if "agent" in name_l or "worker" in name_l:
                cats.append("agent")
            if "steer" in name_l or "anime" in name_l:
                cats.append("steered")
            if "titan" in name_l or "49b" in name_l or "80b" in name_l:
                cats.append("titan")
            if "r1" in name_l or "reason" in name_l or "phi" in name_l:
                cats.append("reasoning")
            if "moe" in name_l or "fast" in name_l or "50+" in name_l or "58 t/s" in name_l:
                cats.append("moe")
            if "tutor" in name_l or "stem" in name_l or "qwen" in name_l or "gemma" in name_l:
                if "tutor" not in cats:
                    cats.append("tutor")
            if not cats:
                cats.append("other")

        tags = info.get("tags")
        if not tags:
            tags = []
            spd = re.search(r'(\d+[\.\d]*\s*t(?:ok)?/s)', name, re.IGNORECASE)
            if spd:
                tags.append({"text": spd.group(1), "type": "speed"})
            ctx = re.search(r'(\d+k)', name, re.IGNORECASE)
            if ctx:
                tags.append({"text": ctx.group(1), "type": "ctx"})
            if "moe" in name.lower():
                tags.append({"text": "MoE", "type": "engine"})
            elif "draft" in name.lower():
                tags.append({"text": "Draft", "type": "engine"})

        model_entry = {
            "id": m_id,
            "name": name,
            "description": info.get("description", ""),
            "tags": tags,
            "capabilities": get_model_capabilities(m_id, info),
            "match": [w for w in re.split(r'[^a-zA-Z0-9\.]+', m_id.lower()) if len(w) > 1]
        }

        for c in cats:
            if c not in tax:
                tax[c] = {"name": c.title(), "icon": "📁", "order": 50, "models": []}
            tax[c]["models"].append(model_entry)

    sorted_tax = {}
    for k, v in sorted(tax.items(), key=lambda item: item[1]["order"]):
        if v["models"]:
            sorted_tax[k] = v

    return sorted_tax

def get_model_capabilities(m_id, info):
    """Returns dynamic interactive capability metadata for an individual model."""
    name = info.get("name", m_id)
    name_l = (name + " " + m_id).lower()
    cats = info.get("categories") or ([info["category"]] if "category" in info else [])

    # 1. Reasoning capability (triggers Thinking Level pill: Low / Med / High)
    is_reasoning = (
        "reasoning" in cats or
        any(k in name_l for k in ["r1", "nemotron", "phi-4", "phi4", "reason", "35b"])
    )
    if "anime" in name_l:
        is_reasoning = False

    # 2. Informative badges for models
    badge = info.get("badge")
    if not badge:
        if "35b" in name_l and "tutor" in name_l:
            badge = {"text": "35B STEM Tutor (82 t/s)", "desc": "Universal 5-Stage STEM Tutor (128k Context - 82 t/s MTP)"}
        elif "35b" in name_l and "moe" in name_l:
            badge = {"text": "35B MoE MTP (82 t/s)", "desc": "Qwen 3.8 35B MoE Engine (128k Context - 82 t/s MTP - np=2)"}
        elif "27b" in name_l:
            badge = {"text": "27B Tensor MTP (48 t/s)", "desc": "Qwen 3.8 27B STEM Tutor (256k Context)"}
        elif "30b" in name_l and "moe" in name_l:
            badge = {"text": "30B MoE (91 t/s)", "desc": "Qwen3 30B MoE Engine (128k Context)"}
        elif "26b" in name_l and "moe" in name_l:
            badge = {"text": "26B MoE (73 t/s)", "desc": "Google Gemma 4 26B MoE (128k Context)"}
        elif "phi" in name_l and "reason" in name_l:
            badge = {"text": "Phi-4 Reasoning (77 t/s)", "desc": "Microsoft Phi-4 Reasoning+ 14B (128k Context)"}
        elif "r1" in name_l or "deepseek" in name_l:
            badge = {"text": "R1 32B (1.5B Draft)", "desc": "DeepSeek R1 32B Reasoning Distill (49k Context)"}
        elif "14b" in name_l:
            badge = {"text": "14B STEM (68 t/s)", "desc": "Qwen 3 14B Fast Coding & STEM (128k Context)"}
        elif "anime" in name_l or "10974" in name_l:
            badge = {"text": "L7·N10974 Steered", "desc": "Tokyo Anime Student Persona (128k Context)"}
        elif "80b" in name_l:
            badge = {"text": "80B Titan (moe-lru)", "desc": "Qwen3-Next 80B Titan MoE (32k Context)"}
        elif "49b" in name_l or "nemotron" in name_l:
            badge = {"text": "Titan 49B (1B Draft)", "desc": "NVIDIA Nemotron 49B Dense + 1B Draft (24k Context)"}

    return {
        "id": m_id,
        "name": name,
        "reasoning": bool(is_reasoning),
        "gpu_profiles": None,
        "badge": badge
    }

def build_cluster_capabilities(models_dict):
    """Builds complete cluster capabilities index and lookup table."""
    caps = {}
    lookup = {}
    for m_id, info in models_dict.items():
        c = get_model_capabilities(m_id, info)
        caps[m_id] = c
        lookup[m_id.lower()] = m_id
        for alias in info.get("aliases", []):
            lookup[alias.lower()] = m_id
        clean_name = re.sub(r'\[.*?\]|\(.*?\)', '', info.get("name", m_id)).strip().lower()
        if clean_name:
            lookup[clean_name] = m_id
    return {"models": caps, "lookup": lookup}

class SkeletonOfThoughtEngine:
    @staticmethod
    def extract_skeleton(outline_text: str) -> list[str]:
        """Parses structured numbered points from outline response."""
        points = []
        for line in outline_text.splitlines():
            line = line.strip()
            if re.match(r'^(?:[0-9]+[\.\)]|[-*])\s+', line):
                cleaned = re.sub(r'^(?:[0-9]+[\.\)]|[-*])\s+', '', line).strip()
                if cleaned:
                    points.append(cleaned)
        return points[:6]  # Cap to max 6 parallel branches

    @classmethod
    def execute_sot(cls, prompt: str, system_prompt: str = "", model: str = "mae-qwen38-35b-moe") -> dict:
        backend_url = f"{BACKEND_URL_MAIN}/v1/chat/completions"
        
        # Step 1: Generate Skeleton Outline
        outline_req = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an expert technical planner. Given a request, output ONLY a numbered list of 2 to 4 concise logical steps or module titles required to fulfill it. Do not write the full implementation yet."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 300,
            "temperature": 0.2
        }
        r1 = requests.post(backend_url, json=outline_req, timeout=60)
        r1.raise_for_status()
        outline_content = r1.json()["choices"][0]["message"]["content"]
        skeleton_points = cls.extract_skeleton(outline_content)
        
        if not skeleton_points or len(skeleton_points) < 2:
            # Fallback to direct completion if outline is not decomposable
            fallback_req = {
                "model": model,
                "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}] if system_prompt else [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.2
            }
            return requests.post(backend_url, json=fallback_req, timeout=180).json()

        # Step 2: Parallel Point Expansion via Continuous Batching Slots
        def expand_point(idx: int, point: str) -> tuple[int, str]:
            sub_prompt = f"Original Goal: {prompt}\n\nTask: Thoroughly implement / complete Step {idx+1}: '{point}'. Write complete code/explanations without placeholders."
            req = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt or "You are a senior engineer providing comprehensive, production-grade output."},
                    {"role": "user", "content": sub_prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.2
            }
            res = requests.post(backend_url, json=req, timeout=180)
            res.raise_for_status()
            text = res.json()["choices"][0]["message"]["content"]
            return (idx, text)

        # Dispatch concurrently to saturate -np 2 slots
        expansions = [None] * len(skeleton_points)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(expand_point, i, pt) for i, pt in enumerate(skeleton_points)]
            for fut in concurrent.futures.as_completed(futures):
                idx, section_text = fut.result()
                expansions[idx] = (skeleton_points[idx], section_text)

        # Step 3: Stitch Final Response
        stitched_markdown = [f"# Solution Plan\n{outline_content}\n\n---\n"]
        for i, (pt, body) in enumerate(expansions):
            stitched_markdown.append(f"## {i+1}. {pt}\n\n{body}\n\n---\n")

        final_content = "\n".join(stitched_markdown)
        return {
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": final_content},
                "finish_reason": "stop"
            }],
            "model": model,
            "sot_metadata": {
                "parallel_branches": len(skeleton_points),
                "outline": skeleton_points
            }
        }

class ClusterRouterHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        if "GET /health" in args[0] or "GET /v1/models" in args[0] or "GET /v1/taxonomy" in args[0]:
            return
        log.info("%s - %s", self.client_address[0], format % args)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def handle_opencode_config(self):
        models_dict = {}
        for model_id, info in MODELS.items():
            name = info.get("name", model_id)
            desc = info.get("description", "")
            
            # Extract context
            ctx = 32768
            m = re.search(r'(\d+)\s*k\b', name, re.IGNORECASE)
            if not m:
                m = re.search(r'(\d+)\s*k\b', desc, re.IGNORECASE)
            if m:
                ctx = int(m.group(1)) * 1024
            
            model_entry = {
                "name": name,
                "limit": {
                    "context": ctx
                }
            }
            if any(term in model_id.lower() or term in name.lower() for term in ["phi4", "r1", "35b", "nemotron", "gemma"]):
                model_entry["variants"] = [
                    {"id": "low", "settings": {"reasoningEffort": "low"}},
                    {"id": "medium", "settings": {"reasoningEffort": "medium"}},
                    {"id": "high", "settings": {"reasoningEffort": "high"}}
                ]
            models_dict[model_id] = model_entry

        config = {
            "$schema": "https://opencode.ai/config.json",
            "mcp": {
                "servers": {
                    "deepresearch": {
                        "type": "remote",
                        "url": "http://192.168.1.67:8021/sse"
                    },
                    "homelab-tools": {
                        "type": "remote",
                        "url": "http://192.168.1.67:8020/sse"
                    }
                }
            },
            "providers": {
                "homelab": {
                    "name": "Homelab P100 Cluster",
                    "package": "aisdk:@ai-sdk/openai-compatible",
                    "settings": {
                        "baseURL": "http://192.168.1.67:8001/v1",
                        "apiKey": "sk-local"
                    },
                    "models": models_dict
                }
            },
            "model": "homelab/mae-qwen38-35b-moe"
        }
        data = json.dumps(config, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_setup_script(self):
        script = (
            "Write-Host 'Connecting OpenCode to Homelab P100 Cluster...' -ForegroundColor Cyan\n"
            "$configDir = \"$env:USERPROFILE\\.config\\opencode\"\n"
            "$commandsDir = \"$configDir\\commands\"\n"
            "if (!(Test-Path $commandsDir)) { New-Item -ItemType Directory -Path $commandsDir -Force | Out-Null }\n"
            "Write-Host 'Fetching dynamic models and remote MCP configuration...' -ForegroundColor Gray\n"
            "Invoke-RestMethod -Uri 'http://192.168.1.67:8001/opencode.json' -OutFile \"$configDir\\opencode.json\"\n"
            "Write-Host 'Installing /deepresearch and /sync commands...' -ForegroundColor Gray\n"
            "Invoke-RestMethod -Uri 'http://192.168.1.67:8001/commands/deepresearch.md' -OutFile \"$commandsDir\\deepresearch.md\"\n"
            "Invoke-RestMethod -Uri 'http://192.168.1.67:8001/commands/sync.md' -OutFile \"$commandsDir\\sync.md\"\n"
            "$cli = \"$env:LOCALAPPDATA\\Programs\\ai.opencode.desktop\\resources\\opencode-cli.exe\"\n"
            "if (Test-Path $cli) { & $cli reload | Out-Null; Write-Host 'OpenCode configuration reloaded live!' -ForegroundColor Green }\n"
            "else { Write-Host 'Restart OpenCode desktop to apply new models and tools.' -ForegroundColor Yellow }\n"
            "Write-Host 'Setup Complete! 22 models and 2 remote MCP clusters active.' -ForegroundColor Green\n"
        )
        data = script.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_command_file(self, cmd_name):
        cmd_content = ""
        if cmd_name == "sync.md":
            cmd_content = (
                "---\n"
                "description: Automatically sync the latest models, context windows, and MCP tools from the Homelab cluster\n"
                "---\n\n"
                "Fetch the latest dynamic configuration directly from the homelab cluster and reload OpenCode:\n\n"
                "1. Run the following command in terminal to update the global OpenCode config:\n"
                "   `powershell -Command \"Invoke-RestMethod -Uri 'http://192.168.1.67:8001/opencode.json' -OutFile \\\"$env:USERPROFILE\\.config\\opencode\\opencode.json\\\"\"`\n"
                "2. Then trigger OpenCode to reload its configuration:\n"
                "   `powershell -Command \"$cli = \\\"$env:LOCALAPPDATA\\Programs\\ai.opencode.desktop\\resources\\opencode-cli.exe\\\"; if (Test-Path $cli) { & $cli reload } else { opencode reload }\"`\n"
                "3. Verify the models loaded:\n"
                "   `powershell -Command \"$cli = \\\"$env:LOCALAPPDATA\\Programs\\ai.opencode.desktop\\resources\\opencode-cli.exe\\\"; if (Test-Path $cli) { & $cli models } else { opencode models }\"`\n"
                "4. Summarize the synced models, their context limits (e.g. 256k for mae-qwen38-35b-256k, 128k for mae-qwen38-35b-moe), and active remote MCP servers to the user.\n"
            )
        elif cmd_name == "deepresearch.md":
            cmd_content = (
                "---\n"
                "description: Run the deep-research loop on a topic (hot brainstorm subagent, default-temperature gating)\n"
                "---\n\n"
                "Run the deep-research protocol on the topic: $ARGUMENTS\n\n"
                "1. Frame: Restate research question, decompose into 3-6 sub-questions.\n"
                "2. Research rounds: One `deepresearch_deep_research` (or `deep_research`) call per sub-question (topic = lowercase hyphenated slug, e.g. `raising-neocaridina-shrimp`). The homelab server handles DuckDuckGo/Bing SERP and real-browser TLS impersonation automatically. Add specific URLs with `deepresearch_fetch_url` (or `fetch_url`).\n"
                "3. Evaluate: Tag each claim with its source id. Use `cite` (or `deepresearch_cite`) to inspect text excerpts.\n"
                "4. Brainstorm: Generate candidate follow-up questions.\n"
                "5. Gate: Filter candidates through relevance and novelty.\n"
                "6. Journal: Use `deepresearch_save_note` (or `save_note`) for findings, contradictions, and open questions.\n"
                "7. Converge: Stop when questions are answered or ~10 rounds reached.\n"
                "8. Synthesize & Save Locally:\n"
                "   a. CRITICAL - SAVE LOCALLY: Write the full markdown report directly to the local workspace file:\n"
                "      `Research/deep-research/<topic>/report.md`\n"
                "      using your local file writing tool (`write_file`). Create parent directories if needed. The user must have the physical markdown file on their local computer.\n"
                "   b. Archive to Cluster: Also call `deepresearch_save_report` (or `save_report`) to archive the report on the homelab cluster.\n"
                "   c. Open in Preview: Open the local file `Research/deep-research/<topic>/report.md` in the Review/preview pane with `browser.preview` (pass the local path).\n\n"
                "When finished, report: the answer summary, the local file path (`Research/deep-research/<topic>/report.md`), and the LAN URL (`http://192.168.1.67:8001/reports/<topic>`).\n"
            )
        data = cmd_content.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def handle_report_view(self):
        reports_dir = Path("/opt/homelab-mcp/deep-research")
        parts = [p for p in self.path.split("/") if p and p != "reports"]
        
        if not parts:
            topics = []
            if reports_dir.exists():
                for d in reports_dir.iterdir():
                    if d.is_dir() and (d / "report.md").exists():
                        topics.append(d.name)
            topics.sort()
            html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Homelab Deep Research Reports</title>
<style>body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; line-height: 1.6; background: #0d1117; color: #c9d1d9; }}
h1 {{ color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; }}
ul {{ list-style-type: none; padding: 0; }}
li {{ margin: 12px 0; background: #161b22; padding: 12px 16px; border-radius: 6px; border: 1px solid #30363d; }}
a {{ color: #58a6ff; text-decoration: none; font-size: 1.1em; font-weight: 500; }}
a:hover {{ text-decoration: underline; }}
</style></head><body>
<h1>Homelab Deep Research Reports</h1>
<p>Select a report to view with live Markdown & Mermaid diagrams:</p>
<ul>
{"".join(f'<li><a href="/reports/{t}">{t}</a> (<a href="/reports/{t}/raw">raw</a>)</li>' for t in topics) if topics else "<li>No reports found yet.</li>"}
</ul>
</body></html>"""
            data = html.encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        topic = parts[0]
        is_raw = len(parts) > 1 and parts[1] in ("raw", "report.md")
        report_file = reports_dir / topic / "report.md"
        if not report_file.exists():
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"Report for topic '{topic}' not found.".encode('utf-8'))
            return

        md_content = report_file.read_text(encoding="utf-8")
        if is_raw:
            data = md_content.encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        escaped_md = json.dumps(md_content)
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{topic} — Research Report</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.0/github-markdown-dark.min.css">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
<style>
body {{ background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
.markdown-body {{ box-sizing: border-box; min-width: 200px; max-width: 980px; margin: 0 auto; padding: 45px; background-color: #0d1117; border: 1px solid #30363d; border-radius: 8px; }}
.top-bar {{ max-width: 980px; margin: 0 auto 15px auto; display: flex; justify-content: space-between; align-items: center; }}
.top-bar a {{ color: #58a6ff; text-decoration: none; font-size: 14px; }}
.mermaid {{ background: #161b22; padding: 15px; border-radius: 6px; margin: 15px 0; text-align: center; }}
</style>
</head><body>
<div class="top-bar">
  <a href="/reports">&larr; Back to all reports</a>
  <a href="/reports/{topic}/raw" target="_blank">View Raw Markdown</a>
</div>
<article class="markdown-body" id="content">Loading report...</article>
<script>
  mermaid.initialize({{ startOnLoad: false, theme: 'dark' }});
  const rawMd = {escaped_md};
  const renderer = new marked.Renderer();
  const origCode = renderer.code.bind(renderer);
  renderer.code = function(code, lang) {{
    if (lang === 'mermaid') {{
      return '<div class="mermaid">' + code + '</div>';
    }}
    return origCode(code, lang);
  }};
  marked.setOptions({{ renderer: renderer, gfm: true, breaks: true }});
  document.getElementById('content').innerHTML = marked.parse(rawMd);
  mermaid.run();
</script>
</body></html>"""
        data = html.encode('utf-8')
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ["/v1/models", "/models"]:
            self.handle_models_list()
        elif self.path in ["/opencode.json", "/v1/opencode.json"]:
            self.handle_opencode_config()
        elif self.path in ["/setup.ps1", "/install.ps1"]:
            self.handle_setup_script()
        elif self.path.startswith("/commands/"):
            cmd = self.path.split("/")[-1]
            self.handle_command_file(cmd)
        elif self.path.startswith("/reports"):
            self.handle_report_view()
        elif self.path in ["/v1/taxonomy", "/taxonomy"]:
            self.handle_taxonomy()
        elif self.path in ["/v1/capabilities", "/capabilities"]:
            self.handle_capabilities()
        elif self.path in ["/health", "/"]:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "router": "cluster-router-v4.0"}).encode())
        else:
            self.proxy_request("GET")

    def do_POST(self):
        if self.path in ["/v1/chat/completions", "/chat/completions"]:
            self.handle_chat_completions()
        elif self.path in ["/v1/sot/completions", "/sot/completions", "/sot"]:
            self.handle_sot_completions()
        else:
            self.proxy_request("POST")

    def handle_sot_completions(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b""
        try:
            data = json.loads(post_body.decode('utf-8'))
            prompt = data.get("prompt")
            if not prompt and "messages" in data and data["messages"]:
                prompt = data["messages"][-1].get("content", "")
            sys_msg = next((m["content"] for m in data.get("messages", []) if m.get("role") == "system"), "")
            requested_model = data.get("model", "mae-qwen38-35b-moe")
            target_model = resolve_target_model(requested_model)
            
            # Enforce multi-slot continuous batching service for SoT
            if "256k" in target_model:
                target_model = "mae-qwen38-35b-moe"
                
            ok = ensure_model_active(target_model)
            if not ok:
                self.send_response(504)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Failed to activate target model {target_model}"}).encode())
                return
            
            log.info(f"Executing Skeleton-of-Thought on model '{target_model}' for prompt: {prompt[:60]}...")
            result = SkeletonOfThoughtEngine.execute_sot(prompt, sys_msg, target_model)
            resp_bytes = json.dumps(result).encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)
            return
        except Exception as e:
            log.error(f"Error in SoT pipeline: {e}")
            if not self.wfile.closed:
                try:
                    self.send_error(500, f"SoT Error: {e}")
                except Exception:
                    pass
            return

    def handle_taxonomy(self):
        """Returns dynamic model taxonomy with categories and badges for Open WebUI tree."""
        tax = get_model_taxonomy(MODELS)
        resp = {"status": "ok", "taxonomy": tax}
        body = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_capabilities(self):
        """Returns dynamic capability index for interactive model option pills."""
        caps = build_cluster_capabilities(MODELS)
        resp = {"status": "ok", "capabilities": caps}
        body = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_models_list(self):
        """Returns canonical models for Open WebUI model selector."""
        data = []
        for model_id, info in MODELS.items():
            if info.get("hide_from_tree"):
                continue
            data.append({
                "id": model_id,
                "name": info["name"],
                "object": "model",
                "created": 1792900000,
                "owned_by": "cluster",
                "meta": {
                    "description": info["description"]
                }
            })
        data.sort(key=lambda x: x["name"].lower())
        resp = {"object": "list", "data": data}
        body = json.dumps(resp).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_chat_completions(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len) if content_len > 0 else b""
        
        target_model = "mae-qwen38-35b-moe"
        is_stream = False
        try:
            req_json = json.loads(post_body.decode("utf-8"))
            req_model = req_json.get("model", "")
            target_model = resolve_target_model(req_model)
            is_stream = req_json.get("stream", False)
            log.info(f"Chat completion for '{req_model}' -> resolved to: '{target_model}' (stream={is_stream})")

            # Enforce prompt cache reuse
            req_json["cache_prompt"] = True

            # If target model is anime steered, reinforce persona & disable <think> blocks
            if target_model == "mae-qwen3-8b-anime":
                msgs = req_json.get("messages", [])
                persona_prompt = "/no_think\nYou are Mae, a 20-year-old anime-loving Japanese university student living in Tokyo."
                if msgs and msgs[0].get("role") != "system":
                    msgs.insert(0, {"role": "system", "content": persona_prompt})
                elif msgs and msgs[0].get("role") == "system":
                    curr = msgs[0].get("content", "")
                    if "Mae" not in curr:
                        msgs[0]["content"] = f"{persona_prompt}\n{curr}"
                    elif "/no_think" not in curr:
                        msgs[0]["content"] = f"/no_think\n{curr}"
                req_json["messages"] = msgs

            # If target model is 35B STEM Tutor, reinforce Universal 5-Stage Problem-Solving Framework
            if target_model.startswith("mae-qwen38-35b-tutor"):
                msgs = req_json.get("messages", [])
                if msgs and msgs[0].get("role") != "system":
                    msgs.insert(0, {"role": "system", "content": STEM_TUTOR_PROMPT})
                elif msgs and msgs[0].get("role") == "system":
                    curr = msgs[0].get("content", "")
                    if "Universal 5-Stage Problem-Solving Framework" not in curr:
                        msgs[0]["content"] = f"{STEM_TUTOR_PROMPT}\n\n{curr}".strip()
                req_json["messages"] = msgs
                if "temperature" not in req_json:
                    req_json["temperature"] = 0.45

            # Handle reasoning effort / thinking levels for reasoning models
            reasoning_effort = req_json.get("reasoning_effort")
            is_reasoning_model = any(k in target_model.lower() for k in ["r1", "nemotron", "phi4", "3.8", "engineering", "reason", "35b"])
            if reasoning_effort and is_reasoning_model:
                msgs = req_json.get("messages", [])
                effort_str = str(reasoning_effort).lower()
                if effort_str == "low":
                    think_directive = "### Thinking Level: Low (Fast Response)\n- Keep internal scratchpad thinking inside <think> strictly concise, high-level, and under 500 tokens.\n- Move directly to the final formulas and calculations without repetitive arithmetic."
                elif effort_str == "medium":
                    think_directive = "### Thinking Level: Medium (Balanced Reasoning)\n- Keep internal scratchpad thinking inside <think> focused, structured, and around 1,000 to 1,500 tokens.\n- Formulate governing equations clearly and proceed directly to the step-by-step solution."
                elif effort_str == "high":
                    think_directive = "### Thinking Level: High (Exhaustive Analysis)\n- Perform rigorous multi-perspective validation, consider plausible alternatives, and double-check key assumptions inside <think>.\n- Formulate derivations symbolically and present thorough verification."
                else:
                    think_directive = None

                if think_directive:
                    if msgs and msgs[0].get("role") != "system":
                        msgs.insert(0, {"role": "system", "content": think_directive})
                    elif msgs and msgs[0].get("role") == "system":
                        curr = msgs[0].get("content", "")
                        curr_clean = re.sub(r'### Thinking Level:[^\n]*\n(?:- [^\n]*\n?)*', '', curr).strip()
                        msgs[0]["content"] = f"{curr_clean}\n\n{think_directive}".strip()
                    req_json["messages"] = msgs

            # Sanitize and expand tools if present
            if "tools" in req_json and isinstance(req_json["tools"], list):
                sanitized_tools = []
                for t in req_json["tools"]:
                    if isinstance(t, dict) and t.get("type") == "function":
                        sanitized_tools.append(t)
                    elif isinstance(t, str):
                        if t in TOOL_SCHEMAS:
                            sanitized_tools.extend(TOOL_SCHEMAS[t])
                    elif isinstance(t, dict) and "name" in t:
                        sanitized_tools.append({"type": "function", "function": t})

                if sanitized_tools:
                    req_json["tools"] = sanitized_tools
                else:
                    del req_json["tools"]
            post_body = json.dumps(req_json).encode("utf-8")
        except Exception as e:
            log.warning(f"Could not parse request JSON: {e}")

        ok = ensure_model_active(target_model)
        if not ok:
            self.send_response(504)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Failed to activate target model {target_model}"}).encode())
            return

        backend_url = get_backend_url_for_model(target_model)
        self.forward_to_backend("POST", post_body, backend_url)

    def proxy_request(self, method: str):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else None
        self.forward_to_backend(method, body, BACKEND_URL_MAIN)

    def forward_to_backend(self, method: str, body: bytes, backend_base_url: str):
        target_url = f"{backend_base_url}{self.path}"
        headers = {}
        for h, val in self.headers.items():
            if h.lower() not in ["host", "content-length"]:
                headers[h] = val

        try:
            with requests.request(method, target_url, data=body, headers=headers, stream=True, timeout=300) as resp:
                self.send_response(resp.status_code)
                for k, v in resp.headers.items():
                    if k.lower() not in ["content-length", "transfer-encoding", "connection"]:
                        self.send_header(k, v)
                self.end_headers()

                for chunk in resp.iter_content(chunk_size=1024):
                    if chunk:
                        self.wfile.write(chunk)
                        self.wfile.flush()
        except Exception as e:
            log.error(f"Proxy forwarding error to {target_url}: {e}")
            if not self.wfile.closed:
                try:
                    self.send_error(502, f"Bad Gateway: {e}")
                except Exception:
                    pass

def run():
    port = 8001
    log.info(f"Starting Advanced Cluster Model Router v4.0 (Next-Gen MTP MoE & Teamwork Edition) on 0.0.0.0:{port} ...")
    server = ThreadingHTTPServer(("0.0.0.0", port), ClusterRouterHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    run()

# Upstream Credits & Acknowledgments

This project builds upon, optimizes, and integrates several exceptional open-source projects. We express our sincere gratitude to the original creators and maintainers:

### 1. llama.cpp
* **Author / Maintainers:** Georgi Gerganov and the [llama.cpp community](https://github.com/ggml-org/llama.cpp)
* **License:** MIT License
* **Contribution:** Core tensor and model inference engine. The patches in `patches/` adapt and optimize execution for NVIDIA Pascal Compute Capability 6.0 (`sm_60`).

### 2. shinbunbun/llama-cpp-p100-patches
* **Author:** [shinbunbun](https://github.com/shinbunbun/llama-cpp-p100-patches)
* **License:** MIT License
* **Contribution:** Pioneering work demonstrating FP16 matrix-vector kernels for the Pascal P100 architecture.

### 3. Model Context Protocol (MCP)
* **Author / Maintainers:** [Anthropic & MCP Contributors](https://github.com/modelcontextprotocol)
* **License:** MIT License
* **Contribution:** Standardized protocol for connecting AI coding assistants to centralized tools over Streamable HTTP and SSE.

### 4. curl_cffi
* **Author:** [Yifei Kong](https://github.com/yifeikong/curl_cffi)
* **License:** Apache 2.0 License
* **Contribution:** High-performance browser TLS and HTTP/2 frame impersonation used in the research fetcher.

---
*All patch files and scripts in this repository are distributed under the terms of the MIT License.*

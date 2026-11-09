#!/usr/bin/env bash
# Disable PCIe Access Control Services (ACS) on PCIe Root Ports
# Required on Intel Xeon / Consumer boards to allow direct GPU-to-GPU DMA transfers (P2P)
# without host CPU / chipset bottlenecks.
set -euo pipefail

echo "Detecting and disabling PCIe ACS for P2P GPU communication..."
# Scan for PCIe bridge ports and disable ACS redirection (mask 0x0000)
for BDF in $(lspci -d ::0604 | awk '{print $1}'); do
    setpci -s "$BDF" ECAP_ACS+0x6.w=0000 2>/dev/null && echo "  - ACS disabled on bridge $BDF" || true
done

echo "PCIe P2P unblocked! Check status with: nvidia-smi topo -p2p r"


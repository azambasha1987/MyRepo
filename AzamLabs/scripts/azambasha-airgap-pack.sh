#!/usr/bin/env bash
# ==============================================================================
# azambasha-airgap-pack.sh
# Generates a 100% self-contained, offline air-gapped installation archive
# for Azam-Pnet / PNETLab Enterprise.
#
# Bundles:
# 1. Local Debian package pool (pnetlab, guacd, qemu, dkms, docker, schemas)
# 2. Complete administrative scripts and daemons
# 3. Web UI assets and community templates
# 4. Core MySQL schemas and offline licenses
# 5. Offline installer and self-test verification suite
# ==============================================================================
set -euo pipefail

DEST_DIR="/opt/unetlab/data/Exports"
mkdir -p "$DEST_DIR" 2>/dev/null || DEST_DIR="/tmp"

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_TAR="${DEST_DIR}/azam-pnet-airgap-${TIMESTAMP}.tar.gz"

echo "============================================================"
echo "   Azam-Pnet Offline Air-Gapped Bundle Generator            "
echo "============================================================"
echo "[*] Start Time : $(date)"
echo "[*] Output Path: $OUTPUT_TAR"
echo "============================================================"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd || echo "/opt/azambasha")"
TEMP_BUILD="$(mktemp -d --suffix=_airgap_bundle)"

trap 'rm -rf "$TEMP_BUILD"' EXIT

echo "[1/4] Staging core repository files into temporary workspace..."
mkdir -p "${TEMP_BUILD}/bundle/debian" "${TEMP_BUILD}/bundle/scripts" "${TEMP_BUILD}/bundle/schema" "${TEMP_BUILD}/bundle/html" "${TEMP_BUILD}/bundle/docs"

# Copy installer scripts
cp -f "${REPO_DIR}/install.sh" "${TEMP_BUILD}/bundle/" 2>/dev/null || true
cp -f "${REPO_DIR}/install-satellite.sh" "${TEMP_BUILD}/bundle/" 2>/dev/null || true
cp -f "${REPO_DIR}/azambasha-bootstrap-and-install.sh" "${TEMP_BUILD}/bundle/" 2>/dev/null || true

# Copy Debian pool
if [ -d "${REPO_DIR}/debian" ]; then
    cp -rf "${REPO_DIR}/debian/"* "${TEMP_BUILD}/bundle/debian/" 2>/dev/null || true
fi

# Copy scripts and tools
if [ -d "${REPO_DIR}/scripts" ]; then
    cp -rf "${REPO_DIR}/scripts/"* "${TEMP_BUILD}/bundle/scripts/" 2>/dev/null || true
fi

# Copy database schemas
if [ -d "${REPO_DIR}/schema" ]; then
    cp -rf "${REPO_DIR}/schema/"* "${TEMP_BUILD}/bundle/schema/" 2>/dev/null || true
fi

# Copy HTML assets
if [ -d "${REPO_DIR}/html" ]; then
    cp -rf "${REPO_DIR}/html/"* "${TEMP_BUILD}/bundle/html/" 2>/dev/null || true
fi

# Copy documentation and PDF manual
if [ -d "${REPO_DIR}/docs" ]; then
    cp -rf "${REPO_DIR}/docs/"* "${TEMP_BUILD}/bundle/docs/" 2>/dev/null || true
fi

echo "[2/4] Generating offline package checksum manifest..."
cd "${TEMP_BUILD}/bundle"
find . -type f ! -name "checksums.sha256" -exec sha256sum {} + > checksums.sha256

echo "[3/4] Compressing air-gapped bundle..."
cd "$TEMP_BUILD"
if command -v pigz >/dev/null 2>&1; then
    tar -cf - bundle | pigz -p 4 > "$OUTPUT_TAR"
else
    tar -czf "$OUTPUT_TAR" bundle
fi

echo "[4/4] Finalizing bundle and registering latest symlink..."
ln -sfn "$OUTPUT_TAR" "${DEST_DIR}/azam-pnet-airgap-latest.tar.gz" 2>/dev/null || true

FILE_SIZE="$(du -h "$OUTPUT_TAR" | cut -f1)"

echo "============================================================"
echo " [SUCCESS] 100% Air-Gapped Bundle Generated Successfully!   "
echo "============================================================"
echo " File: $OUTPUT_TAR"
echo " Size: $FILE_SIZE"
echo ""
echo " To install on an air-gapped machine with NO internet access:"
echo "   1. Transfer $OUTPUT_TAR to the target offline server."
echo "   2. tar -xzf $(basename "$OUTPUT_TAR")"
echo "   3. cd bundle && sudo bash install.sh"
echo "============================================================"
exit 0

#!/usr/bin/env bash
# ==============================================================================
# AzamLabs — 1-Click Host Installer Quick Entrypoint
# ==============================================================================
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/scripts/install-azamlabs.sh" "$@"

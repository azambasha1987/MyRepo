#!/usr/bin/env bash
# ==============================================================================
# Azam Basha Lab Topology & Device Config Auto-Backup & Restore Engine
# ==============================================================================
# Backs up and restores:
#   1. All .unl topology files (/opt/unetlab/labs/)
#   2. All saved node startup & running configs (/opt/unetlab/data/Labs/)
#   3. MySQL pnetlab_db lab hierarchy, folders, and node metadata
# ==============================================================================
set -euo pipefail

BACKUP_DIR="/opt/azambasha/backups"
LABS_DIR="/opt/unetlab/labs"
DATA_DIR="/opt/unetlab/data/Labs"

# Install symlinks if running as root
if [ "$(id -u)" -eq 0 ]; then
    ln -sf "$(realpath "$0")" /usr/local/bin/azam-backup 2>/dev/null || true
    ln -sf "$(realpath "$0")" /usr/local/bin/azam-restore 2>/dev/null || true
fi

usage() {
    echo "Usage: sudo azam-backup [OPTION]"
    echo ""
    echo "Options:"
    echo "  --backup           Create a complete timestamped backup of all labs and configs (default)"
    echo "  --list             List all existing backup bundles"
    echo "  --restore <FILE>   Restore labs, configs, and database from specified backup archive"
    echo "  --prune <DAYS>     Remove backups older than N days (default: 30)"
    echo "  -h, --help         Show this help message"
    exit 0
}

MODE="backup"
RESTORE_FILE=""
PRUNE_DAYS=30

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backup)
            MODE="backup"
            shift
            ;;
        --list)
            MODE="list"
            shift
            ;;
        --restore)
            MODE="restore"
            RESTORE_FILE="${2:-}"
            shift 2 || { echo "[!] Error: --restore requires a backup file path."; exit 1; }
            ;;
        --prune)
            MODE="prune"
            PRUNE_DAYS="${2:-30}"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            # If invoked as azam-restore <file>
            if [[ "$(basename "$0")" == *"restore"* ]]; then
                MODE="restore"
                RESTORE_FILE="$1"
                shift
            else
                echo "[!] Unknown argument: $1"
                usage
            fi
            ;;
    esac
done

mkdir -p "$BACKUP_DIR"

if [ "$MODE" = "list" ]; then
    echo "================================================================================"
    echo "                   Azam-Pnet Existing Lab Backup Bundles                        "
    echo "================================================================================"
    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
        echo "  (No backups found in $BACKUP_DIR)"
    else
        ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null | awk '{printf "  ↳ %-45s Size: %s  Date: %s %s\n", $9, $5, $6, $7}'
    fi
    echo "================================================================================"
    exit 0
fi

if [ "$MODE" = "restore" ]; then
    if [ -z "$RESTORE_FILE" ] || [ ! -f "$RESTORE_FILE" ]; then
        echo "[!] Error: Backup file not found: '$RESTORE_FILE'"
        echo "Use 'sudo azam-backup --list' to see available backups."
        exit 1
    fi

    echo "================================================================================"
    echo "          Azam-Pnet Lab Restore Engine - Processing Archive                     "
    echo "================================================================================"
    echo "[*] Target Archive: $RESTORE_FILE"

    TEMP_EXTRACT=$(mktemp -d /tmp/azam-restore.XXXXXX)
    trap 'rm -rf "$TEMP_EXTRACT"' EXIT

    echo "[*] Extracting archive..."
    tar -xzf "$RESTORE_FILE" -C "$TEMP_EXTRACT"

    # 1. Restore Labs
    if [ -d "$TEMP_EXTRACT/labs" ]; then
        echo "[*] Restoring .unl topologies to $LABS_DIR..."
        mkdir -p "$LABS_DIR"
        cp -rn "$TEMP_EXTRACT/labs/"* "$LABS_DIR/" 2>/dev/null || true
    fi

    # 2. Restore Device Configs
    if [ -d "$TEMP_EXTRACT/data_labs" ]; then
        echo "[*] Restoring saved device configs to $DATA_DIR..."
        mkdir -p "$DATA_DIR"
        cp -rn "$TEMP_EXTRACT/data_labs/"* "$DATA_DIR/" 2>/dev/null || true
    fi

    # 3. Restore Database metadata
    if [ -f "$TEMP_EXTRACT/pnetlab_db.sql" ] && command -v mysql &>/dev/null; then
        echo "[*] Restoring database lab hierarchy and tables..."
        mysql -u root -pazam pnetlab_db < "$TEMP_EXTRACT/pnetlab_db.sql" 2>/dev/null || true
    fi

    # 4. Repair Permissions
    echo "[*] Normalizing permissions across restored topologies..."
    if [ -x /opt/unetlab/wrappers/unl_wrapper ]; then
        /opt/unetlab/wrappers/unl_wrapper -a fixpermissions || true
    fi
    chown -R root:root "$LABS_DIR" "$DATA_DIR" 2>/dev/null || true
    chmod -R 755 "$LABS_DIR" "$DATA_DIR" 2>/dev/null || true

    echo "================================================================================"
    echo "[✔] Restore completed successfully! All labs and startup configs are online."
    echo "================================================================================"
    exit 0
fi

# Default: Backup
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BUNDLE_NAME="azam_lab_backup_${TIMESTAMP}.tar.gz"
BUNDLE_PATH="${BACKUP_DIR}/${BUNDLE_NAME}"
TEMP_STAGING=$(mktemp -d /tmp/azam-backup.XXXXXX)
trap 'rm -rf "$TEMP_STAGING"' EXIT

echo "================================================================================"
echo "          Azam-Pnet Lab Topology & Config Auto-Backup Engine                     "
echo "================================================================================"
echo "[*] Starting backup snapshot at $(date)..."

# 1. Stage Labs
if [ -d "$LABS_DIR" ]; then
    echo "[*] Staging .unl topologies from $LABS_DIR..."
    mkdir -p "$TEMP_STAGING/labs"
    cp -r "$LABS_DIR/"* "$TEMP_STAGING/labs/" 2>/dev/null || true
fi

# 2. Stage Configs
if [ -d "$DATA_DIR" ]; then
    echo "[*] Staging device startup configurations from $DATA_DIR..."
    mkdir -p "$TEMP_STAGING/data_labs"
    cp -r "$DATA_DIR/"* "$TEMP_STAGING/data_labs/" 2>/dev/null || true
fi

# 3. Stage Database Dump
if command -v mysqldump &>/dev/null; then
    echo "[*] Exporting pnetlab_db database structure and records..."
    mysqldump -u root -pazam --single-transaction --quick pnetlab_db > "$TEMP_STAGING/pnetlab_db.sql" 2>/dev/null || true
fi

# 4. Create Compressed Tarball
echo "[*] Compressing backup into $BUNDLE_PATH..."
tar -czf "$BUNDLE_PATH" -C "$TEMP_STAGING" .

BUNDLE_SIZE=$(du -h "$BUNDLE_PATH" | awk '{print $1}')

echo "================================================================================"
echo "[✔] Backup completed successfully!"
echo "    ↳ Archive File: $BUNDLE_PATH"
echo "    ↳ Size:         $BUNDLE_SIZE"
echo "    ↳ Restore with: sudo azam-restore $BUNDLE_PATH"
echo "================================================================================"

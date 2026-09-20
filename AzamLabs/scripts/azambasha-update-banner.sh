#!/usr/bin/env bash
# ==============================================================================
# azambasha-update-banner.sh
# Universal Dynamic Console Banner Updater for Master & Satellite Nodes
# Auto-detects live IP, node role, polls for DHCP during boot, and refreshes /etc/issue.
# ==============================================================================

MAX_WAIT_SECONDS=15

# 1. Resolve Live IPv4 Address with Polling Support
resolve_live_ip() {
    local ip=""

    # Tier 1: pnet0 bridge IPv4
    ip=$(ip -4 addr show dev pnet0 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | grep -v '^127\.' | grep -v '^169\.254\.' | head -n1)
    if [ -n "$ip" ]; then
        echo "$ip"
        return 0
    fi

    # Tier 2: Interface handling default gateway route
    local def_iface
    def_iface=$(ip -4 route show default 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="dev") print $(i+1)}' | head -n1)
    if [ -n "$def_iface" ]; then
        ip=$(ip -4 addr show dev "$def_iface" 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | grep -v '^127\.' | grep -v '^169\.254\.' | head -n1)
        if [ -n "$ip" ]; then
            echo "$ip"
            return 0
        fi
    fi

    # Tier 3: Any physical or primary bridge interface (ens*, enp*, eth*, eno*, br*)
    for iface in $(ip -o link show 2>/dev/null | awk -F': ' '{print $2}' | cut -d'@' -f1); do
        case "$iface" in
            lo|docker*|veth*|virbr*|tun*|tap*|dummy*|wg*|zt*) continue ;;
            *)
                ip=$(ip -4 addr show dev "$iface" 2>/dev/null | awk '/inet /{print $2}' | cut -d/ -f1 | grep -v '^127\.' | grep -v '^169\.254\.' | head -n1)
                if [ -n "$ip" ]; then
                    echo "$ip"
                    return 0
                fi
                ;;
        esac
    done

    # Tier 4: Fallback to non-loopback hostname -I
    ip=$(hostname -I 2>/dev/null | tr ' ' '\n' | grep -v '^127\.' | grep -v '^169\.254\.' | grep -v '^172\.1[7-9]\.' | head -n1)
    if [ -n "$ip" ]; then
        echo "$ip"
        return 0
    fi

    return 1
}

get_ip() {
    local ip=""
    local elapsed=0

    # Wait for DHCP or network assignment if called during boot
    while [ $elapsed -lt $MAX_WAIT_SECONDS ]; do
        ip=$(resolve_live_ip || true)
        if [ -n "$ip" ] && [ "$ip" != "127.0.0.1" ]; then
            echo "$ip"
            return 0
        fi
        sleep 1
        elapsed=$((elapsed + 1))
    done

    # Final attempt fallback
    ip=$(resolve_live_ip || true)
    if [ -n "$ip" ]; then
        echo "$ip"
    else
        echo "127.0.0.1"
    fi
}

HOST_IP="$(get_ip)"

# 2. Detect Node Role (Master Controller vs Satellite Worker Node)
ROLE="Master Controller"
if [ -f "/etc/pnetlab-role" ]; then
    DETECTED_ROLE="$(cat /etc/pnetlab-role 2>/dev/null || true)"
    [ "$DETECTED_ROLE" = "satellite" ] && ROLE="Satellite Worker Node"
    [ "$DETECTED_ROLE" = "master" ] && ROLE="Master Controller"
elif [ -d "/opt/unetlab/html" ] || [ -f "/etc/apache2/sites-available/pnetlab.conf" ]; then
    ROLE="Master Controller"
elif systemctl is-active --quiet pnetlab-satd 2>/dev/null || [ -f "/opt/unetlab/data/satellite.json" ]; then
    ROLE="Satellite Worker Node"
fi

# 3. Generate Formatted Banner
if [ "$ROLE" = "Satellite Worker Node" ]; then
    PAIR_STATUS="Ready for Master Pairing"
    if [ -f "/opt/unetlab/data/satellite.json" ] && grep -q "master_ip" "/opt/unetlab/data/satellite.json" 2>/dev/null; then
        MASTER_HOST=$(grep -o '"master_ip"[^,]*' /opt/unetlab/data/satellite.json | cut -d'"' -f4)
        [ -n "$MASTER_HOST" ] && PAIR_STATUS="Paired with Master (${MASTER_HOST})"
    fi

    cat > /etc/issue << EOF

============================================================
           Azam Basha v8 Virtual Network Emulator
============================================================
  Role            : ${ROLE}
  Status          : ${PAIR_STATUS}
  SSH Management  : ssh root@${HOST_IP} (Password: azam)
============================================================

\S (\l)

EOF
else
    cat > /etc/issue << EOF

============================================================
           Azam Basha v8 Virtual Network Emulator
============================================================
  Role            : ${ROLE}
  Web UI Access   : https://${HOST_IP}/
  Default User    : admin
  Default Pass    : azam
  SSH Management  : ssh root@${HOST_IP} (Password: azam)
============================================================

\S (\l)

EOF
fi

cp -f /etc/issue /etc/issue.net 2>/dev/null || true
echo "[azambasha-banner] Role: ${ROLE} | Updated /etc/issue -> IP: ${HOST_IP}"

# 4. Refresh Active TTY Console so the banner updates on screen immediately
if [ -c /dev/tty1 ]; then
    pkill -HUP -f 'agetty.*tty1' 2>/dev/null || true
fi

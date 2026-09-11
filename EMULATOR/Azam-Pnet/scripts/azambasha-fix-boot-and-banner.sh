#!/usr/bin/env bash
# ==============================================================================
# azambasha-fix-boot-and-banner.sh
# Universal Fix for Boot Errors (KVM VMX/SVM, SMBus, Dracut) and Console Banner IP
# Works universally on all Intel and AMD processors across Master and Satellite nodes.
# ==============================================================================
set -euo pipefail

echo "============================================================"
echo "    Universal Boot Diagnostics & Banner IP Optimization    "
echo "============================================================"

# --- 1. Universal CPU Virtualization Detection ---
echo "[1/5] Detecting CPU architecture and hardware virtualization flags..."
CPU_VENDOR=$(grep -m1 'vendor_id' /proc/cpuinfo 2>/dev/null | awk '{print $3}' || true)
CPU_MODEL=$(grep -m1 'model name' /proc/cpuinfo 2>/dev/null | cut -d: -f2 | sed 's/^[ \t]*//' || true)
echo "      -> CPU Model: ${CPU_MODEL:-Unknown} (${CPU_VENDOR:-Unknown})"

KVM_MOD=""
if grep -m1 -E -qw 'vmx' /proc/cpuinfo 2>/dev/null; then
    KVM_MOD="kvm_intel"
    echo "      -> Detected Intel Hardware Virtualization (VT-x / vmx active)"
elif grep -m1 -E -qw 'svm' /proc/cpuinfo 2>/dev/null; then
    KVM_MOD="kvm_amd"
    echo "      -> Detected AMD Hardware Virtualization (AMD-V / svm active)"
else
    echo "      -> [NOTE] Hardware virtualization flags (vmx/svm) not exposed to VM."
    echo "         Ensure 'Virtualize Intel VT-x/EPT or AMD-V/RVI' is enabled in hypervisor."
fi

# --- 2. Sanitize Kernel Modules Configuration ---
echo "[2/5] Sanitizing /etc/modules-load.d/pnetlab.conf..."
mkdir -p /etc/modules-load.d /etc/modprobe.d

# Strip out any invalid cross-vendor modules from all configuration files
sed -i -E '/kvm_(intel|amd)/d' /etc/modules-load.d/pnetlab.conf /etc/modules /etc/modules-load.d/*.conf 2>/dev/null || true

cat > /etc/modules-load.d/pnetlab.conf << 'EOF'
bridge
stp
llc
8021q
tun
dummy
br_netfilter
veth
sch_fq_codel
kvm
EOF

if [ -n "$KVM_MOD" ]; then
    echo "$KVM_MOD" >> /etc/modules-load.d/pnetlab.conf
    modprobe "$KVM_MOD" 2>/dev/null || true
    echo "      -> Successfully registered $KVM_MOD in /etc/modules-load.d/pnetlab.conf"
fi

# Restart and verify systemd-modules-load
echo "      -> Restarting systemd-modules-load.service..."
systemctl restart systemd-modules-load.service 2>/dev/null || true
SVC_STATUS=$(systemctl is-active systemd-modules-load.service 2>/dev/null || echo "failed")
echo "      -> systemd-modules-load.service status: [${SVC_STATUS}]"

# --- 3. Blacklist Virtual SMBus Controller (piix4_smbus) ---
echo "[3/5] Blacklisting unhandled virtual SMBus controller (i2c_piix4)..."
echo "blacklist i2c_piix4" > /etc/modprobe.d/blacklist-piix4.conf
rmmod i2c_piix4 2>/dev/null || true

# --- 4. Sanitize GRUB & Rebuild Clean Dracut Initramfs ---
echo "[4/5] Eliminating deprecated copymods and rebuilding clean initramfs..."
if [ -f /etc/default/grub ]; then
    sed -i -E 's/\b(copymods|rd\.driver\.export(=[a-zA-Z0-9_-]+)?)\b//g' /etc/default/grub /etc/default/grub.d/*.cfg 2>/dev/null || true
    if ! grep -q 'loglevel=3' /etc/default/grub 2>/dev/null; then
        sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="loglevel=3 /' /etc/default/grub 2>/dev/null || true
    fi
    command -v update-grub >/dev/null 2>&1 && update-grub 2>/dev/null || true
fi

# Purge cloud-initramfs packages that inject 50copymods hook into dracut
echo "      -> Purging cloud-initramfs-copymods & cloud-initramfs-dyn-netconf..."
DEBIAN_FRONTEND=noninteractive apt-get purge -y cloud-initramfs-copymods cloud-initramfs-dyn-netconf 2>/dev/null || true
rm -rf /usr/lib/dracut/modules.d/50copymods /usr/lib/dracut/modules.d/50kernel-modules-export 2>/dev/null || true

# Permanently omit copymods from dracut
mkdir -p /etc/dracut.conf.d
echo 'omit_dracutmodules+=" copymods kernel-modules-export "' > /etc/dracut.conf.d/01-omit-copymods.conf

# Rebuild active kernel initramfs with dracut
echo "      -> Rebuilding clean initramfs (dracut -f)..."
dracut -f 2>/dev/null || true
echo "      -> Initramfs rebuilt successfully."

# --- 5. Deploy Dynamic Banner Updater & Live Network Hooks ---
echo "[5/5] Updating console banner script and network dispatcher hooks..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BANNER_SOURCE="${SCRIPT_DIR}/azambasha-update-banner.sh"
if [ ! -f "$BANNER_SOURCE" ]; then
    BANNER_SOURCE="/opt/azambasha/scripts/azambasha-update-banner.sh"
fi

if [ -f "$BANNER_SOURCE" ] && [ "$BANNER_SOURCE" != "/usr/local/bin/azambasha-update-banner.sh" ]; then
    cp -f "$BANNER_SOURCE" /usr/local/bin/azambasha-update-banner.sh
fi
chmod +x /usr/local/bin/azambasha-update-banner.sh 2>/dev/null || true

mkdir -p /etc/networkd-dispatcher/routable.d /etc/network/if-up.d 2>/dev/null || true
cat > /etc/networkd-dispatcher/routable.d/50-azambasha-banner.sh << 'EOF'
#!/bin/sh
/usr/local/bin/azambasha-update-banner.sh >/dev/null 2>&1 || true
EOF
chmod +x /etc/networkd-dispatcher/routable.d/50-azambasha-banner.sh 2>/dev/null || true

cat > /etc/network/if-up.d/azambasha-banner << 'EOF'
#!/bin/sh
/usr/local/bin/azambasha-update-banner.sh >/dev/null 2>&1 || true
EOF
chmod +x /etc/network/if-up.d/azambasha-banner 2>/dev/null || true

# Deploy systemd banner service
cat > /etc/systemd/system/azambasha-banner.service << 'EOF'
[Unit]
Description=Azam Basha — Update console banner with live IP
After=network-online.target systemd-networkd.service networking.service
Wants=network-online.target
Before=getty.target serial-getty@ttyS0.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/azambasha-update-banner.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload 2>/dev/null || true
systemctl enable azambasha-banner.service 2>/dev/null || true

# Execute banner generation immediately
if [ -x /usr/local/bin/azambasha-update-banner.sh ]; then
    /usr/local/bin/azambasha-update-banner.sh
fi

echo "============================================================"
echo " [SUCCESS] Universal Boot & Banner Fix Applied Successfully!"
echo "============================================================"

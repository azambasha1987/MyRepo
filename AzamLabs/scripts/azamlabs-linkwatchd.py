#!/usr/bin/env python3
# azamlabs-linkwatchd — per-link traffic watcher for the Network Watcher UI.
#
# One process per watch session, spawned by azamlabs-brokerd (linkwatch_start)
# as a transient systemd unit "pnet-linkwatch-<watch_id>". Reads its config
# from /dev/shm/pnet-watch/<watch_id>.conf.json (root-written by brokerd):
#
#   {"watch_id": "1_12",
#    "interfaces": ["vunl3_0", "vunl4_0"],
#    "filters": [{"id": "f0", "expr": "ip proto 89 or (vlan and ip proto 89)"}],
#    "hb_timeout": 180}
#
# For each (interface x filter) it opens an AF_PACKET socket with the filter
# attached IN-KERNEL as classic BPF (compiled in-process via libpcap, attached via
# SO_ATTACH_FILTER) — non-matching traffic never reaches userspace, so the
# steady-state cost is near zero. All sockets sit on one epoll loop. Once a
# second it writes an atomic JSON snapshot consumed by pnq-linkwatch.php:
#
#   {"ts": ..., "watch_id": "1_12", "filters": ["f0"],
#    "taps": {"vunl3_0": {"f0": {
#        "out": {"pps": 2, "total": 120, "last_ts": ..., "last": "summary"},
#        "in":  {...}}}}}
#
# "out" = node -> network, "in" = network -> node. On a host tap the kernel
# tags frames the guest EMITS as PACKET_HOST/BROADCAST/... (they arrive at the
# host over the tap) and frames the bridge DELIVERS to the guest as
# PACKET_OUTGOING — i.e. the intuitive sense is inverted (verified on the
# Noble gate, see docs). DIR_BY_PKTTYPE below is the single switch point.
#
# Lifecycle: exits cleanly (snapshot/conf/hb unlinked) when the heartbeat file
# <watch_id>.hb (touched by pnq-linkwatch.php on every GET) goes stale, when
# every watched tap disappears (lab stopped), or on SIGTERM (linkwatch_stop).
# On SIGHUP (brokerd linkwatch_start / linkwatch_reload on an already-running
# watch) it re-reads conf.json and DIFFS its socket set — opening sockets for
# newly-added (tap x filter) pairs and closing removed ones — while PRESERVING
# the counters of every surviving pair (live filter add/remove, no reset).

import ctypes
import errno
import json
import os
import selectors
import signal
import socket
import struct
import sys
import time

from pnet_bpfcompile import compile_bpf

LW_DIR = "/dev/shm/pnet-watch"
ETH_P_ALL = 0x0003
SO_ATTACH_FILTER = 26
PACKET_OUTGOING = 4
SNAPLEN = 256          # enough for the one-line summary decode
MAX_READS_PER_TICK = 400   # per socket; bounds CPU under floods (counts then
                           # undercount — acceptable for a teaching visual)


PROTO_NAMES = {
    1: "ICMP", 2: "IGMP", 4: "IP-in-IP", 6: "TCP", 17: "UDP", 41: "6in4",
    44: "IPv6 fragment", 46: "RSVP", 47: "GRE", 50: "ESP", 51: "AH",
    58: "ICMPv6", 88: "EIGRP", 89: "OSPF", 103: "PIM", 112: "VRRP",
    115: "L2TPv3", 124: "IS-IS", 132: "SCTP", 137: "MPLS-in-IP",
}
PORT_NAMES = {
    20: "FTP", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 49: "TACACS+",
    53: "DNS", 67: "DHCP", 68: "DHCP", 69: "TFTP", 80: "HTTP", 88: "Kerberos",
    123: "NTP", 137: "NetBIOS", 138: "NetBIOS", 139: "NetBIOS", 161: "SNMP",
    162: "SNMP trap", 179: "BGP", 389: "LDAP", 443: "HTTPS", 445: "SMB",
    500: "IKE", 514: "Syslog", 520: "RIP", 521: "RIPng", 546: "DHCPv6",
    547: "DHCPv6", 636: "LDAPS", 639: "MSDP", 646: "LDP", 830: "NETCONF",
    1645: "RADIUS", 1646: "RADIUS", 1701: "L2TP", 1723: "PPTP",
    1812: "RADIUS", 1813: "RADIUS", 1900: "SSDP", 1985: "HSRP", 2029: "HSRP",
    2055: "NetFlow", 2123: "GTP-C", 2152: "GTP-U", 3222: "GLBP", 3389: "RDP",
    3503: "LSP ping", 3784: "BFD", 3785: "BFD echo", 4189: "PCEP",
    4341: "LISP", 4342: "LISP", 4500: "IPsec NAT-T", 4739: "IPFIX",
    4784: "BFD", 4789: "VXLAN", 5060: "SIP", 5246: "CAPWAP", 5247: "CAPWAP",
    5353: "mDNS", 5355: "LLMNR", 5900: "VNC", 6081: "Geneve", 6343: "sFlow",
    6653: "OpenFlow", 6784: "BFD", 8472: "VXLAN",
}
# Non-IP EtherTypes seen in labs (and on the bridged LAN: TIPC, Wake-on-LAN, ...).
# 0x9000 is the loopback frame IOS sends as its Ethernet interface keepalive.
ETHER_NAMES = {
    0x0842: "Wake-on-LAN", 0x22F3: "TRILL", 0x8035: "RARP", 0x809B: "AppleTalk",
    0x80F3: "AARP", 0x8137: "IPX", 0x8808: "Flow control", 0x8847: "MPLS",
    0x8848: "MPLS", 0x8863: "PPPoE", 0x8864: "PPPoE", 0x888E: "802.1X",
    0x8892: "PROFINET", 0x88A2: "AoE", 0x88A4: "EtherCAT", 0x88B8: "GOOSE",
    0x88BA: "IEC 61850 SV", 0x88CA: "TIPC", 0x88CC: "LLDP", 0x88E1: "HomePlug",
    0x88E3: "MRP", 0x88E5: "MACsec", 0x88E7: "PBB", 0x88F7: "PTP",
    0x88F8: "NC-SI", 0x88FB: "PRP", 0x8902: "CFM", 0x8903: "FabricPath",
    0x8906: "FCoE", 0x8914: "FIP", 0x8915: "RoCE", 0x892F: "HSR",
    0x893A: "IEEE 1905", 0x894F: "NSH", 0x9000: "Keepalive",
}
SLOW_PROTOCOLS = {1: "LACP", 2: "LACP Marker", 3: "OAM", 10: "ESMC"}
CISCO_SNAP = {0x2000: "CDP", 0x2003: "VTP", 0x2004: "DTP", 0x0111: "UDLD",
              0x0104: "PAgP"}

# Message-type names shown as the envelope's second word ("OSPF Hello").
ICMP_KINDS = {0: "echo reply", 3: "unreachable", 4: "source quench", 5: "redirect",
              8: "echo request", 9: "router advert", 10: "router solicit",
              11: "time exceeded", 12: "param problem", 13: "timestamp",
              14: "timestamp reply"}
ICMP6_KINDS = {1: "unreachable", 2: "too big", 3: "time exceeded",
               4: "param problem", 128: "echo request", 129: "echo reply",
               130: "MLD query", 131: "MLD report", 132: "MLD done", 133: "RS",
               134: "RA", 135: "NS", 136: "NA", 137: "redirect",
               143: "MLDv2 report"}
IGMP_KINDS = {0x11: "query", 0x12: "v1 report", 0x16: "v2 report", 0x17: "leave",
              0x22: "v3 report"}
OSPF_KINDS = {1: "Hello", 2: "DBD", 3: "LSR", 4: "LSU", 5: "LSAck"}
EIGRP_KINDS = {1: "Update", 2: "Request", 3: "Query", 4: "Reply", 5: "Hello",
               10: "SIA-Query", 11: "SIA-Reply"}
PIM_KINDS = {0: "Hello", 1: "Register", 2: "Register-Stop", 3: "Join/Prune",
             4: "Bootstrap", 5: "Assert", 8: "C-RP-Adv"}
GRE_INNER = {0x0800: "IPv4", 0x86DD: "IPv6", 0x8847: "MPLS", 0x6558: "Ethernet",
             0x88BE: "ERSPAN", 0x22EB: "ERSPAN", 0x880B: "PPP"}
BGP_KINDS = {1: "OPEN", 2: "UPDATE", 3: "NOTIFICATION", 4: "KEEPALIVE",
             5: "ROUTE-REFRESH"}
DHCP_KINDS = {1: "Discover", 2: "Offer", 3: "Request", 4: "Decline", 5: "Ack",
              6: "Nak", 7: "Release", 8: "Inform"}
DHCP6_KINDS = {1: "Solicit", 2: "Advertise", 3: "Request", 4: "Confirm", 5: "Renew",
               6: "Rebind", 7: "Reply", 8: "Release", 9: "Decline",
               10: "Reconfigure", 11: "Info-Request", 12: "Relay-Forw",
               13: "Relay-Repl"}
HSRP_KINDS = {0: "Hello", 1: "Coup", 2: "Resign"}
BFD_STATES = {0: "AdminDown", 1: "Down", 2: "Init", 3: "Up"}
RIP_KINDS = {1: "request", 2: "response"}
NTP_KINDS = {1: "symmetric", 2: "symmetric", 3: "client", 4: "server",
             5: "broadcast"}
IKE_KINDS = {2: "Main Mode", 4: "Aggressive", 5: "Informational", 32: "Quick Mode",
             34: "SA_INIT", 35: "AUTH", 36: "CREATE_CHILD", 37: "INFORMATIONAL"}
ISIS_KINDS = {15: "L1 Hello", 16: "L2 Hello", 17: "P2P Hello", 18: "L1 LSP",
              20: "L2 LSP", 24: "L1 CSNP", 25: "L2 CSNP", 26: "L1 PSNP",
              27: "L2 PSNP"}
EAPOL_KINDS = {0: "EAP", 1: "Start", 2: "Logoff", 3: "Key"}
EAP_CODES = {1: "Request", 2: "Response", 3: "Success", 4: "Failure"}
PPPOE_DISC = {0x09: "PADI", 0x07: "PADO", 0x19: "PADR", 0x65: "PADS", 0xA7: "PADT"}
PPP_PROTOS = {0xC021: "LCP", 0x8021: "IPCP", 0x8057: "IPv6CP", 0x0021: "IPv4",
              0x0057: "IPv6", 0xC023: "PAP", 0xC223: "CHAP"}
CFM_KINDS = {1: "CCM", 2: "LBR", 3: "LBM", 4: "LTR", 5: "LTM", 33: "AIS", 35: "LCK",
             42: "LMR", 43: "LMM", 46: "DMR", 47: "DMM"}
PTP_KINDS = {0: "Sync", 1: "Delay_Req", 2: "Pdelay_Req", 3: "Pdelay_Resp",
             8: "Follow_Up", 9: "Delay_Resp", 10: "Pdelay_Resp_FU", 11: "Announce",
             12: "Signaling", 13: "Management"}


def log(msg):
    print(msg, file=sys.stderr, flush=True)


def open_filtered_socket(iface, prog_n, prog_buf):
    """AF_PACKET socket with the cBPF program attached BEFORE bind: protocol 0
    receives nothing, so no unfiltered packets ever queue (no drain race)."""
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, 0)
    # keep a reference to the ctypes buffer alive for the setsockopt call
    fprog = struct.pack("HL", prog_n, ctypes.addressof(prog_buf))
    s.setsockopt(socket.SOL_SOCKET, SO_ATTACH_FILTER, fprog)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)
    s.bind((iface, ETH_P_ALL))
    s.setblocking(False)
    return s


# ---- packet summary (rate-limited, stdlib decode) ------------------------------

def _tcp_kind(pkt, off, svc):
    if len(pkt) < off + 14:
        return None
    flags = pkt[off + 13]
    if flags & 0x04:
        return "RST"
    if flags & 0x02:
        return "SYN-ACK" if flags & 0x10 else "SYN"
    if flags & 0x01:
        return "FIN"
    if svc == "BGP":
        po = off + (pkt[off + 12] >> 4) * 4
        if len(pkt) >= po + 19 and pkt[po:po + 16] == b"\xff" * 16:
            return BGP_KINDS.get(pkt[po + 18])
    return None


def _dhcp_kind(pkt, po):
    n = len(pkt)
    if n < po + 240 or pkt[po + 236:po + 240] != b"\x63\x82\x53\x63":
        return None
    i = po + 240
    while i + 1 < n:                       # walk options to 53 (message type)
        code = pkt[i]
        if code == 0:
            i += 1
            continue
        if code == 255:
            break
        if code == 53 and pkt[i + 1] >= 1 and i + 2 < n:
            return DHCP_KINDS.get(pkt[i + 2])
        i += 2 + pkt[i + 1]
    return None


def _udp_kind(pkt, po, svc):
    n = len(pkt)
    if n <= po:
        return None
    if svc in ("DNS", "mDNS", "LLMNR"):
        return ("response" if pkt[po + 2] & 0x80 else "query") if n > po + 2 else None
    if svc == "DHCP":
        return _dhcp_kind(pkt, po)
    if svc == "DHCPv6":
        return DHCP6_KINDS.get(pkt[po])
    if svc == "HSRP":
        return HSRP_KINDS.get(pkt[po + 1]) if n > po + 1 and pkt[po] == 0 else None
    if svc == "BFD":
        return BFD_STATES.get(pkt[po + 1] >> 6) if n > po + 1 else None
    if svc in ("RIP", "RIPng"):
        return RIP_KINDS.get(pkt[po])
    if svc == "NTP":
        return NTP_KINDS.get(pkt[po] & 0x07)
    if svc == "IKE":
        return IKE_KINDS.get(pkt[po + 18]) if n > po + 18 else None
    if svc == "VXLAN" and n >= po + 8 and pkt[po] & 0x08:
        return "VNI %d" % (struct.unpack_from("!I", pkt, po + 4)[0] >> 8)
    return None


def _l4(proto, pkt, off):
    """(name, src-port text, dst-port text, kind) for an L4 header at off."""
    name = PROTO_NAMES.get(proto, "proto %d" % proto)
    n = len(pkt)
    if proto in (6, 17) and n >= off + 4:
        sp, dp = struct.unpack_from("!HH", pkt, off)
        # The lower named port is the service: the other end is ephemeral.
        known = [p for p in (sp, dp) if p in PORT_NAMES]
        svc = PORT_NAMES[min(known)] if known else None
        if svc:
            name = svc
        if proto == 6:
            kind = _tcp_kind(pkt, off, svc)
        else:
            kind = _udp_kind(pkt, off + 8, svc) if svc else None
        return name, ":%d > " % sp, ":%d" % dp, kind
    kind = None
    if n > off:
        b0 = pkt[off]
        if proto == 1:
            kind = ICMP_KINDS.get(b0)
        elif proto == 58:
            kind = ICMP6_KINDS.get(b0)
        elif proto == 2:
            kind = IGMP_KINDS.get(b0)
        elif proto == 103:
            kind = PIM_KINDS.get(b0 & 0x0F)
        elif proto == 112:
            kind = "advert" if b0 & 0x0F == 1 else None
        elif proto == 89 and n > off + 1:
            kind = OSPF_KINDS.get(pkt[off + 1])
        elif proto == 88 and n > off + 1:
            kind = EIGRP_KINDS.get(pkt[off + 1])
            # A Hello carrying an acknowledgement number is EIGRP's Ack.
            if kind == "Hello" and n >= off + 16 and struct.unpack_from("!I", pkt, off + 12)[0]:
                kind = "Ack"
        elif proto == 47 and n >= off + 4:
            kind = GRE_INNER.get(struct.unpack_from("!H", pkt, off + 2)[0])
    return name, " > ", "", kind


def _bpdu(pkt, b, family):
    """(protocol, kind) for a spanning-tree BPDU starting at b."""
    if len(pkt) < b + 4:
        return family, None
    version, bpdu_type = pkt[b + 2], pkt[b + 3]
    if bpdu_type == 0x80:
        return family, "TCN"
    if family == "STP":
        name = {2: "RSTP", 3: "MSTP"}.get(version, "STP")
    else:
        name = "Rapid PVST+" if version == 2 else family
    tc = len(pkt) > b + 4 and pkt[b + 4] & 0x01
    return name, ("TC" if tc else None)


def _llc(pkt, off):
    """(protocol, kind) for an 802.3 length frame with an LLC header at off."""
    if len(pkt) < off + 3:
        return "LLC", None
    dsap, ssap = pkt[off], pkt[off + 1]
    if dsap == 0x42 and ssap == 0x42:
        return _bpdu(pkt, off + 3, "STP")
    if dsap == 0xFE and ssap == 0xFE:
        kind = ISIS_KINDS.get(pkt[off + 7] & 0x1F) if len(pkt) > off + 7 else None
        return "IS-IS", kind
    if dsap == 0xAA and ssap == 0xAA and len(pkt) >= off + 8:  # SNAP
        oui = pkt[off + 3:off + 6]
        pid = struct.unpack_from("!H", pkt, off + 6)[0]
        if oui == b"\x00\x00\x0c":             # Cisco
            if pid == 0x010b:
                return _bpdu(pkt, off + 8, "PVST+")
            if pid in CISCO_SNAP:
                return CISCO_SNAP[pid], None
        return "SNAP %04x" % pid, None
    if dsap == 0xE0:
        return "IPX", None
    if dsap == 0xF0:
        return "NetBIOS", None
    return "LLC %02x/%02x" % (dsap, ssap), None


def _ether(eth, pkt, off):
    """(protocol, kind) for a non-IP, non-ARP EtherType."""
    n = len(pkt)
    if eth == 0x8809:
        return (SLOW_PROTOCOLS.get(pkt[off], "Slow protocol") if n > off else "Slow protocol"), None
    name = ETHER_NAMES.get(eth, "EtherType 0x%04x" % eth)
    kind = None
    if n > off + 1:
        if eth in (0x8847, 0x8848) and n >= off + 4:
            kind = "label %d" % (struct.unpack_from("!I", pkt, off)[0] >> 12)
        elif eth == 0x888E:
            kind = EAPOL_KINDS.get(pkt[off + 1])
            if kind == "EAP" and n > off + 4:
                kind = EAP_CODES.get(pkt[off + 4], kind)
        elif eth == 0x8863:
            kind = PPPOE_DISC.get(pkt[off + 1])
        elif eth == 0x8864 and n >= off + 8:
            kind = PPP_PROTOS.get(struct.unpack_from("!H", pkt, off + 6)[0])
        elif eth == 0x8902:
            kind = CFM_KINDS.get(pkt[off + 1])
        elif eth == 0x88F7:
            kind = PTP_KINDS.get(pkt[off] & 0x0F)
        elif eth == 0x8808:
            kind = {1: "PAUSE", 0x0101: "PFC"}.get(struct.unpack_from("!H", pkt, off)[0])
        elif eth == 0x8035 and n >= off + 8:
            kind = {3: "request", 4: "reply"}.get(struct.unpack_from("!H", pkt, off + 6)[0])
    return name, kind


def _mac(raw):
    return ":".join("%02x" % byte for byte in raw)


def describe_packet(pkt, wirelen, _isl=True):
    """Bounded L2/L3 sample for the UI. Fields describe this tap observation only."""
    sample = {"summary": "%dB" % wirelen, "protocol": "Ethernet",
              "src_mac": None, "dst_mac": None}
    try:
        if len(pkt) < 14:
            return sample
        # Cisco ISL (DTP negotiates in it too): a 26-byte header to 01:00:0c:00:00
        # wrapping the real frame. Describe the inner frame, tagged with its VLAN.
        if _isl and pkt[:5] == b"\x01\x00\x0c\x00\x00" and pkt[14:17] == b"\xaa\xaa\x03" and len(pkt) >= 40:
            vlan = struct.unpack_from("!H", pkt, 20)[0] >> 1
            inner = describe_packet(pkt[26:], wirelen, False)
            inner["summary"] = "ISL vlan%d %s" % (vlan, inner["summary"])
            return inner
        sample["dst_mac"] = _mac(pkt[:6])
        sample["src_mac"] = _mac(pkt[6:12])
        eth = struct.unpack_from("!H", pkt, 12)[0]
        off = 14
        vids = []
        while eth in (0x8100, 0x88A8, 0x9100) and len(pkt) >= off + 4 and len(vids) < 2:
            vids.append(struct.unpack_from("!H", pkt, off)[0] & 0x0FFF)  # 802.1Q / QinQ
            eth = struct.unpack_from("!H", pkt, off + 2)[0]
            off += 4
        tag = ("vlan%s " % ".".join(str(v) for v in vids)) if vids else ""
        if eth == 0x0800 and len(pkt) >= off + 20:  # IPv4
            ihl = (pkt[off] & 0x0F) * 4
            if pkt[off] >> 4 != 4 or ihl < 20 or len(pkt) < off + ihl:
                return sample
            proto = pkt[off + 9]
            src = socket.inet_ntop(socket.AF_INET, pkt[off + 12:off + 16])
            dst = socket.inet_ntop(socket.AF_INET, pkt[off + 16:off + 20])
            fragment = struct.unpack_from("!H", pkt, off + 6)[0] & 0x1FFF
            l4off = off + ihl
            if fragment:
                name, sps, dps, kind = PROTO_NAMES.get(proto, "proto %d" % proto), " > ", "", None
            else:
                name, sps, dps, kind = _l4(proto, pkt, l4off)
            sample.update(src_ip=src, dst_ip=dst, ip_version=4, protocol=name)
            if kind:
                sample["kind"] = kind
            sample["summary"] = "%s%s%s%s%s %s%s %dB" % (tag, src, sps, dst, dps, name, (" " + kind) if kind else "", wirelen)
            return sample
        if eth == 0x86DD and len(pkt) >= off + 40:  # IPv6
            if pkt[off] >> 4 != 6:
                return sample
            proto = pkt[off + 6]
            src = socket.inet_ntop(socket.AF_INET6, pkt[off + 8:off + 24])
            dst = socket.inet_ntop(socket.AF_INET6, pkt[off + 24:off + 40])
            l4off = off + 40
            # Walk only the standard fixed-length extension headers present in
            # SNAPLEN. A fragment with nonzero offset has no L4 header here.
            for _ in range(8):
                if proto in (0, 43, 60) and len(pkt) >= l4off + 2:
                    next_proto, words = pkt[l4off], pkt[l4off + 1]
                    size = (words + 1) * 8
                elif proto == 44 and len(pkt) >= l4off + 8:
                    next_proto = pkt[l4off]
                    if struct.unpack_from("!H", pkt, l4off + 2)[0] & 0xFFF8:
                        break
                    size = 8
                elif proto == 51 and len(pkt) >= l4off + 2:
                    next_proto, words = pkt[l4off], pkt[l4off + 1]
                    size = (words + 2) * 4
                else:
                    break
                if len(pkt) < l4off + size:
                    break
                proto, l4off = next_proto, l4off + size
            name, sps, dps, kind = _l4(proto, pkt, l4off)
            sample.update(src_ip=src, dst_ip=dst, ip_version=6, protocol=name)
            if kind:
                sample["kind"] = kind
            sample["summary"] = "%s%s%s%s%s %s%s %dB" % (tag, src, sps, dst, dps, name, (" " + kind) if kind else "", wirelen)
            return sample
        if eth == 0x0806:                            # ARP
            sample["protocol"] = "ARP"
            if len(pkt) >= off + 28:
                htype, ptype, hlen, plen, op = struct.unpack_from("!HHBBH", pkt, off)
                if htype == 1 and ptype == 0x0800 and hlen == 6 and plen == 4:
                    spa = socket.inet_ntop(socket.AF_INET, pkt[off + 14:off + 18])
                    tpa = socket.inet_ntop(socket.AF_INET, pkt[off + 24:off + 28])
                    sample.update(arp_sender_ip=spa, arp_target_ip=tpa,
                                  arp_sender_mac=_mac(pkt[off + 8:off + 14]),
                                  arp_target_mac=_mac(pkt[off + 18:off + 24]))
                    kind = {1: "request", 2: "reply"}.get(op)
                    if kind:
                        sample["kind"] = kind
                    sample["summary"] = "%sARP%s %s > %s %dB" % (tag, (" " + kind) if kind else "", spa, tpa, wirelen)
                    return sample
            sample["summary"] = tag + "ARP %dB" % wirelen
            return sample
        if eth < 0x0600:                             # 802.3 length + LLC
            name, kind = _llc(pkt, off)
        else:
            name, kind = _ether(eth, pkt, off)
        sample["protocol"] = name
        if kind:
            sample["kind"] = kind
        bpdu = " BPDU" if name in ("STP", "RSTP", "MSTP", "PVST+", "Rapid PVST+") else ""
        sample["summary"] = "%s%s%s%s %dB" % (tag, name, bpdu, (" " + kind) if kind else "", wirelen)
        return sample
    except Exception:
        return sample




def summarize(pkt, wirelen):
    return describe_packet(pkt, wirelen)["summary"]


# ---- main --------------------------------------------------------------------

class Watcher:
    def __init__(self, watch_id):
        self.watch_id = watch_id
        conf_path = os.path.join(LW_DIR, watch_id + ".conf.json")
        with open(conf_path) as f:
            conf = json.load(f)
        self.conf_path = conf_path
        self.snap_path = os.path.join(LW_DIR, watch_id + ".json")
        self.hb_path = os.path.join(LW_DIR, watch_id + ".hb")
        self.hb_timeout = int(conf.get("hb_timeout", 180))
        # snapshot cadence (s); also drives the per-key summary rate-limit
        self.interval = max(0.2, min(2.0, float(conf.get("interval", 1.0))))
        self.interfaces = list(conf["interfaces"])
        self.filters = list(conf["filters"])  # [{"id","expr"}]
        self.sel = selectors.DefaultSelector()
        # sockmap[(iface, fid)] = {"sock", "expr", "buf"} — one AF_PACKET socket per
        # (tap x filter). Keyed so a SIGHUP reload can DIFF the desired set against
        # the live set: keep survivors (stats preserved), close removed, open new.
        self.sockmap = {}
        # stats[(iface, fid, dir)] = {"total","win","last_ts","last","last_sum_ts"}
        self.stats = {}
        self.start_ts = time.time()
        self.stopping = False
        # Set by the SIGHUP handler; drained in the run loop (signal-safe). Tier 2:
        # brokerd rewrites conf.json then SIGHUPs us for an in-place filter add/
        # remove/edit, so surviving (tap x filter) counters never reset.
        self.reload_pending = False

    def _compile_progs(self, filters):
        """Compile each distinct filter expression to (n, cBPF-buffer), tolerating
        a bad expr (broker-built, so this is defensive). Returns {expr: (n, buf)}.
        The kernel COPIES the program at SO_ATTACH_FILTER time, so one buffer can
        back sockets on many taps."""
        compiled = {}
        for f in filters:
            expr = f["expr"]
            if expr in compiled:
                continue
            try:
                n, raw = compile_bpf(expr)
                compiled[expr] = (n, ctypes.create_string_buffer(raw, len(raw)))
            except Exception as e:
                log("compile failed for %r: %s" % (expr, e))
        return compiled

    def _open_pair(self, iface, fid, expr, prog):
        """Open + register one (tap x filter) socket. prog = (n, buf). Idempotent:
        a pair already in sockmap is left untouched (its stats survive)."""
        if (iface, fid) in self.sockmap:
            return False
        n, buf = prog
        try:
            s = open_filtered_socket(iface, n, buf)
        except OSError as e:
            log("skip %s/%s: %s" % (iface, fid, e))
            return False
        self.sel.register(s, selectors.EVENT_READ, (iface, fid))
        self.sockmap[(iface, fid)] = {"sock": s, "expr": expr, "buf": buf}
        return True

    def _drop_stats(self, iface, fid):
        for d in ("in", "out"):
            self.stats.pop((iface, fid, d), None)

    def setup(self):
        compiled = self._compile_progs(self.filters)
        opened = 0
        for iface in self.interfaces:
            for f in self.filters:
                prog = compiled.get(f["expr"])
                if prog and self._open_pair(iface, f["id"], f["expr"], prog):
                    opened += 1
        log("watch %s: %d sockets (%d ifaces x %d filters)"
            % (self.watch_id, opened, len(self.interfaces), len(self.filters)))
        return opened

    def reload(self):
        """SIGHUP handler body: re-read conf.json and DIFF the socket set against
        the live one. Surviving (tap x filter) pairs whose expr is UNCHANGED keep
        their socket AND their counters; pairs that were removed (or whose expr
        changed) are closed and their stats dropped; genuinely-new pairs are
        opened fresh. This is what makes a live filter add/remove non-destructive
        to the counters the user is watching."""
        try:
            with open(self.conf_path) as f:
                conf = json.load(f)
        except (OSError, ValueError) as e:
            log("reload: bad conf, keeping current set: %s" % e)
            return
        new_ifaces = list(conf.get("interfaces", []))
        new_filters = list(conf.get("filters", []))   # [{"id","expr"}]
        if not new_ifaces or not new_filters:
            log("reload: empty interfaces/filters, ignoring")
            return
        compiled = self._compile_progs(new_filters)
        # desired[(iface, fid)] = expr — only for exprs that compiled.
        desired = {}
        for iface in new_ifaces:
            for f in new_filters:
                if f["expr"] in compiled:
                    desired[(iface, f["id"])] = f["expr"]
        # Close removed or expr-changed pairs (drop their stats).
        removed = 0
        for key, ent in list(self.sockmap.items()):
            want = desired.get(key)
            if want is None or want != ent["expr"]:
                self.drop_socket(ent["sock"])
                self._drop_stats(key[0], key[1])
                removed += 1
        # Open new (or expr-changed) pairs; survivors are skipped by _open_pair.
        added = 0
        for (iface, fid), expr in desired.items():
            if self._open_pair(iface, fid, expr, compiled[expr]):
                added += 1
        self.interfaces = new_ifaces
        self.filters = [f for f in new_filters if f["expr"] in compiled]
        try:
            self.interval = max(0.2, min(2.0, float(conf.get("interval", self.interval))))
        except (TypeError, ValueError):
            pass
        log("watch %s reloaded: +%d -%d sockets, %d live (%d ifaces x %d filters)"
            % (self.watch_id, added, removed, len(self.sockmap),
               len(self.interfaces), len(self.filters)))

    def _key(self, iface, fid, direction):
        k = (iface, fid, direction)
        st = self.stats.get(k)
        if st is None:
            st = self.stats[k] = {"total": 0, "win": 0, "last_ts": 0.0,
                                  "last": "", "sample": None, "sample_ts": 0.0,
                                  "last_sum_ts": 0.0}
        return st

    def drain(self, sock, iface, fid):
        now = time.time()
        for _ in range(MAX_READS_PER_TICK):
            try:
                pkt, addr = sock.recvfrom(SNAPLEN)
            except BlockingIOError:
                return True
            except OSError as e:
                # Only a genuinely removed tap ends the watch. ENETDOWN here is a
                # one-shot pending error (the tap was admin-down at bind time, or a
                # link flap) that recvfrom delivers once and clears — consume it and
                # keep watching, else a single blip kills the whole watch and the UI
                # shows "Watch ended (engine side)".
                if e.errno in (errno.ENODEV, errno.ENXIO):
                    return False                   # tap gone
                return True
            # inverted on host taps: PACKET_OUTGOING = bridge -> guest ("in")
            direction = "in" if addr[2] == PACKET_OUTGOING else "out"
            st = self._key(iface, fid, direction)
            st["total"] += 1
            st["win"] += 1
            st["last_ts"] = now
            if now - st["last_sum_ts"] >= self.interval:
                st["last_sum_ts"] = now
                st["sample"] = describe_packet(pkt, len(pkt))
                st["last"] = st["sample"]["summary"]
                st["sample_ts"] = now
        return True

    def drop_socket(self, sock):
        try:
            self.sel.unregister(sock)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
        for key, ent in list(self.sockmap.items()):
            if ent["sock"] is sock:
                del self.sockmap[key]
                break

    def write_snapshot(self, dt):
        taps = {}
        for (iface, fid, direction), st in self.stats.items():
            ent = taps.setdefault(iface, {}).setdefault(fid, {})
            ent[direction] = {
                "pps": round(st["win"] / dt, 1) if dt > 0 else 0,
                "total": st["total"],
                "last_ts": round(st["last_ts"], 1),
                "last": st["last"],
                "sample": st["sample"],
                "sample_ts": round(st["sample_ts"], 3),
            }
            st["win"] = 0
        snap = {"ts": round(time.time(), 1), "watch_id": self.watch_id,
                "filters": [f["id"] for f in self.filters], "taps": taps}
        tmp = self.snap_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(snap, f, separators=(",", ":"))
        os.chmod(tmp, 0o644)
        os.replace(tmp, self.snap_path)

    def heartbeat_stale(self):
        try:
            hb = os.stat(self.hb_path).st_mtime
        except OSError:
            hb = self.start_ts
        return time.time() - hb > self.hb_timeout

    def cleanup(self):
        for ent in list(self.sockmap.values()):
            self.drop_socket(ent["sock"])
        # Only remove the snapshot/sidecar on a genuine SELF-exit (all taps gone /
        # heartbeat stale). On SIGTERM we are being stopped OR re-armed by brokerd
        # (linkwatch_start = stop+respawn): deleting the snapshot here opens a gap
        # where GET sees active:false and the client ends the watch ("Watch ended")
        # on every add/delete. A real stop owns deletion itself (brokerd _lw_unlink
        # + pnq-linkwatch stop); a re-arm's new watcher just overwrites the snapshot.
        if self.stopping:
            return
        links_sidecar = os.path.join(LW_DIR, self.watch_id + ".links.json")
        for p in (self.snap_path, self.conf_path, self.hb_path, links_sidecar):
            try:
                os.unlink(p)
            except OSError:
                pass

    def run(self):
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "stopping", True))
        signal.signal(signal.SIGHUP, lambda *_: setattr(self, "reload_pending", True))
        if self.setup() == 0:
            log("no sockets opened, exiting")
            self.cleanup()
            return 1
        last_tick = time.time()
        while not self.stopping:
            if self.reload_pending:
                self.reload_pending = False
                self.reload()
            for key, _ in self.sel.select(timeout=self.interval):
                sock = key.fileobj
                iface, fid = key.data
                if not self.drain(sock, iface, fid):
                    log("tap %s gone, dropping" % iface)
                    self.drop_socket(sock)
            now = time.time()
            if now - last_tick >= self.interval:
                self.write_snapshot(now - last_tick)
                last_tick = now
                if not self.sockmap:
                    log("all taps gone, exiting")
                    break
                if self.heartbeat_stale():
                    log("heartbeat stale (> %ds), exiting" % self.hb_timeout)
                    break
        self.cleanup()
        log("watch %s done" % self.watch_id)
        return 0


def main():
    if len(sys.argv) != 2:
        log("usage: azamlabs-linkwatchd.py <watch_id>")
        return 2
    return Watcher(sys.argv[1]).run()


if __name__ == "__main__":
    sys.exit(main())

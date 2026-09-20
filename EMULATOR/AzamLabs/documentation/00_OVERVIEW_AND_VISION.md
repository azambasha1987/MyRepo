# 🌌 AzamLabs: Overview, Vision & Social Media Primer

> **"Building the Future of Network, Cloud & Cybersecurity Emulation."**

---

## 🚀 The Vision

For over a decade, network engineers, cybersecurity analysts, and cloud architects have relied on legacy emulators like EVE-NG, PNETLab, and GNS3. While these tools revolutionized IT certification prep, they have accumulated severe technical debt:
- **Massive Resource Bloat**: Legacy stacks require Apache, PHP-FPM, heavy MySQL databases, and background wrappers that consume 1.5 GB to 2 GB of RAM before launching a single router.
- **Artificial Limits**: Recent updates (such as EVE-NG v7 in June 2026) terminated free community editions, imposing a strict 7-node cap.
- **Physical LAN Hazards**: Virtual routers routinely leak rogue DHCP, ARP, and BPDU packets, corrupting real office and home Wi-Fi networks.
- **Format Incompatibility**: Labs created in GNS3 don't work in EVE-NG; Containerlab labs don't open in CML; engineers are forced to rebuild topologies from scratch.

**AzamLabs was born to fix this once and for all.**

AzamLabs is a **100% clean-room, futuristic network emulator** engineered specifically for **Ubuntu 26.04 LTS ("Resolute")** and **Docker**. It runs at near-zero idle overhead (~75 MB RAM), provides universal cross-platform compatibility, and integrates cutting-edge cybersecurity and multi-cloud capabilities.

---

## 📊 How AzamLabs Compares to Legacy Platforms

| Feature | Legacy EVE-NG (v7) | PNETLab (v8) | Containerlab | GNS3 (v3.1 Beta) | **AzamLabs Core** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Clean-Room Codebase** | ❌ Legacy | ❌ Legacy | ✅ Clean Go | ❌ Legacy Python | **✅ 100% Original Clean-Room** |
| **Free Node Limit** | ❌ **Capped at 7 Nodes** | ✅ Unlimited | ✅ Unlimited | ✅ Unlimited | **✅ Unlimited (1024+ Nodes)** |
| **Idle System RAM** | 1,500 MB | 1,650 MB | ~50 MB (CLI only) | 800 MB | **~75 MB (FastAPI + uvloop)** |
| **100:1 Memory Sharing** | ⚠️ Basic | ⚠️ Manual Script | ❌ N/A | ❌ N/A | **✅ Automated KSM + IOL Shim** |
| **Universal Lab Import** | ❌ UNL only | ⚠️ Partial UNL | ❌ CLAB only | ❌ GNS3 only | **✅ CLAB + CML + EVE + GNS3** |
| **Live Web Wireshark** | ⚠️ Pro Only | ❌ External Pipe | ❌ CLI only | ⚠️ v3.1 Beta | **✅ In-Browser Zero-Client** |
| **Cyber Range Simulator** | ❌ None | ❌ None | ❌ None | ❌ None | **✅ 1-Click Attack Generator** |
| **Cloud VPC Peering** | ❌ None | ❌ None | ❌ None | ❌ None | **✅ Direct AWS/Azure WireGuard** |
| **AI Autonomous Healer** | ❌ None | ❌ None | ❌ None | ⚠️ Copilot Beta | **✅ 1-Click Root-Cause Fixer** |
| **OLED Pure Dark Canvas** | ❌ Dated UI | ❌ Dated UI | ⚠️ Web Graph | ⚠️ Beta Web UI | **✅ 60 FPS GPU-Accelerated Studio** |

---

## 📢 Social Media Shareable Posts (Ready to Copy & Paste)

### 💼 LinkedIn Post Template
```
🚀 Exciting Project Reveal: Introducing AzamLabs — The Next-Gen Universal Network, Cloud & Cybersecurity Emulator!

If you've ever studied for CCNA, CCNP, CCIE, or practiced Cloud & Cyber Range labs, you know the frustration:
- Emulators eating 2GB of RAM before you even boot a router.
- Labs trapped in one format (EVE-NG vs GNS3 vs Containerlab vs CML).
- Virtual DHCP servers accidentally leaking into your home or office Wi-Fi.

We decided to build the solution from scratch: AzamLabs!
Built natively on Ubuntu 26.04 LTS & 100% Docker-proof:

✨ What makes AzamLabs different?
1. ⚡ 95% Lighter: Base engine idles at just ~75 MB RAM (FastAPI + uvloop).
2. 🔄 Universal Compatibility: Open ANY lab — .clab.yml, .yaml (CML2), .unl (EVE-NG), or .gns3 with zero conversion hassle!
3. 💾 100:1 Density: Run 100 Cisco routers on the RAM and CPU of just 1 router using Proactive KSM and custom idle-shimming.
4. 🛡️ Built-in Cyber Range: 1-click launch SYN floods, ARP poisoning, and port scans against Kali and Suricata IDS nodes with live threat radar on the canvas.
5. 🔍 In-Browser Wireshark: Click any virtual wire to inspect decoded packet headers directly in the web browser.
6. 🎨 OLED Pure Dark Glassmorphic Studio: 60 FPS animated traffic flows and glowing photon particles.

Check out our open architecture and documentation here: [Insert GitHub Repo Link]

#Networking #Cisco #Cybersecurity #CloudComputing #Containerlab #DevNet #CCIE #OpenSource #Ubuntu26
```

---

### 🐦 Twitter / X Thread Template
```
1/5 🌐 Tired of network emulators that eat 2GB of RAM just to idle? We built something completely new: AzamLabs — the universal, next-gen network & cloud security emulator for Ubuntu 26.04 & Docker. 🧵👇

2/5 ⚡ 95% Lower Overhead: Built with async Python 3.12 (FastAPI + uvloop) & SQLite WAL. Base engine uses ~75 MB RAM instead of 1.6 GB. Every drop of CPU and RAM is reserved for your actual routers and firewalls!

3/5 🔄 Universal Lab Ingestion: Got labs from @Containerlab (.clab.yml), Cisco CML (.yaml), EVE-NG (.unl), or GNS3 (.gns3)? Drag and drop them right onto the canvas. AzamLabs auto-detects and converts them instantly!

4/5 🛡️ Cyber Range + Cloud: Launch Kali, Suricata, and Zeek nodes. Test firewall rules with 1-click attack injections (SYN floods, ARP poisoning). Connect your lab directly to AWS Transit Gateway over WireGuard!

5/5 🎨 Futuristic OLED Pure Dark Studio: 60 FPS GPU-accelerated canvas with live glowing traffic particles, multi-tab xterm.js terminals, and in-browser Wireshark. Check out the documentation: [Link] 🚀
```

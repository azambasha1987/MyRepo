# 07. High-Speed Image & Project Uploads Guide

An in-depth analysis and operational guide for accelerating image (`.qcow2`, `.vmdk`, `.iso`, `.bin`) and portable project archive (`.gns3project`) transfers to **AzamGNS3**.

---

## 1. Why Uploads Were Slow: Root Cause Analysis

Network emulation appliances (Cisco IOS-XRv 9000, Arista vEOS, Juniper vQFX, Windows Server) range from **2 GB to 20 GB** in size. Uploading these files through standard web emulation interfaces often suffers from three major bottlenecks:

### Bottleneck 1: Browser-Side Client-Side Pre-Hashing
When using the Web UI **Image Manager $\rightarrow$ Add Image** dialog:
- The browser calculates an MD5 checksum of the entire file in JavaScript using `SparkMD5` within a Web Worker *before the upload starts*.
- For an 8 GB image on a laptop, computing an MD5 hash in single-threaded JavaScript takes **2 to 5 minutes** ("Reading file: 12% ... 48% ... 100%").
- Users perceive this as a stalled or extremely sluggish upload, even though no data has left the machine yet.

### Bottleneck 2: Backend Unbuffered I/O & Thread-Pool Thrashing
- By default, Python ASGI servers (Starlette / Uvicorn) stream HTTP body data in small TCP chunks (typically 16 KB to 64 KB).
- The server framework piped each 64 KB chunk directly into `aiofiles.open(...)`.
- `aiofiles` handles asynchronous writes by offloading each write call to a thread executor (`loop.run_in_executor`).
- **The Mathematical Penalty**:
  $$\frac{8\,\text{GB}}{64\,\text{KB}} = 131{,}072\,\text{thread context switches}$$
- Scheduling 130,000+ thread futures starves the Python asyncio event loop, delays TCP socket reads, and forces the OS to shrink the TCP receive window. Network throughput collapses from gigabit speed to a crawl.

### Bottleneck 3: Host & VM TCP Socket Buffer Caps
Standard Ubuntu Linux defaults limit TCP socket memory buffers to `6 MB`, which chokes TCP sliding window scalability on high-throughput virtual bridges and Gigabit LAN connections.

---

## 2. AzamGNS3 Speed Optimizations Applied

We implemented a three-tier optimization across the kernel, backend, and frontend:

### 1. 4 MiB Contiguous Streaming Write Engine
In `gns3server/utils/images.py`, `projects.py`, and `base_manager.py`:
- Incoming network stream chunks are accumulated into a memory buffer (`bytearray`) up to **4 MiB**.
- The entire 4 MiB block is dispatched to disk in a single aligned write.
- **Result**: Thread executor dispatches drop from **131,072** down to **2,048** (a **98.4% reduction**). The event loop remains responsive, and TCP socket draining runs at full wire speed.

### 2. 32 MB High-Bandwidth TCP Kernel Tuning
Configured in `/etc/sysctl.d/99-azamgns3-perf.conf` on the VM:
```ini
# Virtual interface & socket memory
net.core.rmem_max = 33554432
net.core.wmem_max = 33554432
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.core.netdev_max_backlog = 100000

# High-bandwidth TCP autotuning up to 32MB
net.ipv4.tcp_rmem = 4096 87380 33554432
net.ipv4.tcp_wmem = 4096 65536 33554432
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
```

### 3. Optimized Web Worker Slices & Throttled IPC
In `gns3-web-ui`:
- Web worker slice chunking expanded to 16 MiB.
- Progress updates throttled to avoid flooding the Angular UI event loop.

---

## 3. High-Speed Upload Methods Compared

| Method | Speed | Best Used For | Notes |
| :--- | :--- | :--- | :--- |
| **Direct SCP / SFTP** *(Recommended)* | **100 – 350+ MB/s** (Wire speed) | Large QEMU images (2 GB – 30 GB), bulk libraries | Zero browser overhead. Auto-discovered by AzamGNS3 watchdog. |
| **Template Wizard Upload** | **60 – 110 MB/s** | Single appliance images | Bypasses client-side JS pre-hashing dialog. |
| **Web UI Image Manager** | **50 – 90 MB/s** | Standard uploads with catalog match | Now accelerated with 4MB stream buffering. |

---

## 4. The Fastest Method: Direct Wire-Speed SCP / SFTP Copy

AzamGNS3 features a built-in **Image Reconciliation Service** powered by Linux `inotify` and Python `watchdog`. Any image placed directly into the storage directory is **automatically detected, verified, and registered into the database** without touching the browser.

### Step 1: Copy Image via SCP (from Windows PowerShell)
Open PowerShell on your laptop and transfer directly into the QEMU image directory:

```powershell
# Syntax: scp <local-file> root@<VM-IP>:/opt/gns3/images/QEMU/
scp "C:\Path\To\vios-adventerprisek9.qcow2" root@192.168.1.28:/opt/gns3/images/QEMU/
```

> [!TIP]
> **GUI Transfer Tool**: You can also use **WinSCP** or **FileZilla** (SFTP protocol) to connect to `192.168.1.28` (User: `root`, Port: `22`) and drag-and-drop entire folders of images directly into `/opt/gns3/images/QEMU/`.

### Step 2: Set Proper File Ownership
Ensure the `azam` service user owns the transferred file:

```bash
# On the Ubuntu VM:
sudo chown -R azam:azam /opt/gns3/images/QEMU/
```

### Step 3: Instant Recognition in AzamGNS3
Within seconds, the Image Reconciliation daemon detects the file. Open the AzamGNS3 Web UI:
- Navigate to **Preferences $\rightarrow$ QEMU VM Templates $\rightarrow$ New**.
- Choose **"Use an existing image"** — your transferred image will appear in the dropdown list ready for instant deployment!

---

## 5. Fast Project Uploads & Restores

For large `.gns3project` archives:
1. **Via Web UI**:
   - In the Projects dashboard, click **Import Project**.
   - With our 4 MiB buffer patch, upload times are cut significantly as socket draining and disk unzipping run without event loop stalls.
2. **Direct CLI / SCP Project Deployment (For Huge Topologies)**:
   - Copy the unzipped project folder directly into `/opt/gns3/projects/<project-id>/`.
   - Ensure permissions: `sudo chown -R azam:azam /opt/gns3/projects/`.

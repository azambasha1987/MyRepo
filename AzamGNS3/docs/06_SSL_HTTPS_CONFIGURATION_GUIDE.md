# 06. SSL / HTTPS Configuration Guide

A step-by-step operational guide for generating, configuring, and applying SSL/TLS certificates in **AzamGNS3** to secure Web UI sessions, xterm.js consoles, and FastMCP API communications.

---

## 1. Overview & Validation Rules

In AzamGNS3 (built on GNS3 3.1 architecture with Pydantic v2 schemas), server settings are strictly validated before being committed to disk. 

### Why the Validation Error Occurs
When toggling **"Enable SSL"** in the Web UI without providing the certificate and key paths, the Pydantic schema validator (`gns3server/schemas/config.py`) raises:

```text
Invalid server settings: 1 validation error for ServerConfig
Server
  Value error, SSL is enabled but certfile is not configured [type=value_error]
```

### Strict Schema Requirements
1. **Atomic Configuration**: If `enable_ssl` is set to `True`, both `certfile` and `certkey` must be provided simultaneously.
2. **File Existence Validation**: The schema types `certfile` and `certkey` as `pydantic.FilePath`. This means **the files must physically exist on the server filesystem** at the time of validation, or the server will reject the change.
3. **Daemon Read Access**: The files must be readable by the `azam` service user under systemd sandbox isolation (`ProtectSystem=strict`).

---

## 2. Directory Architecture & Permissions

To comply with systemd sandboxing rules defined in `/etc/systemd/system/azamgns3.service`, the dedicated SSL directory must reside under `/etc/azamgns3/` (which is configured in `ReadWritePaths`).

| Resource | Path | Recommended Permissions | Owner |
| :--- | :--- | :--- | :--- |
| **SSL Directory** | `/etc/azamgns3/ssl/` | `0700` (`drwx------`) | `azam:azam` |
| **Private Key** | `/etc/azamgns3/ssl/server.key` | `0600` (`-rw-------`) | `azam:azam` |
| **Certificate** | `/etc/azamgns3/ssl/server.crt` | `0644` (`-rw-r--r--`) | `azam:azam` |

---

## 3. Step-by-Step Implementation

### Step 1: Create the SSL Directory
SSH into the AzamGNS3 host (or open a terminal on the VM) and create the SSL storage directory:

```bash
sudo mkdir -p /etc/azamgns3/ssl
```

---

### Step 2: Generate the SSL Certificate and Private Key

#### Option A: Quick Self-Signed Certificate with SAN (Recommended for Lab / IP Access)
Modern web browsers (Chrome, Edge, Firefox) reject certificates without **Subject Alternative Name (SAN)** extensions. Use OpenSSL with `-addext` to include your server IP (e.g., `192.168.1.28`) and `localhost`:

```bash
# Replace 192.168.1.28 with your actual server IP if different
sudo openssl req -x509 -nodes -days 730 -newkey rsa:2048 \
  -keyout /etc/azamgns3/ssl/server.key \
  -out /etc/azamgns3/ssl/server.crt \
  -subj "/C=US/ST=Lab/L=Lab/O=AzamGNS3/CN=192.168.1.28" \
  -addext "subjectAltName=IP:192.168.1.28,IP:127.0.0.1,DNS:localhost"
```

> [!TIP]
> **OpenSSL 1.1.1+ and 3.x Compatibility**: The `-addext` parameter generates the X509v3 SAN extension in a single command, ensuring modern browser compatibility without requiring a separate configuration file.

#### Option B: Multi-SAN OpenSSL Config (For Domain Names & Multiple IPs)
If you access AzamGNS3 via a domain name (e.g. `gns3.lab.local`), create an OpenSSL configuration file:

```bash
cat << 'EOF' | sudo tee /etc/azamgns3/ssl/openssl.cnf
[req]
default_bits        = 2048
prompt              = no
default_md          = sha256
distinguished_name  = req_distinguished_name
x509_extensions     = v3_req

[req_distinguished_name]
C  = US
ST = State
L  = City
O  = AzamGNS3 Emulation
CN = azamgns3.local

[v3_req]
basicConstraints    = CA:FALSE
keyUsage            = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage    = serverAuth
subjectAltName      = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = azamgns3.local
IP.1  = 127.0.0.1
IP.2  = 192.168.1.28
EOF

sudo openssl req -x509 -nodes -days 730 \
  -config /etc/azamgns3/ssl/openssl.cnf \
  -keyout /etc/azamgns3/ssl/server.key \
  -out /etc/azamgns3/ssl/server.crt
```

---

### Step 3: Set Ownership and Access Permissions
AzamGNS3 executes under the unprivileged service account `azam:azam`. Set the file ownership and restrictive permissions:

```bash
# Grant ownership to azam user and group
sudo chown -R azam:azam /etc/azamgns3/ssl

# Lock down private key permissions
sudo chmod 700 /etc/azamgns3/ssl
sudo chmod 600 /etc/azamgns3/ssl/server.key
sudo chmod 644 /etc/azamgns3/ssl/server.crt
```

Verify that the files were created and permissions are correct:
```bash
ls -la /etc/azamgns3/ssl/
```
*Expected output:*
```text
drwx------ 2 azam azam 4096 Oct  9 18:40 .
-rw-r--r-- 1 azam azam 1280 Oct  9 18:40 server.crt
-rw------- 1 azam azam 1704 Oct  9 18:40 server.key
```

---

### Step 4: Apply the SSL Configuration

You can apply the configuration either via the **Web UI** or directly in the **Configuration File**.

#### Method 1: Via the Web UI (Zero Downtime Config Edit)
1. Navigate to the AzamGNS3 Web UI in your browser (`http://192.168.1.28:3080/`).
2. Log in (Default credentials: `admin` / `admin`).
3. Click the **Gear icon (Settings)** in the navigation bar.
4. Select **Server Settings**.
5. Enter the following values:
   - **Certificate file (`certfile`)**: `/etc/azamgns3/ssl/server.crt`
   - **Certificate key (`certkey`)**: `/etc/azamgns3/ssl/server.key`
   - **Enable SSL (`enable_ssl`)**: Check / Toggle to **ON**
6. Click **Save Changes**.
   > [!NOTE]
   > The Web UI will now successfully validate and save the settings without error because both files exist and are readable on disk.
7. Restart the service as instructed in Step 5.

#### Method 2: Via Configuration File (Direct CLI)
Alternatively, update `/etc/azamgns3/gns3_server.conf` directly using `sed` or an editor:

```bash
# Ensure [Server] section has SSL enabled
sudo sed -i '/\[Server\]/a enable_ssl = True\ncertfile = /etc/azamgns3/ssl/server.crt\ncertkey = /etc/azamgns3/ssl/server.key' /etc/azamgns3/gns3_server.conf
```

Or verify `/etc/azamgns3/gns3_server.conf` contains:

```ini
[Server]
host = 0.0.0.0
port = 3080
enable_ssl = True
certfile = /etc/azamgns3/ssl/server.crt
certkey = /etc/azamgns3/ssl/server.key
images_path = /opt/gns3/images
projects_path = /opt/gns3/projects
...
```

---

### Step 5: Restart the AzamGNS3 Service

Because SSL settings bind Uvicorn listeners upon daemon initialization, restart the service to activate HTTPS:

```bash
sudo systemctl restart azamgns3
```

Check the service status and ensure Uvicorn has bound to HTTPS:

```bash
sudo systemctl status azamgns3
```

Inspect the logs to verify SSL initialization:

```bash
sudo journalctl -u azamgns3 -n 30 --no-pager
```

*Look for log entries confirming SSL mode:*
```text
INFO:     SSL is enabled
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on https://0.0.0.0:3080 (Press CTRL+C to quit)
```

---

### Step 6: Accessing AzamGNS3 via HTTPS

Open your browser and navigate to the HTTPS endpoint:

```text
https://192.168.1.28:3080/
```

#### Handling the Self-Signed Certificate Warning:
Because self-signed certificates are not signed by a public Certificate Authority (CA), your browser will display a privacy warning on first visit:
- **Google Chrome / Microsoft Edge**: Click **Advanced** $\rightarrow$ Click **"Proceed to 192.168.1.28 (unsafe)"** (or click anywhere on the page and type `thisisunsafe`).
- **Mozilla Firefox**: Click **Advanced** $\rightarrow$ Click **"Accept the Risk and Continue"**.
- **Safari**: Click **Show Certificate** $\rightarrow$ Click **"Continue"**.

All subsequent traffic, including terminal WebSockets (`wss://`), project APIs, and FastMCP tools, is now end-to-end encrypted with TLS 1.3.

---

## 4. Emergency Rollback (Recovery Procedure)

If an invalid certificate path or corrupt key prevents the server from starting, you can revert back to plain HTTP within seconds:

```bash
# 1. Edit the configuration file to disable SSL
sudo sed -i 's/enable_ssl = True/enable_ssl = False/' /etc/azamgns3/gns3_server.conf

# 2. Restart the daemon
sudo systemctl restart azamgns3

# 3. Access the server over HTTP
# http://192.168.1.28:3080/
```

---

## 5. Summary Reference Cheat-Sheet

```bash
# 1. Create directory
sudo mkdir -p /etc/azamgns3/ssl

# 2. Generate Key & Cert with SAN
sudo openssl req -x509 -nodes -days 730 -newkey rsa:2048 \
  -keyout /etc/azamgns3/ssl/server.key \
  -out /etc/azamgns3/ssl/server.crt \
  -subj "/C=US/ST=Lab/L=Lab/O=AzamGNS3/CN=192.168.1.28" \
  -addext "subjectAltName=IP:192.168.1.28,IP:127.0.0.1,DNS:localhost"

# 3. Fix permissions for azam user
sudo chown -R azam:azam /etc/azamgns3/ssl
sudo chmod 700 /etc/azamgns3/ssl
sudo chmod 600 /etc/azamgns3/ssl/server.key
sudo chmod 644 /etc/azamgns3/ssl/server.crt

# 4. Configure in /etc/azamgns3/gns3_server.conf
# [Server]
# enable_ssl = True
# certfile = /etc/azamgns3/ssl/server.crt
# certkey = /etc/azamgns3/ssl/server.key

# 5. Restart daemon
sudo systemctl restart azamgns3

# 6. Connect via https://<IP>:3080/
```

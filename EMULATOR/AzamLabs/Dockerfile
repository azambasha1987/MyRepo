# ==============================================================================
# AzamLabs Universal Emulation Platform — Production Multi-Stage Dockerfile
# Optimized for Ultra-Lightweight Footprint (<150MB) & 100:1 KSM Deduplication
# ==============================================================================

# Stage 1: Native C Shim Builder
FROM python:3.12-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY shim/ /build/shim/
RUN make -C /build/shim/

# Stage 2: Production Minimal Runtime
FROM python:3.12-slim

LABEL maintainer="AzamLabs Engineering Team"
LABEL description="AzamLabs Universal Network, Cloud & Cybersecurity Emulation Platform"
LABEL version="1.0.0"

# Install essential dataplane and networking runtime utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    iptables \
    nftables \
    tcpdump \
    bridge-utils \
    telnet \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Setup system paths
WORKDIR /app
RUN mkdir -p /var/lib/azamlabs /opt/azamlabs/lib /opt/azamlabs/bin

# Copy compiled CPU idle governor shim
COPY --from=builder /build/shim/azam-iol-shim.so /opt/azamlabs/lib/azam-iol-shim.so

# Copy backend Python codebase and frontend static assets
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/

# Install backend dependencies and register 'azam' CLI globally
RUN pip install --no-cache-dir /app/backend

# Runtime Environment Variables
ENV PYTHONUNBUFFERED=1 \
    AZAM_APP_NAME="AzamLabs" \
    AZAM_ENVIRONMENT="production" \
    AZAM_DATABASE_PATH="/var/lib/azamlabs/azamlabs.db" \
    AZAM_DATA_DIR="/var/lib/azamlabs" \
    AZAM_IOL_SHIM_PATH="/opt/azamlabs/lib/azam-iol-shim.so"

# Expose Studio API / Web UI / MCP port and Serial Console range
EXPOSE 8000
EXPOSE 30000-30100

# Health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Launch production server
CMD ["uvicorn", "azamlabs.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

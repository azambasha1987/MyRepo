"""
AzamLabs Configuration Module
Manages runtime configuration, storage paths, networking parameters, and KSM tunings.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # Platform Information
    APP_NAME: str = "AzamLabs Core"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("AZAM_ENV", "development")
    DEBUG: bool = os.getenv("AZAM_DEBUG", "false").lower() == "true"

    # Server Bindings
    HOST: str = os.getenv("AZAM_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("AZAM_PORT", "8000"))

    # Base System Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = Path(os.getenv("AZAM_DATA_DIR", str(BASE_DIR / "data")))
    LABS_DIR: Path = Path(os.getenv("AZAM_LABS_DIR", str(BASE_DIR / "labs")))
    IMAGES_DIR: Path = Path(os.getenv("AZAM_IMAGES_DIR", str(BASE_DIR / "images")))
    STATIC_DIR: Path = Path(os.getenv("AZAM_STATIC_DIR", str(BASE_DIR / "frontend")))
    DATABASE_PATH: Path = DATA_DIR / "azamlabs.db"

    # Sub-Image Paths
    QEMU_IMAGES_DIR: Path = IMAGES_DIR / "qemu"
    IOL_IMAGES_DIR: Path = IMAGES_DIR / "iol" / "bin"
    VPCS_IMAGES_DIR: Path = IMAGES_DIR / "vpcs"
    DOCKER_IMAGES_DIR: Path = IMAGES_DIR / "docker"

    # Dataplane & Networking (Ubuntu 26 Native)
    MGMT_BRIDGE: str = os.getenv("AZAM_MGMT_BRIDGE", "azam0")
    MGMT_SUBNET: str = os.getenv("AZAM_MGMT_SUBNET", "172.20.0.0/16")
    NAT_SUBNET: str = os.getenv("AZAM_NAT_SUBNET", "172.21.0.0/16")
    ENABLE_EBPF_SANDBOX: bool = True

    # 100:1 Memory Deduplication (KSM) Tunings
    KSM_PAGES_TO_SCAN: int = 50000
    KSM_SLEEP_MILLISECS: int = 10
    KSM_MERGE_ACROSS_NODES: int = 1

    # Anti-Bootstorm Scheduler & Eco-Mode
    STAGGER_DELAY_SECONDS: float = 2.0
    MAX_CONCURRENT_BOOTS: int = 4
    ECO_MODE_IDLE_TIMEOUT_MINUTES: int = 30
    ECO_MODE_ENABLED: bool = True

    def init_directories(self) -> None:
        """Ensure all required runtime directories exist."""
        for path in [
            self.DATA_DIR,
            self.LABS_DIR,
            self.IMAGES_DIR,
            self.QEMU_IMAGES_DIR,
            self.IOL_IMAGES_DIR,
            self.VPCS_IMAGES_DIR,
            self.DOCKER_IMAGES_DIR,
        ]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.init_directories()

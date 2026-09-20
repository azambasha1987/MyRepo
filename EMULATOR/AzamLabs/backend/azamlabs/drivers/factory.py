"""
AzamLabs Driver Factory
Provides centralized resolution and caching of virtual execution drivers.
"""

from typing import Dict
from azamlabs.core.schema import DriverType
from azamlabs.drivers.base import BaseDeviceDriver
from azamlabs.drivers.docker import DockerDriver
from azamlabs.drivers.qemu import QemuDriver
from azamlabs.drivers.iol import IolDriver
from azamlabs.drivers.vpcs import VpcsDriver


class DriverFactory:
    """Factory creating and caching driver singletons."""

    _drivers: Dict[DriverType, BaseDeviceDriver] = {
        DriverType.DOCKER: DockerDriver(),
        DriverType.QEMU: QemuDriver(),
        DriverType.IOL: IolDriver(),
        DriverType.VPCS: VpcsDriver(),
    }

    @classmethod
    def get_driver(cls, driver_type: DriverType) -> BaseDeviceDriver:
        """Returns the appropriate device driver for the given DriverType."""
        driver = cls._drivers.get(driver_type)
        if not driver:
            return cls._drivers[DriverType.DOCKER]
        return driver

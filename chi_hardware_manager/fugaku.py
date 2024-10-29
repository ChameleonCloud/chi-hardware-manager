import time

from ironic_python_agent import errors, hardware, netutils
from oslo_log import log

LOG = log.getLogger()


def _detect_hardware():
    """Detect if we're running on a fukaku node or not."""
    # TODO! Don't.
    return True


class FugakuHardwareManager(hardware.HardwareManager):
    """Handle partial IPMI support on Fugaku nodes."""

    HARDWARE_MANAGER_NAME = "FugakuHardwareManager"
    HARDWARE_MANAGER_VERSION = "1"

    def evaluate_hardware_support(self):
        """Declare level of hardware support provided.

        In order to override mainline methods, we must return a value of 2+.
        However, if we're not on a fugaku node, exit!
        """

        if _detect_hardware:
            return hardware.HardwareSupport.SERVICE_PROVIDER
        else:
            return hardware.HardwareSupport.NONE

    def list_hardware_info(self):
        """Return full hardware inventory as a serializable dict.

        This inventory is sent to Ironic on lookup and to Inspector on
        inspection.

        :returns: a dictionary representing inventory
        """
        start = time.time()
        LOG.info("Collecting full inventory")
        # NOTE(dtantsur): don't forget to update docs when extending inventory
        hardware_info = {}
        hardware_info["interfaces"] = self.list_network_interfaces()
        hardware_info["cpu"] = self.get_cpus()
        hardware_info["disks"] = self.list_block_devices()
        hardware_info["memory"] = self.get_memory()
        hardware_info["bmc_address"] = self.get_bmc_address()
        hardware_info["bmc_v6address"] = self.get_bmc_v6address()
        hardware_info["system_vendor"] = self.get_system_vendor_info()
        hardware_info["boot"] = self.get_boot_info()
        hardware_info["hostname"] = netutils.get_hostname()

        try:
            hardware_info["bmc_mac"] = self.get_bmc_mac()
        except errors.IncompatibleHardwareMethodError:
            # if the hardware manager does not support obtaining the BMC MAC,
            # we simply don't expose it.
            pass

        LOG.info("Inventory collected in %.2f second(s)", time.time() - start)
        return hardware_info

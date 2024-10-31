import time
from pathlib import Path

from ironic_python_agent import errors, hardware, netutils
from oslo_log import log

LOG = log.getLogger()


def _read_dmi():
    # check values of chassis_vendor and product_name in  /sys/devices/virtual/dmi/id/

    dmi_path = Path("/sys/devices/virtual/dmi/id/")
    keys = ["sys_vendor", "product_name"]

    dmi_info = {}

    for k in keys:
        with open(dmi_path.joinpath(k)) as f:
            dmi_info[k] = f.read()

    return dmi_info


def _detect_hardware():
    """Detect if we're running on a fukaku node or not."""

    dmi_info = _read_dmi()
    if (
        str.strip(dmi_info.get("sys_vendor")) == "FUJITSU"
        and str.strip(dmi_info.get("product_name")) == "FX700"
    ):
        LOG.info(f"found Fugaku node! {dmi_info}")
        return True
    else:
        LOG.info(f"We're not a Fugaku node, skipping: {dmi_info}")
        return False


class FugakuHardwareManager(hardware.HardwareManager):
    """Handle partial IPMI support on Fugaku nodes."""

    HARDWARE_MANAGER_NAME = "FugakuHardwareManager"
    HARDWARE_MANAGER_VERSION = "1"

    def evaluate_hardware_support(self):
        """Declare level of hardware support provided.

        In order to override mainline methods, we must return a value of 2+.
        However, if we're not on a fugaku node, exit!
        """

        if _detect_hardware():
            # This actually resolves down to an int. Upstream IPA will never
            # return a value higher than 2 (HardwareSupport.MAINLINE). This
            # means your managers should always be SERVICE_PROVIDER or higher.
            return hardware.HardwareSupport.SERVICE_PROVIDER
        else:
            # If the hardware isn't supported, return HardwareSupport.NONE (0)
            # in order to prevent IPA from loading its clean steps or
            # attempting to use any methods inside it.
            return hardware.HardwareSupport.NONE

    def get_bmc_address(self):
        LOG.info("Fugaku: no-op for bmc_address")
        return None

    def get_bmc_v6address(self):
        LOG.info("Fugaku: no-op for bmc_v6address")
        return None

    def get_bmc_mac(self):
        LOG.info("Fugaku: no-op for bmc_mac")
        return None

    def list_hardware_info(self):
        """Return full hardware inventory as a serializable dict.

        This inventory is sent to Ironic on lookup and to Inspector on
        inspection.

        :returns: a dictionary representing inventory
        """
        start = time.time()
        LOG.info("Fugaku: Collecting full inventory")
        # NOTE(dtantsur): don't forget to update docs when extending inventory
        hardware_info = {}
        hardware_info["interfaces"] = self.list_network_interfaces()
        hardware_info["cpu"] = self.get_cpus()
        hardware_info["disks"] = self.list_block_devices()
        hardware_info["memory"] = self.get_memory()
        hardware_info["bmc_address"] = self.get_bmc_address()
        hardware_info["bmc_v6address"] = self.get_bmc_v6address()
        # hardware_info["system_vendor"] = self.get_system_vendor_info()
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

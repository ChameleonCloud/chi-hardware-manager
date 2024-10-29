from pathlib import Path

from ironic_python_agent import errors, hardware
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
    LOG.warn(dmi_info)
    if (
        dmi_info.get("sys_vendor") == "FUJITSU"
        and dmi_info.get("product_name") == "FX700"
    ):
        return True
    else:
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
        return None

    def get_bmc_v6address(self):
        return None

    def get_bmc_mac(self):
        return None

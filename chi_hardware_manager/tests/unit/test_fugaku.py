from unittest import mock
from unittest.mock import DEFAULT, MagicMock

from ironic_python_agent.tests.unit import base

from chi_hardware_manager import fugaku


class FugakuHardwareManager(base.IronicAgentTest):
    def setUp(self):
        super(FugakuHardwareManager, self).setUp()

        self.hardware = fugaku.FugakuHardwareManager()
        self.node = {
            "uuid": "dda135fb-732d-4742-8e72-df8f3199d244",
            "driver_internal_info": {},
        }

    @mock.patch.object(fugaku, "_read_dmi")
    def test_detect_hardware(self, mock_read_dmi):
        # correct case
        mock_read_dmi.return_value = {
            "sys_vendor": "FUJITSU",
            "product_name": "FX700",
        }
        self.assertTrue(fugaku._detect_hardware())

        # handle newlines
        mock_read_dmi.return_value = {
            "sys_vendor": "FUJITSU\n",
            "product_name": "FX700\n",
        }
        self.assertTrue(fugaku._detect_hardware())

        # clearly incorrect case
        mock_read_dmi.return_value = {
            "sys_vendor": "OpenStack Foundation",
            "product_name": "OpenStack Nova",
        }
        self.assertFalse(fugaku._detect_hardware())

    @mock.patch.object(fugaku, "_detect_hardware")
    def test_hardware_support(self, mock_detect):
        mock_detect.return_value = False
        self.assertEqual(0, self.hardware.evaluate_hardware_support())

        mock_detect.return_value = True
        self.assertEqual(3, self.hardware.evaluate_hardware_support())

    def test_none_bmc_info(self):
        self.assertIsNone(self.hardware.get_bmc_address())
        self.assertIsNone(self.hardware.get_bmc_v6address())
        self.assertIsNone(self.hardware.get_bmc_mac())

    # @mock.patch(
    #     "ironic_python_agent.hardware.GenericHardwareManager.list_network_interfaces"
    # )
    # @mock.patch("ironic_python_agent.hardware.GenericHardwareManager.get_cpus")
    # @mock.patch(
    #     "ironic_python_agent.hardware.GenericHardwareManager.list_block_devices"
    # )
    # @mock.patch("ironic_python_agent.hardware.GenericHardwareManager.get_memory")
    # @mock.patch("ironic_python_agent.hardware.GenericHardwareManager.get_bmc_address")
    # @mock.patch("ironic_python_agent.hardware.GenericHardwareManager.get_bmc_v6address")
    # @mock.patch(
    #     "ironic_python_agent.hardware.GenericHardwareManager.get_system_vendor_info"
    # )
    # @mock.patch("ironic_python_agent.hardware.GenericHardwareManager.get_boot_info")
    # @mock.patch("ironic_python_agent.hardware.GenericHardwareManager.get_bmc_mac")

    @mock.patch.multiple(
        "ironic_python_agent.hardware.GenericHardwareManager",
        list_network_interfaces=DEFAULT,
        get_cpus=DEFAULT,
        list_block_devices=DEFAULT,
        get_memory=DEFAULT,
        get_bmc_address=DEFAULT,
        get_bmc_v6address=DEFAULT,
        get_system_vendor_info=DEFAULT,
        get_boot_info=DEFAULT,
        get_bmc_mac=DEFAULT,
    )
    def test_list_hardware_info(
        self,
        list_network_interfaces: mock.Mock,
        get_cpus: mock.Mock,
        list_block_devices: mock.Mock,
        get_memory: mock.Mock,
        get_bmc_address: mock.Mock,
        get_bmc_v6address: mock.Mock,
        get_system_vendor_info: mock.Mock,
        get_boot_info: mock.Mock,
        get_bmc_mac: mock.Mock,
        **kwargs,
    ):
        hardware_info = self.hardware.list_hardware_info()

        # methods from superclass, GenericHardwareManager
        list_network_interfaces.assert_called_once()
        get_cpus.assert_called_once()
        list_block_devices.assert_called_once()
        get_memory.assert_called_once()
        get_system_vendor_info.assert_called_once()
        get_boot_info.assert_called_once()

        # overridden methods
        get_bmc_address.assert_not_called()
        get_bmc_v6address.assert_not_called()
        get_bmc_mac.assert_not_called()

        self.assertIsNone(hardware_info["bmc_address"])
        self.assertIsNone(hardware_info["bmc_v6address"])
        self.assertIsNone(hardware_info["bmc_mac"])

from unittest import mock

from ironic_python_agent import errors
from ironic_python_agent.tests.unit import base

from chi_hardware_manager import fugaku


class FugakuHardwareManager(base.IronicAgentTest):
    def setUp(self):
        super().setUp()

        self.hardware = fugaku.FugakuHardwareManager()
        self.node = {
            "uuid": "dda135fb-732d-4742-8e72-df8f3199d244",
            "driver_internal_info": {},
        }

    @mock.patch.object(fugaku, "_read_dmi")
    def test_detect_hardware(self, mock_read_dmi):
        mock_read_dmi.return_value = {
            "sys_vendor": "FUJITSU",
            "product_name": "FX700",
        }
        self.assertTrue(fugaku._detect_hardware())

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

    @mock.patch.object(fugaku.FugakuHardwareManager, "list_network_interfaces")
    @mock.patch.object(fugaku.FugakuHardwareManager, "get_cpus")
    @mock.patch.object(fugaku.FugakuHardwareManager, "list_block_devices")
    @mock.patch.object(fugaku.FugakuHardwareManager, "get_memory")
    @mock.patch.object(
        fugaku.FugakuHardwareManager, "get_system_vendor_info", create=True
    )
    @mock.patch.object(fugaku.FugakuHardwareManager, "get_boot_info")
    def test_list_hardware_info(
        self,
        mock_list_iface,
        mock_get_cpus,
        mock_list_block_devices,
        mock_get_memory,
        mock_get_system_vendor_info,
        mock_get_boot_info,
    ):
        mock_list_iface.return_value = []
        mock_get_cpus.return_value = []
        mock_list_block_devices.return_value = []
        mock_get_memory.return_value = []
        mock_get_system_vendor_info.return_value = []
        mock_get_boot_info.return_value = []

        hardware_info = self.hardware.list_hardware_info()

        self.assertIsNone(hardware_info["bmc_address"])
        self.assertIsNone(hardware_info["bmc_v6address"])
        self.assertIsNone(hardware_info["bmc_mac"])

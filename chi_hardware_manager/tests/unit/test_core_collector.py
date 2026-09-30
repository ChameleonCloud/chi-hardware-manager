"""Tests for the chameleon-core collector, using a sysfs tree from gh01.

gh01 is an NVIDIA GH200 node at NCAR. File contents come from its inspection
data, and from reading /sys/class/net/*/speed on the node.
"""

import datetime
import shutil
from pathlib import Path
from unittest import mock

import fixtures
from oslotest import base

from chi_hardware_manager.collectors import core

GH01_FILES = {
    # ens3f1np1 is up at 100 Gb/s.
    "sys/class/net/ens3f1np1/address": "b4:5c:b5:53:b7:3d",
    "sys/class/net/ens3f1np1/carrier": "1",
    "sys/class/net/ens3f1np1/speed": "100000",
    # ens3f0np0 is down, so its speed can't be read.
    "sys/class/net/ens3f0np0/address": "b4:5c:b5:53:b7:3c",
    "sys/class/net/ens3f0np0/carrier": "0",
    # Loopback has no device.
    "sys/class/net/lo/address": "00:00:00:00:00:00",
}

GH01_LINKS = {
    "sys/class/net/ens3f1np1/device": "../../../devices/pci0000:00/0000:01:00.1",
    "sys/class/net/ens3f0np0/device": "../../../devices/pci0000:00/0000:01:00.0",
}


def build_tree(root, files, links):
    for path, content in files.items():
        file = root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content + "\n")
    for path, target in links.items():
        link = root / path
        link.parent.mkdir(parents=True, exist_ok=True)
        (link.parent / target).resolve().mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)


class TestCoreCollector(base.BaseTestCase):
    def setUp(self):
        super(TestCoreCollector, self).setUp()
        self.root = Path(self.useFixture(fixtures.TempDir()).path)
        build_tree(self.root, GH01_FILES, GH01_LINKS)
        # Reading a directory raises OSError, like speed on a down link (EINVAL).
        (self.root / "sys/class/net/ens3f0np0/speed").mkdir()

    def collect(self, data=None):
        data = {} if data is None else data
        failures = mock.Mock()
        core.collect(data, failures, root=self.root)
        failures.add.assert_not_called()
        return data["chameleon_core"]

    def test_nic_that_is_up(self):
        nic = self.collect()["data"]["nics"]["ens3f1np1"]
        self.assertEqual(
            {"address": "b4:5c:b5:53:b7:3d", "carrier": 1, "speed_mbps": 100000},
            nic,
        )

    def test_nic_that_is_down_has_no_speed(self):
        nic = self.collect()["data"]["nics"]["ens3f0np0"]
        self.assertEqual(
            {"address": "b4:5c:b5:53:b7:3c", "carrier": 0, "speed_mbps": None},
            nic,
        )

    def test_nic_speed_of_minus_one_means_no_speed(self):
        (self.root / "sys/class/net/ens3f1np1/speed").write_text("-1\n")
        nic = self.collect()["data"]["nics"]["ens3f1np1"]
        self.assertIsNone(nic["speed_mbps"])

    def test_interfaces_without_a_device_are_skipped(self):
        nics = self.collect()["data"]["nics"]
        self.assertEqual(["ens3f0np0", "ens3f1np1"], sorted(nics))

    def test_envelope_leaves_existing_data_untouched(self):
        data = {"inventory": {"interfaces": []}, "error": None}
        result = self.collect(data)

        self.assertEqual({"interfaces": []}, data["inventory"])
        self.assertIsNone(data["error"])
        collected_at = datetime.datetime.fromisoformat(result.pop("collected_at"))
        self.assertEqual(datetime.timedelta(0), collected_at.utcoffset())
        self.assertIsInstance(result.pop("duration_s"), float)
        self.assertEqual(
            {
                "schema_version": core.SCHEMA_VERSION,
                "status": "ok",
                "errors": {},
                "data": mock.ANY,
            },
            result,
        )
        self.assertEqual({"collector_version", "nics"}, set(result["data"]))

    def test_missing_sys_class_net(self):
        shutil.rmtree(self.root / "sys/class/net")

        result = self.collect()

        self.assertEqual("error", result["status"])
        self.assertEqual(["nics"], list(result["errors"]))
        self.assertTrue(result["errors"]["nics"].startswith("FileNotFoundError: "))
        self.assertIsNone(result["data"]["nics"])
        self.assertIn("collector_version", result["data"])

"""chameleon-core inspection collector.

Records kernel values from sysfs as they are, instead of parsing tool output
that can distort them: the image's lshw reports a 100 Gb/s ConnectX-7 NIC as
40 Gb/s. The transmogrifier decides what to publish.

Collects each NIC's MAC address, carrier state and negotiated link speed, and
the collector's version.

Each section is collected independently. Errors are recorded in the output,
never passed to IPA's ``failures``, so the collector never fails an
inspection.
"""

import datetime
import json
import sys
import time
from importlib import metadata
from pathlib import Path

SCHEMA_VERSION = 1


class Sysfs:
    """Reads files under a root directory, normally /.

    text() and integer() return None if a file is missing or unreadable, e.g.
    a NIC's speed while its link is down (EINVAL). entries() raises, so a
    missing directory fails its section.
    """

    def __init__(self, root="/"):
        self.root = Path(root)

    def path(self, *parts):
        return self.root.joinpath(*parts)

    def text(self, *parts):
        try:
            return self.path(*parts).read_text().strip()
        except (OSError, UnicodeDecodeError):
            return None

    def integer(self, *parts):
        try:
            return int(self.text(*parts))
        except (TypeError, ValueError):
            return None

    def entries(self, *parts):
        return sorted(p.name for p in self.path(*parts).iterdir())


def collect_nics(fs):
    nics = {}
    for name in fs.entries("sys/class/net"):
        nic_dir = f"sys/class/net/{name}"
        # Skip interfaces with no device: lo, bridges, bonds, VLANs.
        if not fs.path(nic_dir, "device").exists():
            continue
        speed = fs.integer(nic_dir, "speed")
        nics[name] = {
            "address": fs.text(nic_dir, "address"),
            "carrier": fs.integer(nic_dir, "carrier"),
            # Some drivers report -1 with no link.
            "speed_mbps": speed if speed and speed > 0 else None,
        }
    return nics


SECTIONS = {
    "nics": collect_nics,
}


def collector_version():
    try:
        return metadata.version("chi-hardware-manager")
    except metadata.PackageNotFoundError:
        return None


def collect_core(root="/"):
    """Collect every section, recording a section's error instead of raising."""
    fs = Sysfs(root)
    facts = {"collector_version": collector_version()}
    errors = {}
    for section, collect_section in SECTIONS.items():
        try:
            facts[section] = collect_section(fs)
        except Exception as exc:
            facts[section] = None
            errors[section] = f"{type(exc).__name__}: {exc}"
    return facts, errors


def collect(data, failures, root="/"):
    """IPA inspection collector entry point."""
    started = time.monotonic()
    facts, errors = collect_core(root)
    data["chameleon_core"] = {
        "schema_version": SCHEMA_VERSION,
        "status": "error" if errors else "ok",
        "errors": errors,
        "collected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "duration_s": round(time.monotonic() - started, 3),
        "data": facts,
    }


if __name__ == "__main__":
    # Standalone, without IPA: python3 core.py [ROOT]
    out = {}
    collect(out, None, root=sys.argv[1] if len(sys.argv) > 1 else "/")
    print(json.dumps(out, indent=2, sort_keys=True))

# chi-hardware-manager

Chameleon plugins for the Ironic Python Agent (IPA):

| Plugin | Type | Purpose |
|---|---|---|
| `chi_fugaku_manager` | hardware manager | Skips BMC queries on Fujitsu FX700 (Fugaku) nodes. |
| `chameleon-core` | inspection collector | Records kernel values from sysfs, starting with NIC link speed. |

## Installation

ipa-builder's `chi_ipa` element installs this package from GitHub `main` into
the ramdisk's `/opt/ironic-python-agent` venv. A change reaches nodes only
after the image is rebuilt and deployed.

To build a test image from an unmerged branch, add this line to ipa-builder's
`ipa_debian.env`:

```sh
DIB_REPOREF_chi_hardware_manager=<branch>
```

## Fugaku hardware manager

IPA loads every installed hardware manager automatically, so this one needs
no configuration.

On nodes whose DMI reports `FUJITSU` / `FX700` (from
`/sys/devices/virtual/dmi/id/{sys_vendor,product_name}`), the manager takes
precedence over IPA's generic one. Elsewhere it declares no support and IPA
ignores it.

The FX700's BMC only partly supports IPMI. On these nodes the manager reports
`bmc_address`, `bmc_v6address` and `bmc_mac` as `null` instead of querying the
BMC with `ipmitool`. The rest of the inventory is IPA's generic inventory.

## `chameleon-core` inspection collector

The collector reads NIC values directly from `/sys/class/net`. lshw in the
image reports 100 Gb/s ConnectX-7 NICs as 40 Gb/s, so the collector gives the
real speed. It uses only the standard library.

### Enabling

IPA runs only the collectors named in the `ipa-inspection-collectors` kernel
parameter, in the order listed. Add `chameleon-core` to that parameter on the
inspection ramdisk's kernel command line, before `logs`:

```text
ipa-inspection-collectors=default,extra-hardware,pci-devices,dmi-decode,numa-topology,chameleon-core,logs
```

> [!WARNING]
> Only add `chameleon-core` once the deployed ramdisk includes it. IPA fails
> the whole inspection with `Failed to load collector` if a listed collector
> isn't installed.

The collector itself never fails an inspection. It records errors in its
output (see below).

### Output

The collector adds a `chameleon_core` key to the inspection data:

```json
{
  "chameleon_core": {
    "schema_version": 1,
    "status": "ok",
    "errors": {},
    "collected_at": "2026-09-30T17:31:19.279160+00:00",
    "duration_s": 0.002,
    "data": {
      "collector_version": "0.0.0",
      "nics": {
        "ens3f0np0": {"address": "b4:5c:b5:53:b7:3c", "carrier": 0, "speed_mbps": null},
        "ens3f1np1": {"address": "b4:5c:b5:53:b7:3d", "carrier": 1, "speed_mbps": 100000}
      }
    }
  }
}
```

- `status` is `"error"` if any section failed. That section's value under
  `data` is `null`, and `errors` maps the section name to
  `"<ExceptionType>: <message>"`.
- `collector_version` is the installed package version, or `null` if the
  package isn't installed.
- `nics` lists only interfaces backed by a device, so `lo`, bridges, bonds
  and VLANs are skipped.
- `carrier` is `1` or `0`, or `null` if the interface is administratively
  down.
- `speed_mbps` is the negotiated link speed in Mb/s, or `null` if the link is
  down or the driver reports no speed.

### Reading the data

ironic-inspector stores inspection data only if `[processing] store_data` is
`database` or `swift`. The default is `none`. To show one node's output:

```sh
openstack baremetal introspection data save <node> | jq .chameleon_core
```

### Running by hand

The collector runs without IPA and prints the same output as JSON.

Inside a running ramdisk:

```sh
/opt/ironic-python-agent/bin/python3 -m chi_hardware_manager.collectors.core
```

From a checkout, on any host:

```sh
python3 chi_hardware_manager/collectors/core.py [ROOT]
```

`ROOT` defaults to `/`. To test against captured data, point it at a
directory that contains `sys/class/net`. In the captured tree, each NIC's
`device` link must resolve, or the NIC is skipped.

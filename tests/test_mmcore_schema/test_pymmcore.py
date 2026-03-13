from __future__ import annotations

import os
from pathlib import Path

import pytest

from mmcore_schema.mmconfig import MMConfig

try:
    import pymmcore

    import pymmcore_plus
except ImportError:
    pytest.skip("pymmcore_plus is not installed", allow_module_level=True)


DEMO_CFG = Path(__file__).parent / "configs" / "MMConfig_demo.cfg"


def test_load_system_configuration() -> None:
    core = pymmcore.CMMCore()
    if not (mm_path := pymmcore_plus.find_micromanager()):
        pytest.fail("Micromanager not found, cannot run test")

    os.environ["PATH"] = os.pathsep.join((mm_path, os.environ["PATH"]))
    core.setDeviceAdapterSearchPaths([mm_path])
    demo_cfg = MMConfig.from_file(DEMO_CFG)
    demo_cfg.enable_parallel_device_initialization = True
    demo_cfg.load_in_pymmcore(core)

    assert set(core.getLoadedDevices()) == {
        "Core",
        "DHub",
        "Camera",
        "Dichroic",
        "Emission",
        "Excitation",
        "Objective",
        "Z",
        "Path",
        "XY",
        "White Light Shutter",
        "Autofocus",
        "LED",
        "LED Shutter",
    }
    assert core.getCameraDevice() == "Camera"
    assert core.getShutterDevice() == "White Light Shutter"
    assert core.getFocusDevice() == "Z"
    assert core.getAutoShutter() is True

from contextlib import suppress
from typing import Any, Sequence

from pymmcore_plus import CMMCorePlus

# ---- these methods don't start with get, but take no arguments ----
SYS_STATUS = {
    "debugLogEnabled",
    "isBufferOverflowed",
    "isContinuousFocusEnabled",
    "isContinuousFocusLocked",
    "isSequenceRunning",
    "stderrLogEnabled",
    "systemBusy",
    # "isMultiROIEnabled",  # camera related
    # "isMultiROISupported",
    # "getAutoShutter",
    # "shutterOpen",
}
SYSTEM = {
    "APIVersionInfo",
    "BufferFreeCapacity",
    "BufferTotalCapacity",
    "CircularBufferMemoryFootprint",
    "RemainingImageCount",
    "DeviceAdapterSearchPaths",
    "HostName",
    "MACAddresses",
    "PrimaryLogFile",
    "VersionInfo",
    "UserId",
    "TimeoutMs",  # rarely needed for metadata
}


IMAGE = {
    "BytesPerPixel",
    "Exposure",
    "ImageBitDepth",
    "ImageBufferSize",
    "ImageHeight",
    "ImageWidth",
    "MagnificationFactor",
    "MultiROI",
    "NumberOfCameraChannels",
    "NumberOfComponents",
    "PixelSizeAffine",
    "PixelSizeUm",
    "ROI",
    "CurrentPixelSizeConfig",
}

core = CMMCorePlus()
core.loadSystemConfiguration()
# core.setPixelSizeConfig("Res40x")
# core.setXYPosition(1, 2)


def state(
    core: CMMCorePlus,
    *,
    devices: bool = True,
    system_info: bool = False,
    system_status: bool = False,
    config_groups: bool | Sequence[str] = False,
    image: bool = True,
    position: bool = True,
    autofocus: bool = False,
    pixel_size_configs: bool = False,
    device_types: bool = True,
    cached: bool = True,
    error_value: Any = None,
) -> dict:
    out: dict = {}
    if devices:
        device_state: dict = {}
        _state = core.getSystemStateCache() if cached else core.getSystemState()
        for dev, prop, val in _state:
            device_state.setdefault(dev, {})[prop] = val
        out["Devices"] = device_state
    if system_info:
        out["SystemInfo"] = {
            key: getattr(core, f"get{key}")() for key in sorted(SYSTEM)
        }
    if system_status:
        # XXX: maybe move... the only reason to leave out of SYS_STATUS is
        # because it's the only getX method and we want more uniform keys?
        out["SystemStatus"] = {
            "autoShutter": core.getAutoShutter(),
            "shutterOpen": core.getShutterOpen(),
        }
        out["SystemStatus"].update(
            {key: getattr(core, key)() for key in sorted(SYS_STATUS)}
        )

    if config_groups:
        if not isinstance(config_groups, (list, tuple, set)):
            config_groups = core.getAvailableConfigGroups()

        cfg_group_dict: dict = {}
        for grp in config_groups:
            if grp == "[Channel]":
                grp = core.getChannelGroup()

            grp_dict = cfg_group_dict.setdefault(grp, {})
            grp_info = (
                core.getConfigGroupStateFromCache(grp)
                if cached
                else core.getConfigGroupState(grp)
            )
            for dev, prop, val in grp_info:
                grp_dict.setdefault(dev, {})[prop] = val
        out["ConfigGroups"] = cfg_group_dict

    if image:
        img_dict: dict = {}
        for key in sorted(IMAGE):
            try:
                val = getattr(core, f"get{key}")()
            except Exception:
                val = error_value
            img_dict[key] = val
        out["Image"] = img_dict

    if position:
        pos = {"X": error_value, "Y": error_value, "Focus": error_value}
        with suppress(Exception):
            pos["X"] = core.getXPosition()
            pos["Y"] = core.getYPosition()
        with suppress(Exception):
            pos["Focus"] = core.getPosition()
        out["Position"] = pos

    if autofocus:
        out["AutoFocus"] = {
            "CurrentFocusScore": core.getCurrentFocusScore(),
            "LastFocusScore": core.getLastFocusScore(),
        }
        try:
            out["AutoFocus"]["AutoFocusOffset"] = core.getAutoFocusOffset()
        except Exception:
            out["AutoFocus"]["AutoFocusOffset"] = error_value

    if pixel_size_configs:
        px: dict = {"Current": core.getCurrentPixelSizeConfig()}
        for px_cfg_name in core.getAvailablePixelSizeConfigs():
            px_cfg_info: dict = {}
            for dev, prop, val in core.getPixelSizeConfigData(px_cfg_name):
                px_cfg_info.setdefault(dev, {})[prop] = val
            px_cfg_info["PixelSizeUm"] = core.getPixelSizeUmByID(px_cfg_name)
            px_cfg_info["PixelSizeAffine"] = core.getPixelSizeAffineByID(px_cfg_name)
            px[px_cfg_name] = px_cfg_info

        out["PixelSizeConfig"] = px

    if device_types:
        dev_types_dict = {}
        for dev_name in core.getLoadedDevices():
            dev_types_dict[dev_name] = {
                "Type": core.getDeviceType(dev_name).name,
                "Description": core.getDeviceDescription(dev_name),
                "Adapter": core.getDeviceName(dev_name),
            }
        out["DeviceTypes"] = dev_types_dict
    return out


import time

from rich import print

_start = time.perf_counter_ns()
x = state(core)
fin = time.perf_counter_ns() - _start
print(x)
print(fin / 1000000)

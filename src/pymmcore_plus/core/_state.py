from contextlib import suppress
from typing import Any, Sequence, TypedDict

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


class SystemInfoDict(TypedDict):
    APIVersionInfo: str
    BufferFreeCapacity: int
    BufferTotalCapacity: int
    CircularBufferMemoryFootprint: int
    DeviceAdapterSearchPaths: tuple[str, ...]
    HostName: str
    MACAddresses: tuple[str, ...]
    PrimaryLogFile: str
    RemainingImageCount: int
    TimeoutMs: int  # rarely needed for metadata
    UserId: str
    VersionInfo: str


core = CMMCorePlus()
core.loadSystemConfiguration()
# core.setPixelSizeConfig("Res40x")
# core.setXYPosition(1, 2)


class ImageDict(TypedDict):
    BytesPerPixel: int
    CurrentPixelSizeConfig: str
    Exposure: float
    ImageBitDepth: int
    ImageBufferSize: int
    ImageHeight: int
    ImageWidth: int
    MagnificationFactor: float
    MultiROI: tuple[list[int], list[int], list[int], list[int]] | None
    NumberOfCameraChannels: int
    NumberOfComponents: int
    PixelSizeAffine: tuple[float, float, float, float, float, float]
    PixelSizeUm: int
    ROI: list[int]


class PositionDict(TypedDict):
    X: float | None
    Y: float | None
    Focus: float | None


class AutoFocusDict(TypedDict):
    CurrentFocusScore: float
    LastFocusScore: float
    AutoFocusOffset: float | None


class PixelSizeConfigDict(TypedDict):
    Objective: dict[str, str]
    PixelSizeUm: float
    PixelSizeAffine: tuple[float, float, float, float, float, float]


class DeviceTypeDict(TypedDict):
    Type: str
    Description: str
    Adapter: str


class StateDict(TypedDict, total=False):
    Device: dict[str, dict[str, str]]
    SystemInfo: SystemInfoDict
    SystemStatus: dict[str, bool]
    ConfigGroups: dict[str, dict[str, Any]]
    Image: ImageDict
    Position: PositionDict
    Autofocus: AutoFocusDict
    PixelSizeConfig: dict[str, str | PixelSizeConfigDict]
    DeviceTypes: dict[str, DeviceTypeDict]


def state(
    core: CMMCorePlus,
    *,
    devices: bool = False,
    image: bool = True,
    system_info: bool = True,
    system_status: bool = False,
    config_groups: bool | Sequence[str] = False,
    position: bool = False,
    autofocus: bool = False,
    pixel_size_configs: bool = False,
    device_types: bool = False,
    cached: bool = True,
    error_value: Any = None,
) -> dict:
    out: dict = {}

    if devices:
        # this actually appears to be faster than getSystemStateCache
        device_state: dict = {}
        for dev in core.getLoadedDevices():
            dd = device_state.setdefault(dev, {})
            for prop in core.getDevicePropertyNames(dev):
                try:
                    val = core.getProperty(dev, prop)
                except Exception:
                    val = error_value
                dd[prop] = val
        out["Devices"] = device_state

    if system_info:
        out["SystemInfo"] = {
            key: getattr(core, f"get{key}")()
            for key in sorted(SystemInfoDict.__annotations__)
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
        for key in sorted(ImageDict.__annotations__):
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
        out["DeviceTypes"] = {
            dev_name: {
                "Type": core.getDeviceType(dev_name).name,
                "Description": core.getDeviceDescription(dev_name),
                "Adapter": core.getDeviceName(dev_name),
            }
            for dev_name in core.getLoadedDevices()
        }
    return out


import time

from rich import print

_start = time.perf_counter_ns()
x = state(core)
fin = time.perf_counter_ns() - _start
print(x)
print(fin / 1000000, "ms")

GETTABLES = {
    "AutoShutter",
    "BytesPerPixel",
    "CurrentFocusScore",
    "CurrentPixelSizeConfig",
    "Exposure",
    "ImageBitDepth",
    "ImageBufferSize",
    "ImageHeight",
    "ImageWidth",
    "LastFocusScore",
    "MagnificationFactor",
    "NumberOfCameraChannels",
    "NumberOfComponents",
    "PixelSizeAffine",
    "PixelSizeUm",
    "RemainingImageCount",
    "ROI",
    "ShutterOpen",
    "TimeoutMs",
    # -------- below here must be try/excepted --------
    "AutoFocusOffset",
    # "Image",
    # "LastImage",
    "MultiROI",
    "Position",
    "XPosition",
    "YPosition",
}

# ---- these methods don't start with get, but take no arguments ----
NON_GET = {
    "debugLogEnabled",
    "isBufferOverflowed",
    "isContinuousFocusEnabled",
    "isContinuousFocusLocked",
    # "isMultiROIEnabled",  # camera related
    # "isMultiROISupported",
    "isSequenceRunning",
    "stderrLogEnabled",
    "systemBusy",
}
SYSTEM = {
    "APIVersionInfo",
    "BufferFreeCapacity",
    "BufferTotalCapacity",
    "CircularBufferMemoryFootprint",
    "DeviceAdapterSearchPaths",
    "HostName",
    "MACAddresses",
    "PrimaryLogFile",
    "VersionInfo",
    "UserId",
}
# These are all also available in the system state cache
# CORE_DEVICES = {
#     "AutoFocusDevice",
#     "CameraDevice",
#     "FocusDevice",
#     "GalvoDevice",
#     "ImageProcessorDevice",
#     "ShutterDevice",
#     "SLMDevice",
#     "XYStageDevice",
#     "ChannelGroup",
# }
# these aren't things you tend to need or are covered by other keys
# AVAILABLES = [
#     "AvailableConfigGroups",
#     "AvailablePixelSizeConfigs",
#     "AvailablePropertyBlocks",
#     "DeviceAdapterNames",
#     "LoadedDevices",
#     # "SystemState",
#     # "SystemStateCache",
# ]


from pymmcore_plus import CMMCorePlus

core = CMMCorePlus()
core.loadSystemConfiguration()
core.setPixelSizeConfig("Res40x")
core.setXYPosition(1, 2)


def state(
    core: CMMCorePlus,
    *,
    system_state: bool = True,
    system_info: bool = True,
    status: bool = True,
    config_groups: bool = True,
) -> dict:
    out: dict = {}
    if system_state:
        device_state: dict = {}
        for dev, prop, val in core.getSystemStateCache():
            device_state.setdefault(dev, {})[prop] = val
        out["State"] = device_state
    if system_info:
        out["SystemInfo"] = {
            key: getattr(core, f"get{key}")() for key in sorted(SYSTEM)
        }
    if status:
        out["SystemStatus"] = {key: getattr(core, key)() for key in sorted(NON_GET)}

    if config_groups:
        cfg_group_dict: dict = {}
        for grp in core.getAvailableConfigGroups():
            grp_dict = cfg_group_dict.setdefault(grp, {})
            for dev, prop, val in core.getConfigGroupState(grp):
                grp_dict.setdefault(dev, {})[prop] = val
        out["ConfigGroupsStates"] = cfg_group_dict

    for key in sorted(GETTABLES):
        try:
            val = getattr(core, f"get{key}")()
        except Exception:
            val = "ERROR"
        out[key] = val

    return out


from rich import print

print(state(core))

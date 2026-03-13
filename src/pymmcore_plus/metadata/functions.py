from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, Any, TypedDict

import pymmcore_plus
from pymmcore_plus import core_io
from pymmcore_plus._util import timestamp
from pymmcore_plus.core._constants import DeviceType, PixelFormat

if TYPE_CHECKING:
    import useq
    from typing_extensions import Unpack

    from mmcore_schema.state import (
        ConfigGroup as _StateConfigGroup,
        DeviceInfo as _StateDeviceInfo,
        PixelSizePreset as _StatePixelSizePreset,
        PropertyInfo as _StatePropertyInfo,
    )
    from pymmcore_plus.core import CMMCorePlus

    from .schema import (
        ConfigGroup,
        DeviceInfo,
        FrameMetaV1,
        ImageInfo,
        PixelSizeConfigPreset,
        Position,
        PropertyInfo,
        PropertyValue,
        StagePosition,
        SummaryMetaV1,
        SystemInfo,
    )

    class _OptionalFrameMetaKwargs(TypedDict, total=False):
        """Additional optional fields for frame metadata."""

        mda_event: useq.MDAEvent
        hardware_triggered: bool
        images_remaining_in_buffer: int
        camera_metadata: dict[str, Any]
        extra: dict[str, Any]
        position: Position

# -----------------------------------------------------------------
# These are the two main functions that are called from the outside
# -----------------------------------------------------------------


def summary_metadata(
    core: CMMCorePlus,
    *,
    mda_sequence: useq.MDASequence | None = None,
    cached: bool = True,
    include_time: bool = True,
) -> SummaryMetaV1:
    """Return a summary metadata for the current state of the system.

    See [pymmcore_plus.metadata.SummaryMetaV1][] for a description of the
    dictionary format.
    """
    state = core_io.read_system_state(core, cached=cached)
    summary: SummaryMetaV1 = {
        "format": "summary-dict",
        "version": "1.0",
        "devices": tuple(_convert_device(d, core) for d in state.devices),
        "system_info": system_info(core),
        "image_infos": image_infos(core),
        "position": position(core),
        "config_groups": tuple(
            _convert_config_group(g) for g in state.config_groups
        ),
        "pixel_size_configs": tuple(
            _convert_pixel_size_preset(p) for p in state.pixel_size_configs
        ),
    }
    if include_time:
        summary["datetime"] = timestamp()
    if mda_sequence:
        summary["mda_sequence"] = mda_sequence
    return summary


def frame_metadata(
    core: CMMCorePlus,
    *,
    cached: bool = True,
    runner_time_ms: float = -1,
    camera_device: str | None = None,
    property_values: tuple[PropertyValue, ...] = (),
    include_position: bool = False,
    **kwargs: Unpack[_OptionalFrameMetaKwargs],
) -> FrameMetaV1:
    """Return metadata for the current frame."""
    info: FrameMetaV1 = {
        "format": "frame-dict",
        "version": "1.0",
        "runner_time_ms": runner_time_ms,
        "camera_device": camera_device or core.getPhysicalCameraDevice(),
        "property_values": property_values,
        "exposure_ms": core.getExposure(),
        "pixel_size_um": core.getPixelSizeUm(cached),
        **kwargs,
    }
    if include_position and "position" not in kwargs:
        info["position"] = position(core)
    return info


# ----------------------------------------------
# supporting functions
# ----------------------------------------------


def device_info(core: CMMCorePlus, *, label: str, cached: bool = True) -> DeviceInfo:
    """Return information about a specific device label."""
    state_dev = core_io.read_device_info(core, label, cached=cached)
    return _convert_device(state_dev, core)


def system_info(core: CMMCorePlus) -> SystemInfo:
    """Return general system information."""
    return {
        "pymmcore_version": pymmcore_plus.__version__,
        "pymmcore_plus_version": pymmcore_plus.__version__,
        "mmcore_version": core.getVersionInfo(),
        "device_api_version": core.getAPIVersionInfo(),
        "device_adapter_search_paths": core.getDeviceAdapterSearchPaths(),
        "system_configuration_file": core.systemConfigurationFile(),
        "primary_log_file": core.getPrimaryLogFile(),
        "sequence_buffer_size_mb": core.getCircularBufferMemoryFootprint(),
        "continuous_focus_enabled": core.isContinuousFocusEnabled(),
        "continuous_focus_locked": core.isContinuousFocusLocked(),
        "auto_shutter": core.getAutoShutter(),
        "timeout_ms": core.getTimeoutMs(),
    }


def image_info(core: CMMCorePlus) -> ImageInfo:
    """Return information about the current camera image properties."""
    w = core.getImageWidth()
    h = core.getImageHeight()
    n_comp = core.getNumberOfComponents()
    plane_shape: tuple[int, int] | tuple[int, int, int] = (h, w)
    if n_comp == 1:
        plane_shape = (h, w)
    elif n_comp == 4:
        plane_shape = (h, w, 3)
    else:
        plane_shape = (h, w, n_comp)
    bpp = core.getBytesPerPixel()
    try:
        dtype = f"uint{(bpp // n_comp) * 8}"
    except ZeroDivisionError:
        dtype = "unknown"

    info: ImageInfo = {
        "camera_label": core.getCameraDevice(),
        "plane_shape": plane_shape,
        "dtype": dtype,
        "height": h,
        "width": w,
        "pixel_format": PixelFormat.for_current_camera(core).value,
        "pixel_size_um": core.getPixelSizeUm(True),
        "pixel_size_config_name": core.getCurrentPixelSizeConfig(),
    }

    if (n_channels := core.getNumberOfCameraChannels()) > 1:
        info["num_camera_adapter_channels"] = n_channels
    if (mag_factor := core.getMagnificationFactor()) != 1.0:
        info["magnification_factor"] = mag_factor
    if (affine := core.getPixelSizeAffine(True)) != (1.0, 0.0, 0.0, 0.0, 1.0, 0.0):
        info["pixel_size_affine"] = affine

    with suppress(RuntimeError):
        if (roi := core.getROI()) != [0, 0, w, h]:
            info["roi"] = tuple(roi)  # type: ignore [typeddict-item]
    with suppress(RuntimeError):
        if any(rois := core.getMultiROI()):
            info["multi_roi"] = rois
    return info


def image_infos(core: CMMCorePlus) -> tuple[ImageInfo, ...]:
    """Return information about the current image properties for all cameras."""
    if not (selected := core.getCameraDevice()):
        return ()
    # currently selected device is always first
    infos: list[ImageInfo] = [image_info(core)]
    try:
        # set every other camera and get the image info
        for cam in core.getLoadedDevicesOfType(DeviceType.Camera):
            if cam != selected:
                with suppress(RuntimeError):
                    core.setCameraDevice(cam)
                    infos.append(image_info(core))
    finally:
        # set the camera back to the originally selected device
        with suppress(RuntimeError):
            core.setCameraDevice(selected)
    return tuple(infos)


def position(core: CMMCorePlus, all_stages: bool = False) -> Position:
    """Return current position of active (and, optionally, all) stages."""
    position: Position = {}

    try:
        # single shot faster when it works
        position["x"], position["y"] = core.getXYPosition()
    except RuntimeError:
        with suppress(Exception):
            position["x"] = core.getXPosition()
        with suppress(Exception):
            position["y"] = core.getYPosition()

    with suppress(Exception):
        position["z"] = core.getPosition()

    if all_stages:
        pos_list: list[StagePosition] = []
        for stage in core.getLoadedDevicesOfType(DeviceType.Stage):
            with suppress(Exception):
                pos_list.append(
                    {
                        "device_label": stage,
                        "position": core.getPosition(stage),
                    }
                )
        for stage in core.getLoadedDevicesOfType(DeviceType.XYStage):
            with suppress(Exception):
                pos_list.append(
                    {
                        "device_label": stage,
                        "position": tuple(core.getXYPosition(stage)),  # type: ignore
                    }
                )
        position["all_stages"] = pos_list
    return position


def config_group(core: CMMCorePlus, *, group_name: str) -> ConfigGroup:
    """Return a dictionary of configuration presets for a specific group."""
    return _convert_config_group(core_io.read_config_group(core, group_name))


def config_groups(core: CMMCorePlus) -> tuple[ConfigGroup, ...]:
    """Return all configuration groups."""
    return tuple(
        _convert_config_group(g) for g in core_io.read_config_groups(core)
    )


def pixel_size_config(core: CMMCorePlus, *, config_name: str) -> PixelSizeConfigPreset:
    """Return info for a specific pixel size preset."""
    return _convert_pixel_size_preset(
        core_io.read_pixel_size_preset(core, config_name)
    )


def devices_info(core: CMMCorePlus, cached: bool = True) -> tuple[DeviceInfo, ...]:
    """Return a dictionary of device information for all loaded devices."""
    state_devs = core_io.read_devices(core, cached=cached)
    return tuple(_convert_device(d, core) for d in state_devs)


def property_info(
    core: CMMCorePlus,
    device: str,
    prop: str,
    *,
    cached: bool = True,
) -> PropertyInfo:
    """Return information on a specific device property."""
    state_prop = core_io.read_property_info(core, device, prop, cached=cached)
    return _convert_property(state_prop, core, device)


def properties(
    core: CMMCorePlus, device: str, *, cached: bool = True
) -> tuple[PropertyInfo, ...]:
    """Return a dictionary of device properties values for all loaded devices."""
    state_props = core_io.read_properties(core, device, cached=cached)
    return tuple(_convert_property(p, core, device) for p in state_props)


def pixel_size_configs(core: CMMCorePlus) -> tuple[PixelSizeConfigPreset, ...]:
    """Return a dictionary of pixel size configurations."""
    return tuple(
        _convert_pixel_size_preset(p)
        for p in core_io.read_pixel_size_presets(core)
    )


# --------------- state model → metadata TypedDict conversion ---------------

_IDENTITY_AFFINE = (1.0, 0.0, 0.0, 0.0, 1.0, 0.0)


def _convert_property(
    prop: _StatePropertyInfo,
    core: CMMCorePlus,
    device: str,
) -> PropertyInfo:
    """Convert mmcore_schema.state.PropertyInfo to metadata PropertyInfo."""
    info: PropertyInfo = {
        "name": prop.name,
        "value": prop.value or None,
        "data_type": repr(prop.data_type),
        "allowed_values": prop.allowed_values,
        "is_read_only": prop.is_read_only,
    }
    if prop.is_pre_init:
        info["is_pre_init"] = True
    if prop.limits is not None:
        info["limits"] = prop.limits
    if core.isPropertySequenceable(device, prop.name):
        info["sequenceable"] = True
        info["sequence_max_length"] = core.getPropertySequenceMaxLength(
            device, prop.name
        )
    return info


def _convert_device(
    dev: _StateDeviceInfo,
    core: CMMCorePlus,
) -> DeviceInfo:
    """Convert mmcore_schema.state.DeviceInfo to metadata DeviceInfo."""
    info: DeviceInfo = {
        "label": dev.label,
        "library": dev.library,
        "name": dev.name,
        "type": dev.type.name,
        "description": dev.description,
        "properties": tuple(
            _convert_property(p, core, dev.label) for p in dev.properties
        ),
    }
    if dev.parent_label:
        info["parent_label"] = dev.parent_label
    with suppress(RuntimeError):
        if dev.type == DeviceType.Hub:
            info["child_names"] = dev.child_names
        if dev.type == DeviceType.State:
            info["labels"] = dev.state_labels
        elif dev.type == DeviceType.Stage:
            info["is_sequenceable"] = core.isStageSequenceable(dev.label)
            info["is_continuous_focus_drive"] = core.isContinuousFocusDrive(
                dev.label
            )
            info["focus_direction"] = dev.focus_direction.name  # type: ignore[typeddict-item]
        elif dev.type == DeviceType.XYStage:
            info["is_sequenceable"] = core.isXYStageSequenceable(dev.label)
        elif dev.type == DeviceType.Camera:
            info["is_sequenceable"] = core.isExposureSequenceable(dev.label)
        elif dev.type == DeviceType.SLM:
            info["is_sequenceable"] = core.getSLMSequenceMaxLength(dev.label) > 0
    return info


def _convert_config_group(group: _StateConfigGroup) -> ConfigGroup:
    """Convert mmcore_schema.state.ConfigGroup to metadata ConfigGroup."""
    return {
        "name": group.name,
        "presets": tuple(
            {
                "name": preset.name,
                "settings": tuple(
                    {"dev": s.device, "prop": s.property, "val": s.value}
                    for s in preset.settings
                ),
            }
            for preset in group.presets.values()
        ),
    }


def _convert_pixel_size_preset(
    preset: _StatePixelSizePreset,
) -> PixelSizeConfigPreset:
    """Convert mmcore_schema.state.PixelSizePreset to metadata TypedDict."""
    info: PixelSizeConfigPreset = {
        "name": preset.name,
        "pixel_size_um": preset.pixel_size_um,
        "settings": tuple(
            {"dev": s.device, "prop": s.property, "val": s.value}
            for s in preset.settings
        ),
    }
    if tuple(preset.affine) != _IDENTITY_AFFINE:
        info["pixel_size_affine"] = tuple(preset.affine)  # type: ignore[assignment]
    if preset.dxdz:
        info["pixel_size_dxdz"] = preset.dxdz
    if preset.dydz:
        info["pixel_size_dydz"] = preset.dydz
    if preset.optimal_z_um:
        info["pixel_size_optimal_z_um"] = preset.optimal_z_um
    return info

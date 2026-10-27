# Configuration and Groups

Configuring a microscope with Micro-Manager entails storing and retrieving
a number of device settings.  In general, a single setting comprises
a device name, a property name, and a value.  A **Configuration** object (a
*preset*, in the Micro-Manager app) represents a *collection* of individual
settings; that is, it represents a number of device parameters all in a specific
state, such as would be used to prepare the microscope to image a specific
channel, like "DAPI", or "FITC".

A **Configuration Group** is, in turn, a *collection* of `Configuration` objects;
for example, all of the `Configuration` objects that represent different
"Channel" settings.

Conceptually, Configurations and Groups are organized like this:

```YAML
ConfigGroupA:
    Configuration1:
        deviceA:
            propertyA: 'value_a'
            propertyB: 'value_b'
        deviceB:
            propertyC: 'value_c'
        ...
    Configuration2:
        deviceA:
            propertyA: 'value_d'
            propertyB: 'value_e'
        deviceB:
            propertyC: 'value_f'
        ...
    ...
ConfigGroupB:
    Configuration1:
        deviceC:
            propertyA: 'value_g'
        ...
    ...
```

## Using groups and presets

Groups and presets are usually defined in your configuration (`.cfg`) file.  The
demo configuration has a few of them:

```python
from pymmcore_plus import CMMCorePlus

core = CMMCorePlus()
core.loadSystemConfiguration()  # demo config

core.getAvailableConfigGroups()
# ('Camera', 'Channel', 'Channel-Multiband', 'LightPath', 'Objective', 'System')
core.getAvailableConfigs("Channel")
# ('Cy5', 'DAPI', 'FITC', 'Rhodamine')

core.setConfig("Channel", "FITC")  # (1)!
core.getCurrentConfig("Channel")  # 'FITC'
```

1. This sets all of the properties in the `FITC` preset (and emits the
   [`configSet`][pymmcore_plus.PCoreSignaler.configSet] event).

To see what a preset actually does, use
[`getConfigData`][pymmcore_plus.CMMCorePlus.getConfigData].  It returns a
[`Configuration`][pymmcore_plus.Configuration] that can be indexed with
`(device, property)` keys, and iterated over as `(device, property, value)`
tuples:

```python
cfg = core.getConfigData("Channel", "DAPI")
cfg["Dichroic", "Label"]  # '400DCLP'
list(cfg)
# [('Dichroic', 'Label', '400DCLP'), ('Emission', 'Label', 'Chroma-HQ620'),
#  ('Excitation', 'Label', 'Chroma-D360'), ('Core', 'Shutter', 'White Light Shutter')]
```

## Defining presets

New presets are defined one setting at a time with
[`defineConfig`][pymmcore_plus.CMMCorePlus.defineConfig] (the group is created
if it doesn't exist yet), or all at once with a
[`ConfigGroup`](#pymmcore-plus-objects) object:

```python
core.defineConfig("Channel", "Brightfield", "Dichroic", "Label", "400DCLP")

# or, equivalently, with a ConfigGroup:
channel = core.getConfigGroupObject("Channel")
channel["Brightfield"] = {
    ("Dichroic", "Label"): "400DCLP",
    ("Emission", "Label"): "Chroma-HQ700",
}
channel.setConfig("Brightfield")
```

These changes only live in memory.  To keep them, save the whole system
configuration to a new file (which you can load next time with
`loadSystemConfiguration`):

```python
core.saveSystemConfiguration("my_config.cfg")
```

Pixel size presets work much the same way, with their own methods
([`definePixelSizeConfig`][pymmcore_plus.CMMCorePlus.definePixelSizeConfig],
[`getPixelSizeConfigData`][pymmcore_plus.CMMCorePlus.getPixelSizeConfigData],
etc...), except that you don't set them yourself.  The core picks the one that
matches the current state of the microscope.  With the demo config, for example,
`core.setConfig("Objective", "20X")` changes
[`getCurrentPixelSizeConfig()`][pymmcore_plus.CMMCorePlus.getCurrentPixelSizeConfig]
to `'Res20x'` and [`getPixelSizeUm()`][pymmcore_plus.CMMCorePlus.getPixelSizeUm]
to `0.5`.

## `pymmcore-plus` objects

MMCore and pymmcore's
[configuration](https://micro-manager.org/apidoc/MMCore/latest/class_configuration.html)
object implements a basic container interface, but with custom method
names like `addSetting`, `getSetting`, and `deleteSetting`.

`pymmcore-plus` provides a [`Configuration`][pymmcore_plus.Configuration]
subclass that supports mapping-style indexing, where the keys are 2-tuples of
`(deviceLabel, propertyLabel)` and the values are the property values:
`cfg["Camera", "Exposure"]`, `cfg["Camera", "Exposure"] = "10"` and
`del cfg["Camera", "Exposure"]` all work.  (Note, however, that iterating over a
`Configuration` object behaves like iterating over a list of 3-tuples
`(deviceLabel, propertyLabel, value)`, not a dict, and there are no `keys()` or
`items()` methods.  Use `cfg.dict()` if you want a nested dict.)  All of the
`CMMCorePlus` methods that return a configuration return this subclass, unless
you pass `native=True`.

`pymmcore-plus` also offers a [`ConfigGroup`][pymmcore_plus.ConfigGroup] object
(returned by
[`getConfigGroupObject`][pymmcore_plus.CMMCorePlus.getConfigGroupObject]),
which is a [`MutableMapping`][collections.abc.MutableMapping] where the keys are
[Configuration
Preset](https://micro-manager.org/Micro-Manager_Configuration_Guide#configuration-presets)
names and the values are `Configuration` objects.

See [`Configuration`][pymmcore_plus.Configuration] and
[`ConfigGroup`][pymmcore_plus.ConfigGroup] for the full API.  The related core
methods are in the *Config groups & presets* section of the
[`CMMCorePlus` method summary][cmmcoreplus-config-groups-presets].

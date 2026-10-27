# Events

There are two objects that emit events in `pymmcore-plus`.  The `CMMCorePlus`
object emits the [`PCoreSignaler`][pymmcore_plus.PCoreSignaler] signals at
`core.events` when the state of the microscope changes, and the `MDARunner` emits
the [`PMDASignaler`][pymmcore_plus.mda.PMDASignaler] signals at
`core.mda.events` as an acquisition sequence progresses.

See [Events and Callbacks](../guides/events.md) for how to connect callbacks,
choosing the Qt or psygnal backend, and which thread your callbacks run on.

::: pymmcore_plus.PCoreSignaler
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false
      filters: ["^(?!_|xY|sL).*"]

::: pymmcore_plus.mda.PMDASignaler
    options:
      heading_level: 2
      show_root_full_path: false
      summary: false

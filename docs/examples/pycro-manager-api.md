# Pycro-Manager-Style API

If you have been using Pycro-Manager and are familiar with its API,
the following example may be useful to see what a Pycro-Manager-like
API would look like implemented on the pymmcore-plus engine.  It converts
Pycro-Manager's event dicts to [`useq.MDAEvent`][] objects, and most of its
acquisition hooks to methods of a custom [`MDAEngine`][pymmcore_plus.mda.MDAEngine]
subclass (see [Custom Acquisition Engines](../guides/custom_engine.md)).

!!! warning

    This is not presented as a "suggestion", but rather as an
    educational example.  If you are considering pymmcore-plus
    for a pure-python acquisition workflow, consider using the
    `pymmcore` and `pymmcore-plus` APIs directly.

```python title="pycro-api.py"
--8<-- "examples/pycro-api.py"
```

# CMMCorePlus

The main object in `pymmcore_plus` is the `pymmcore_plus.CMMCorePlus` class.
`CMMCorePlus` is a subclass of
[`pymmcore.CMMCore`](https://github.com/micro-manager/pymmcore) with additional
functionality, and some overrides for the sake of convenience or fixed behavior.

## CMMCorePlus API summary

This table presents all methods available in the `CMMCorePlus` class, and
indicates which methods are unique to `CMMCorePlus` (:sparkles:) and which
methods are overridden from `CMMCore` (:material-plus-thick:).  Below the
table, the signatures of all methods are presented, broken into a
`CMMCorePlus` section and a `CMMCore` section (depending on whether the
method is implemented in `CMMCorePlus` or not).

<small>
:material-plus-thick:  *This method is overridden by `CMMCorePlus`.*  
:sparkles:  *This method only exists in `CMMCorePlus`.*  
:prohibited:  *This method is deprecated.*  
</small>

::: pymmcore_plus.core._mmcore_plus.CMMCorePlus
    options:
        summary: true
        inherited_members: true
        heading_level: 3

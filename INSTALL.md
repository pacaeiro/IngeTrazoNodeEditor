# Installation Guide

## Quick start

Copy the `node_editor/` folder into IngeTrazo's plugin directory and restart IngeTrazo.
No external `pip install` step is required for the core functionality.

```
%APPDATA%\ingetrazo\plugins\node_editor\
```

---

## Bundled / Vendored Libraries

The following libraries are **already included** inside the plugin folder.
They work out-of-the-box with IngeTrazo's internal Python — no installation needed.

| Folder / File | Version | Purpose |
|---|---|---|
| `py_straight_skeleton/` | 0.1.0 | True straight-skeleton algorithm — produces correct hip roofs with courtyard holes |
| `euclid3.py` | 0.1 | 2-D/3-D geometry primitives used by polyskel |
| `polyskel.py` | — | Alternative straight-skeleton implementation (fallback) |

> **Why vendored?**  
> IngeTrazo ships a frozen internal Python interpreter. Running `pip install`
> into an external Python does **not** affect IngeTrazo's runtime.  
> Vendoring places the libraries directly on `sys.path` at plugin startup,
> making them always available regardless of the host Python environment.

---

## Optional External Library — Shapely

**Shapely** is used by the **Roof from Surface** node to compute precise polygon
offsets when `Overhang > 0`. Without it the node skips buffering and still
produces a correct roof (just without the overhang expansion).

### Install into IngeTrazo's miniconda environment

```powershell
conda activate base          # or the env IngeTrazo uses
conda install -c conda-forge shapely
```

### Install via pip

```powershell
pip install shapely
```

### Verify

```python
from shapely.geometry import Polygon
print(Polygon([(0,0),(1,0),(1,1),(0,1)]).buffer(0.1))
```

If the output is a geometry object, Shapely is active. If IngeTrazo's Python
still can't find it, vendor it the same way: copy the installed `shapely/`
package folder into the `node_editor/` directory.

---

## Dependency Summary

| Library | Required? | Status |
|---|---|---|
| `PySide6` | ✅ Required | Bundled with IngeTrazo |
| `py_straight_skeleton` | ✅ Required (hip roofs) | **Vendored in plugin** |
| `euclid3` | ✅ Required (by polyskel) | **Vendored in plugin** |
| `polyskel` | ⚙️ Fallback only | **Vendored in plugin** |
| `shapely` | ⚠️ Optional (overhang) | Install separately if needed |

# liblouis (vendored)

A vendored copy of [liblouis](https://liblouis.io/) used by brf2ebrl to back-translate braille (for example page numbers in the eBraille page list). It is packaged here because liblouis does not publish its Python bindings to PyPI; the `louis` and `pylouis` projects on PyPI are not liblouis and must not be used.

Liblouis is licensed under the LGPL 2.1 or later, see [COPYING.LESSER](COPYING.LESSER).

## Contents

All files come from liblouis v3.39.0.

* `src/louis/__init__.py`: the official ctypes bindings (`python/louis/__init__.py.in` in the source tree). The only change is the library loading, marked with a `Convert2EBRL` comment.
* `src/louis/liblouis.dll`: from `bin/` in `liblouis-3.39.0-win64.zip` (sha256 `64d669ac30f1411e0023b1cecc81c7a7b5374678ee41302c95ac8c7c8fbc6591`, matching the GitHub release asset digest). It only depends on `KERNEL32.dll` and `msvcrt.dll`.
* `src/louis/tables/`: `unicode.dis`, `en-ueb-g1.ctb` and the tables they include, from `share/liblouis/tables/` in the same zip.
* `src/louis/bundled.py`: helper giving absolute paths to the bundled tables.

On platforms other than Windows the bindings load a system installed liblouis, but still use the bundled tables.

## Updating

1. Download `liblouis-<version>-win64.zip` from the [liblouis releases](https://github.com/liblouis/liblouis/releases) and check its sha256 against the release asset digest.
2. Replace `liblouis.dll` and the files in `tables/` (add any newly included tables).
3. Replace `__init__.py` with `python/louis/__init__.py.in` from the matching tag and reapply the library loading change.
4. Update the version in `pyproject.toml` and this README, then run `uv lock`.

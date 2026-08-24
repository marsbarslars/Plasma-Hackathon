# Plasma-Hackathon

WarpX experiments on macOS/arm64. Single-node, no MPI, OpenMP threading, 3D only.

Upstream docs: <https://warpx.readthedocs.io/en/latest/index.html>
Vendored WarpX has its own agent notes at `vendor/warpx/CLAUDE.md` — those describe
building WarpX standalone under conda and do **not** apply here. Use the fish
functions below instead.

## Layout

```
pyproject.toml           uv project (package = false); pywarpx sourced from vendor/warpx
.venv/                   python 3.12
vendor/warpx/            WarpX git checkout (gitignored — not a submodule, see Caveats)
vendor/warpx/build/      standalone CMake/Ninja build → bin/warpx.3d
scripts/animate_mirror.py
runs/<name>/             one directory per simulation, run from inside it
```

## Environment

There are two independent WarpX builds. Neither rebuilds the other.

| What | Built by | Used by |
| --- | --- | --- |
| `pywarpx` (PICMI/Python) | `warpx-sync` / `warpx-rebuild` | `import pywarpx` in `.venv` |
| `warpx.3d` (executable) | `warpx-build` | `warpx3d` |

After updating `vendor/warpx`, run **both** `warpx-rebuild` and `warpx-build`.

Fish functions live one-per-file in `~/.config/fish/functions/` and autoload; see
`fish_ref.md` for the source.

- `warpx-root` — walks up for `vendor/warpx` + `pyproject.toml`, or honours `$WARPX_PROJECT`.
  Everything else builds on it, so the functions work from any subdirectory.
- `warpx-sync [uv args]` — `uv sync` with `WARPX_MPI=OFF`, `WARPX_COMPUTE=OMP`,
  `WARPX_DIMS=3`, Homebrew `libomp` and prefix.
- `warpx-rebuild` — `warpx-sync --reinstall-package pywarpx`; forces the extension rebuild.
- `warpx-build [cmake args]` — CMake/Ninja into `vendor/warpx/build`, `-DWarpX_MPI=OFF
  -DWarpX_COMPUTE=OMP -DWarpX_DIMS=3 -DWarpX_FFT=ON`.
- `warpx3d [args]` — runs `vendor/warpx/build/bin/warpx.3d`.

Requires Homebrew `libomp`, `cmake`, `ninja`, and `uv`.

## Running

From inside the run directory, so diagnostics land in `./diags/`:

```fish
cd runs/magnetic-mirror
warpx3d inputs_3d_magnetic_mirror.txt
```

WarpX writes `warpx_used_inputs` next to the output — it lists every parameter the
run actually consumed, with `my_constants` expanded. **Diff it against the input deck
to catch typo'd keys**, which WarpX ignores silently rather than erroring.

Then animate:

```fish
python ../../scripts/animate_mirror.py --mp4 mirror.mp4
```

`animate_mirror.py` reads `diags/diag1` via `openpmd-viewer` and renders `|B|`
isosurfaces plus proton trails in PyVista, camera down −y so the mirror axis is
horizontal. `--gif`/`--mp4` render offscreen; no flag opens an interactive window.
It draws 60 of the 1000 tracks by default (`--n-tracks`) — all 1000 is unreadable.
Tracks are matched by particle `id` and NaN-filled once a particle is absorbed, so
boundary losses do not corrupt the trails.

## runs/magnetic-mirror

Single-particle orbit tracing in a prescribed mirror field — **not** a self-consistent
plasma. `do_not_deposit = 1` and `initialize_self_fields = 0` make the protons test
particles, so the electrostatic solver has no source and only the applied B matters.

- Domain 2 × 2 × 5 m, 40³ cells, 500 steps at `dt = 4.4e-7 s`, PEC fields, absorbing particles.
- 1000 protons, Gaussian beam at the midplane (z = 2.5 m), uniform momentum spread.
- Field from `example-femm-3d.h5` (FEMM export, openPMD, 47³ over x,y ∈ [-1.15, 1.15],
  z ∈ [-0.375, 5.375] — covers the domain). Applied straight to particles via
  `particles.B_ext_particle_init_style = read_from_file`.

Resolution sanity check, worth redoing if you change `dt`, the field, or the momenta:
on-axis `Bz` is ~5 mT at the ends and ~2 mT at the midplane, so the **mirror ratio is
~2.5**. At `uz = 1.34e-4` protons move ~40 km/s, giving a gyroperiod of ~2.2e-5 s —
about **50 steps per orbit**, ~10 orbits over the run. Gyroradius ~0.1 m, about two
transverse cells.

`diag1` writes openPMD every step (501 files) with `Bx By Bz` on the grid plus the
proton species. The grid `B` matches the FEMM file (max ~8.9 mT), so the animation's
isosurfaces really are the mirror field.

Known dead line in the deck: `diag1.proton.variables` — the species is `protons`, so
the key is ignored and defaults are written instead. Harmless (the defaults cover
everything the animation reads) but it is not doing what it looks like.

## Caveats

- `vendor/` is gitignored, so a fresh clone has no WarpX and `uv sync` will fail.
  Re-clone WarpX into `vendor/warpx` by hand, or convert it to a git submodule.
- `runs/*/diags/` is gitignored — 501 openPMD files per run is far too much to track.
  Committed run artifacts are the input deck and the FEMM field file.

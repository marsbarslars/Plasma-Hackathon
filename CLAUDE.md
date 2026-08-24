# Plasma-Hackathon

WarpX experiments. Single-node, no MPI, 3D only, on CPU (OpenMP or serial) or an
NVIDIA GPU. Developed on macOS/arm64; the tooling does not assume it.

Upstream docs: <https://warpx.readthedocs.io/en/latest/index.html>
Vendored WarpX has its own agent notes at `vendor/warpx/CLAUDE.md` — those describe
building WarpX standalone under conda and do **not** apply here. Use the helpers below.

## Layout

```
pyproject.toml           uv project (package = false); pywarpx sourced from vendor/warpx
.venv/                   python 3.12
vendor/warpx/            WarpX submodule, tracking upstream `development`
vendor/warpx/build/      standalone CMake/Ninja build → bin/warpx.3d
scripts/warpx.py         the helper; stdlib-only Python, runs before .venv exists
scripts/warpx            POSIX wrapper
scripts/warpx.cmd        Windows wrapper
scripts/animate_mirror.py    3D orbit render (PyVista)
scripts/plot_mirror.py       mirror physics figure (matplotlib)
scripts/plasma/              shared analysis: field maps, particles, velocity space
docs/nbi-plan.md             NBI implementation plan
runs/<name>/             one directory per simulation, run from inside it
```

## Getting the source

`vendor/warpx` is a git submodule pinned to a specific upstream commit, so clone with:

```bash
git clone --recurse-submodules https://github.com/marsbarslars/Plasma-Hackathon.git
```

If you already cloned without it, or the directory is empty:

```bash
git submodule update --init --recursive
```

To move to newer upstream WarpX, `git submodule update --remote vendor/warpx`, then
rebuild both targets and commit the changed submodule pointer.

## Environment

There are two independent WarpX builds. Neither rebuilds the other.

| What | Built by | Used by |
| --- | --- | --- |
| `pywarpx` (PICMI/Python) | `warpx sync` / `warpx rebuild` | `import pywarpx` in `.venv` |
| `warpx.3d` (executable) | `warpx build` | `warpx run` |

After changing the submodule pointer, run **both** `warpx rebuild` and `warpx build`.

Run them as `./scripts/warpx <command>`, or `scripts\warpx.cmd <command>` on Windows.
Put `scripts/` on `$PATH` to drop the prefix.

Requires `cmake`, `ninja`, a C++ compiler, `uv`, and Python 3.8+ on `PATH` for the
helper itself. No specific package manager, and no shell beyond `/bin/sh` or `cmd`.

### Why Python and not shell

The helper was bash, which cannot run on Windows without extra tooling, and the
project already depends on Python. Rewriting it as one stdlib-only module avoids
maintaining parallel copies per platform — the same mistake the earlier fish/bash
split made. It targets Python 3.8+ and imports nothing outside the standard library,
because `warpx sync` is what *creates* `.venv`; it cannot depend on it. The two
wrappers do nothing but locate an interpreter and hand off.

### How configuration resolves

One direction, most explicit first: **command-line flag > environment variable >
autodetection**. `warpx info` prints the resolved result without building anything,
and is the first thing to run when a build misbehaves.

`--compute` picks the backend. Autodetection is `cuda_available()` first — which
requires an `nvcc`, not merely a driver, since a machine that can *run* CUDA cannot
necessarily *compile* it — then per-OS: Windows gets `NOACC`, macOS gets `OMP` only
if libomp is actually found, Linux gets `OMP`. Windows is serial because MSVC
implements only OpenMP 2.0 and WarpX's own Windows CI builds `NOACC`.

`--fft` follows the backend: `ON` for CUDA (cuFFT ships with the toolkit), `OFF` on
Windows (FFTW is rarely present on a stock toolchain), `ON` otherwise. Note this
applies to the standalone build only; pywarpx keeps upstream's own default of `OFF`,
so the two targets differ here.

`OpenMP_ROOT` is only probed on macOS — GCC ships libgomp and MSVC has `/openmp`
built in, so elsewhere the compiler already knows. The probe walks conda,
`$HOMEBREW_PREFIX`, `brew --prefix libomp`, the Homebrew and linuxbrew defaults,
MacPorts, `/usr/local` and `/usr`, accepting the first prefix that genuinely holds
`include/omp.h` beside a `libomp`/`libgomp` rather than one that merely exists.
`CMAKE_PREFIX_PATH` gets the same treatment, plus `$CONDA_PREFIX/Library` and
`$VCPKG_ROOT` on Windows; it is prepended to and deduplicated, never replaced.
An exported `OpenMP_ROOT` or `CMAKE_PREFIX_PATH` skips probing entirely.

### Details worth knowing

`WarpX_DIMS` is `3` but WarpX names the binary `warpx.3d` — `DIMS` and `DIM_SUFFIX`
are separate constants for exactly that reason. CMake symlinks the fully-qualified
name (`warpx.3d.NOMPI.OMP.DP.PDP.OPMD.FFT.EB.QED`) to the short one, but that step
needs privileges Windows withholds by default, so `solver_path()` falls back to
globbing `warpx.3d.*` and taking the newest.

Argument splitting is manual, not `argparse.REMAINDER`, which refuses to start
collecting on an option-like token and would reject `warpx sync --reinstall`.
Everything after the subcommand is forwarded verbatim; a helper flag found *after*
the subcommand is an error, since `warpx build --compute cuda` would otherwise hand
`--compute` to cmake and quietly build the wrong backend.

`cmake --build` is always passed `--config Release`: multi-config generators (Visual
Studio, Xcode) require it and single-config ones ignore it. Ninja is used when
present, otherwise CMake picks the platform default.

Switching backends reconfigures the same build directory, so it forces a full
recompile.

### Untested paths

Everything here runs on macOS/arm64 with OpenMP. Linux, Windows and CUDA are written
from WarpX's documented support and CI configuration. `scripts/test_warpx.py` covers
the decisions by faking the platform — the full OS × CUDA × libomp matrix, the
precedence rules, and the solver-lookup fallbacks — but a passing suite only means the
*logic* is right; no end-to-end build has been done on those platforms. Windows is the weakest: upstream's Windows CI is
disabled (`if: 0`, citing WarpX issue #5230), so WarpX itself may not build cleanly
there regardless of this tooling.

## Running

From inside the run directory, so diagnostics land in `./diags/`:

```bash
cd runs/magnetic-mirror
../../scripts/warpx run inputs_3d_magnetic_mirror.txt
```

WarpX writes `warpx_used_inputs` next to the output — it lists every parameter the
run actually consumed, with `my_constants` expanded. **Diff it against the input deck
to catch typo'd keys**, which WarpX ignores silently rather than erroring.

Then animate:

```bash
../../.venv/bin/python ../../scripts/animate_mirror.py --mp4 mirror.mp4
```

`animate_mirror.py` reads `diags/diag1` via `openpmd-viewer` and renders **B field
lines** plus particle trails in PyVista, camera down −y so the mirror axis is
horizontal. Lines are seeded on concentric mid-plane rings and traced both ways, so
each one runs the length of the machine and the throat convergence is visible;
`--isosurfaces` switches back to `|B|` contours. `--gif`/`--mp4`/`--png` render
offscreen; no flag opens an interactive window. It draws 60 tracks by default
(`--n-tracks`) — all of them is unreadable.

Offscreen renders also composite a chart panel on the right: a **static** `|B|` scale
bar — the legend for the field-line colouring — and the evolving (v∥, v⊥)
distribution over **every** particle in the frame, with the loss cone drawn on.
`--no-charts` gives the bare 3D view.

Colour does two jobs, so it uses two maps rather than overloading one: field strength
stays on cividis (matching the lines the bar labels), particle density uses an
inferno ramp whose first entry is replaced by the panel background so empty velocity
space reads as empty, and the loss cone is a cyan absent from both.

The density panel is smoothed and its ceiling calibrated over six frames spread
through the run. Drawing raw counts on a ceiling locked to frame 0 produces
convincing-looking contour bands that are entirely Poisson noise — roughly four
counts per bin stretched across ~18 integer levels, with the top 14% clipped flat. Charted frames are composited in numpy and written with `imageio`
rather than PyVista's own movie writer, since the panel is matplotlib; the render
window is sized to a multiple of 16 so ffmpeg does not silently resize.

The camera uses **parallel projection**. Under perspective, a long thin machine
draws the near and far faces of the bounding box at noticeably different sizes,
which reads as field lines escaping the domain when they are merely nearer.
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
field lines really are the mirror field.

Known dead line in the deck: `diag1.proton.variables` — the species is `protons`, so
the key is ignored and defaults are written instead. Harmless (the defaults cover
everything the animation reads) but it is not doing what it looks like.

## runs/mirror-validation

Phase 0 of `docs/nbi-plan.md`, and the case to copy for new work — `magnetic-mirror`
is kept only for history. Isotropic 30 keV deuterons in the same FEMM field scaled
×100 (0.149 T midplane, 0.461 T throats). On-axis mirror ratio 3.086, loss cone
34.7°; the per-particle criterion `sin²θ < B_birth/B_max` predicts 97.1% of fates.
See that directory's README for results and reproduction.

Four things bitten by, all of which look like physics errors:

- **Mesh arrays are written `(z,y,x)`.** Indexing as `(x,y,z)` made the mirror ratio
  read 1.28 instead of 3.09. `scripts/plasma/field.py` normalises on load; use it
  rather than reading openPMD meshes by hand.
- **Custom particle attributes need `addRealAttributes` first**, or the diagnostic
  aborts. Their parser reports `ux,uy,uz` as γv in m/s, not the documented γβ.
- **Reduced diagnostics go to `diags/reducedfiles/`**, and a second run in the same
  directory overwrites them unless `reduced_diags.path` is set.
- **Diagnostic interval has to resolve the gyro-orbit for 3D rendering.** At 4 ns
  steps the throat gyroperiod is ~71 steps, so a 200-step interval aliases orbits
  into zigzags. Render from a short, finely sampled run instead.

Parameter sweeps need no templating: WarpX takes ParmParse overrides on the command
line, e.g. `warpx run inputs max_step=2400 ions.npart=400`.

## runs/nbi-angle-scan

Phase 2: a directed 30 keV deuterium beam injected at angles from 0° to 90°. Only
the fast-ion leg is modelled — a neutral beam flies straight and is invisible to
PIC, so ions are injected at their birth points.

`gaussian_beam` is built along +z and rotated bodily to the aiming angle.
**`do_gaussian_beam_rotation_momenta` is the load-bearing flag** — without it only
the footprint turns and the beam still flies along +z. `x/y/z_rms` are applied
*before* rotation, so specify them axis-aligned.

Result: a sharp transition with a 50% crossing at 33.2°, against a loss cone of
34.70° computed with the on-axis `B_max` and 24.12° with the global maximum. The
observed value sits between the bounds because `rg/L ≈ 0.24` here — μ is only
approximately conserved and off-axis orbits see more field than the on-axis
criterion assumes. See that directory's README.

No vessel yet, so radial losses are the domain box, not a vacuum vessel.

## runs/vessel-mirror

Phase 1: an embedded-boundary vacuum vessel around the Phase 0 mirror, scanned over
radius. EB works with `grid_type = collocated` and the labframe electrostatic
solver. `boundary.particle_eb = Absorbing`, and `ions.save_particles_at_eb = 1`
gives scraped particles with surface normals `nx, ny, nz` plus `timeScraped`.

Confinement rises to 0.795 at a 0.9 m vessel, matching Phase 0's bare-box number.
Axial losses barely move with radius, so the wall cost is additive to the loss cone.
Wall load peaks at the **midplane**, not the throats — gyroradius goes as 1/B, so
orbits are widest where the field is weakest.

Two traps: a vessel narrower than the source silently deletes particles born outside
it at initialisation (they reach no loss channel — normalise by the step-0
`ParticleNumber`, not by `npart`), and reading the scraping diagnostic before WarpX
has finished flushing gives short counts that mimic a physics discrepancy.

## Caveats

- `runs/*/diags/` is gitignored — 501 openPMD files per run is far too much to track.
  Committed run artifacts are the input deck and the FEMM field file.
- `vendor/warpx/build/` is ignored by WarpX's own `.gitignore`, so build output never
  shows up as submodule dirt. A modified submodule pointer in `git status` means the
  checkout actually moved.

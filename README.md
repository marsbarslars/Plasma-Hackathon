# Plasma-Hackathon

Particle simulations with [WarpX](https://warpx.readthedocs.io/en/latest/index.html),
configured for single-node runs: no MPI, 3D only, on CPU or an NVIDIA GPU.

Currently one experiment — `runs/magnetic-mirror`, which traces proton orbits through
a magnetic mirror field exported from FEMM and renders them as an animation.

## Requirements

- `cmake`, `ninja`, and a C++ compiler
- Python 3.8+ on `PATH` to run the helper; Python 3.12 for the simulations, which
  [`uv`](https://docs.astral.sh/uv/) will fetch
- For CPU threading: an OpenMP runtime. GCC and MSVC already have one; macOS needs
  `libomp` separately, because AppleClang ships none.
- For GPU: the CUDA toolkit, i.e. an actual `nvcc`, not just a driver

No particular package manager is assumed — Homebrew, MacPorts, conda, vcpkg and
distro packages all work. If something lives somewhere unusual, point at it and the
probing is skipped:

```bash
export OpenMP_ROOT=/path/to/libomp/prefix
```

`CMAKE_PREFIX_PATH` is honoured the same way — it is prepended to, never replaced.

## Setup

WarpX is a submodule, so clone recursively:

```bash
git clone --recurse-submodules https://github.com/marsbarslars/Plasma-Hackathon.git
cd Plasma-Hackathon
```

Already cloned without it? `git submodule update --init --recursive`.

Check what the helper detected before building anything:

```bash
./scripts/warpx info
```

That prints the compute backend, OpenMP prefix, generator and so on. If it looks
right, build. There are two independent builds — the Python bindings and the
standalone solver — and most workflows want both:

```bash
./scripts/warpx sync
```

```bash
./scripts/warpx build
```

`sync` creates `.venv` and builds `pywarpx`; `build` compiles the solver into
`vendor/warpx/build/bin/`. The first build of either takes a while — considerably
longer for CUDA.

On Windows use `scripts\warpx.cmd` in place of `./scripts/warpx`; the arguments are
identical.

## Choosing a backend

By default the backend is detected:

| Machine | Backend |
| --- | --- |
| CUDA toolkit present | `CUDA` |
| Linux | `OMP` |
| macOS with `libomp` | `OMP` |
| macOS without `libomp` | `NOACC` (serial) |
| Windows | `NOACC` (serial) |

CUDA wins wherever `nvcc` exists. A CUDA *driver* is not enough — plenty of machines
can run GPU binaries but not compile them, and guessing wrong there trades a working
build for a confusing failure.

Windows defaults to serial because MSVC only implements OpenMP 2.0 and WarpX's own
Windows CI builds `NOACC`. It is slower but it works; pass `--compute OMP` if your
Windows toolchain handles it.

Override with a flag or an environment variable — flag wins, then variable, then
detection:

```bash
./scripts/warpx --compute CUDA build
```

```bash
WARPX_COMPUTE=NOACC ./scripts/warpx build
```

`--mpi` and `--fft` work the same way. Switching backends reconfigures the same build
directory, so expect a full recompile.

## Running a simulation

Run from inside the run directory so diagnostics land in `./diags/`:

```bash
cd runs/magnetic-mirror
../../scripts/warpx run inputs_3d_magnetic_mirror.txt
```

Then render the result:

```bash
../../.venv/bin/python ../../scripts/animate_mirror.py --mp4 mirror.mp4
```

Omit `--mp4` for an interactive PyVista window, or pass `--gif`/`--png` instead. The
animation shows magnetic field lines with particle trails, viewed side-on so the
mirror axis runs horizontally, alongside two charts: a static `|B|` scale bar keying
the field-line colours, and the live (v∥, v⊥) distribution over all particles with
the loss cone marked. Pass `--isosurfaces` for `|B|` contours instead of field lines, or
`--no-charts` for the bare 3D view.

Diagnostic output is gitignored — 501 openPMD files per run is more than is worth
tracking. The input deck and the FEMM field file are committed, so runs reproduce.

## The helper

| Command | Does |
| --- | --- |
| `warpx info` | Print the detected configuration and build nothing. |
| `warpx root` | Print the project root. |
| `warpx sync` | Sync the uv environment, building `pywarpx`. |
| `warpx rebuild` | Force a `pywarpx` rebuild after the submodule moves. |
| `warpx build` | Build the standalone solver. |
| `warpx run` | Run the solver. |

Anything after the subcommand is forwarded verbatim to `uv`, `cmake` or the solver,
so the helper's own options go *before* it:

```bash
./scripts/warpx --compute CUDA build -DAMReX_CUDA_ARCH=8.6
```

Putting a helper option after the subcommand is an error rather than a silent
misconfiguration.

The commands work from any subdirectory and honour `$WARPX_PROJECT`. `scripts/warpx.py`
is the whole implementation — standard library only, since it has to run before
`.venv` exists — and the two wrappers just find a Python and hand off.

## Tests

The platform-dependent logic — backend selection, solver lookup, argument splitting —
is tested by faking the platform, so all three OS paths are covered from one machine:

```bash
python3 scripts/test_warpx.py
```

## Updating WarpX

```bash
git submodule update --remote vendor/warpx
```

Then rebuild **both** targets — `./scripts/warpx rebuild` and `./scripts/warpx build` —
and commit the moved submodule pointer.

## Portability caveats

Developed and tested on macOS/arm64 with OpenMP. The Linux, Windows and CUDA paths
are written from WarpX's documented support and its CI configuration, and the backend
selection logic is covered by tests, but they have not been run end to end here.

Windows is the least certain of these: WarpX's own Windows CI is currently disabled
upstream, so expect to do some work there rather than a clean first build.

## More

`CLAUDE.md` has the details: how the two builds differ, how detection resolves, the
physics parameters behind the magnetic mirror run and how to sanity-check them, and
known quirks in the input deck.

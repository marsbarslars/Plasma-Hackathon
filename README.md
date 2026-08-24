# Plasma-Hackathon

Particle simulations with [WarpX](https://warpx.readthedocs.io/en/latest/index.html),
configured for single-node runs: no MPI, OpenMP threading, 3D only. Developed on
macOS/arm64; the scripts do not assume it.

Currently one experiment — `runs/magnetic-mirror`, which traces proton orbits through
a magnetic mirror field exported from FEMM and renders them as an animation.

## Requirements

- `cmake`, `ninja`, and a C++ compiler
- An OpenMP runtime — on macOS that means `libomp`, since AppleClang does not ship one
- [`uv`](https://docs.astral.sh/uv/)
- Python 3.12 (uv will fetch it)

Any package manager works. The scripts probe conda, Homebrew, MacPorts and the usual
system prefixes for `libomp`, so `brew install libomp cmake ninja`, `port install
libomp cmake ninja`, or a conda environment are all fine. If yours lives somewhere
unusual, point at it directly and the probing is skipped:

```bash
export OpenMP_ROOT=/path/to/libomp/prefix
```

`CMAKE_PREFIX_PATH` is honoured the same way — the scripts prepend to it, never
replace it.

## Setup

WarpX is a submodule, so clone recursively:

```bash
git clone --recurse-submodules https://github.com/marsbarslars/Plasma-Hackathon.git
cd Plasma-Hackathon
```

Already cloned without it? `git submodule update --init --recursive`.

There are two builds, and they are independent — the Python bindings and the
standalone solver. Most workflows want both:

```bash
./scripts/warpx-sync
```

```bash
./scripts/warpx-build
```

`warpx-sync` creates `.venv` and builds `pywarpx` from the submodule; `warpx-build`
compiles `vendor/warpx/build/bin/warpx.3d`. The first build of either takes a while.

## Running a simulation

Run from inside the run directory so diagnostics land in `./diags/`:

```bash
cd runs/magnetic-mirror
../../scripts/warpx3d inputs_3d_magnetic_mirror.txt
```

Then render the result:

```bash
../../.venv/bin/python ../../scripts/animate_mirror.py --mp4 mirror.mp4
```

Omit `--mp4` for an interactive PyVista window, or pass `--gif` instead. The animation
shows `|B|` isosurfaces with proton trails, viewed side-on so the mirror axis runs
horizontally.

Diagnostic output is gitignored — 501 openPMD files per run is more than is worth
tracking. The input deck and the FEMM field file are committed, so runs reproduce.

## Scripts

| Command | Does |
| --- | --- |
| `scripts/warpx-root` | Print the project root. |
| `scripts/warpx-sync` | Sync the uv environment, building `pywarpx`. Extra args go to `uv sync`. |
| `scripts/warpx-rebuild` | Force a `pywarpx` rebuild after the submodule moves. |
| `scripts/warpx-build` | Build the standalone `warpx.3d` executable. Extra args go to CMake. |
| `scripts/warpx3d` | Run `warpx.3d`. |

They work from any subdirectory, and honour `$WARPX_PROJECT` if you want to point them
at a project explicitly. Put `scripts/` on your `$PATH` to drop the `../../`.

They are plain bash with no package manager assumed, written against bash 3.2 so the
version macOS ships works without upgrading.

## Updating WarpX

```bash
git submodule update --remote vendor/warpx
```

Then rebuild **both** targets — `./scripts/warpx-rebuild` and `./scripts/warpx-build` —
and commit the moved submodule pointer.

## More

`CLAUDE.md` has the details: how the two builds differ, the physics parameters behind
the magnetic mirror run and how to sanity-check them, and known quirks in the input deck.

#!/usr/bin/env bash
# Shared helpers for the warpx-* scripts. Source, don't execute.
#
# Written for bash 3.2 (what macOS ships), so no associative arrays, no `${x^^}`,
# and no `set -u` — bash 3.2 treats "$@" with zero arguments as an unset variable.

set -eo pipefail

# Locate the project root: $WARPX_PROJECT, else walk up from $PWD, else walk up
# from this script's own directory (covers being called from outside the project).
warpx_root() {
    if [ -n "$WARPX_PROJECT" ]; then
        printf '%s\n' "$WARPX_PROJECT"
        return 0
    fi

    local start dir
    for start in "$PWD" "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"; do
        dir=$(cd "$start" && pwd -P)
        while [ "$dir" != / ]; do
            if [ -d "$dir/vendor/warpx" ] && [ -f "$dir/pyproject.toml" ]; then
                printf '%s\n' "$dir"
                return 0
            fi
            dir=$(dirname "$dir")
        done
    done

    echo "warpx-root: not inside a WarpX project; set \$WARPX_PROJECT" >&2
    return 1
}

# Homebrew supplies libomp on macOS. Elsewhere, respect whatever is already set
# rather than failing outright.
# True if $1 looks like a prefix containing an OpenMP runtime.
warpx_is_omp_prefix() {
    local d="$1" lib
    if [ ! -f "$d/include/omp.h" ]; then
        return 1
    fi
    for lib in libomp.dylib libomp.so libomp.a libgomp.dylib libgomp.so; do
        if [ -f "$d/lib/$lib" ]; then
            return 0
        fi
    done
    return 1
}

# Candidate prefixes for the OpenMP runtime, most specific first. Homebrew is one
# entry among several, not a requirement: MacPorts, conda, Nix and distro packages
# all land somewhere on this list, and $OpenMP_ROOT short-circuits it entirely.
warpx_omp_candidates() {
    if [ -n "$CONDA_PREFIX" ]; then
        printf '%s\n' "$CONDA_PREFIX"
    fi
    if [ -n "$HOMEBREW_PREFIX" ]; then
        printf '%s\n' "$HOMEBREW_PREFIX/opt/libomp" "$HOMEBREW_PREFIX"
    fi
    if command -v brew >/dev/null 2>&1; then
        brew --prefix libomp 2>/dev/null || true
    fi
    printf '%s\n' \
        /opt/homebrew/opt/libomp \
        /usr/local/opt/libomp \
        /opt/local \
        /usr/local \
        /usr
}

# Candidate prefixes for everything else CMake has to find (FFTW, HDF5, ADIOS...).
warpx_pkg_candidates() {
    if [ -n "$CONDA_PREFIX" ]; then
        printf '%s\n' "$CONDA_PREFIX"
    fi
    if [ -n "$HOMEBREW_PREFIX" ]; then
        printf '%s\n' "$HOMEBREW_PREFIX"
    fi
    if command -v brew >/dev/null 2>&1; then
        brew --prefix 2>/dev/null || true
    fi
    printf '%s\n' /opt/homebrew /opt/local /usr/local
}

warpx_prepend_prefix_path() {
    local d="$1"
    case ":$CMAKE_PREFIX_PATH:" in
        *":$d:"*) return 0 ;;   # already there
    esac
    if [ -n "$CMAKE_PREFIX_PATH" ]; then
        export CMAKE_PREFIX_PATH="$d:$CMAKE_PREFIX_PATH"
    else
        export CMAKE_PREFIX_PATH="$d"
    fi
}

# Set OpenMP_ROOT and CMAKE_PREFIX_PATH if they are not already set. Anything the
# caller exported wins outright — this only fills in blanks.
warpx_export_toolchain() {
    local d found

    if [ -z "$OpenMP_ROOT" ]; then
        found=""
        for d in $(warpx_omp_candidates); do
            if [ -n "$d" ] && warpx_is_omp_prefix "$d"; then
                found="$d"
                break
            fi
        done
        if [ -n "$found" ]; then
            export OpenMP_ROOT="$found"
        else
            echo "warpx: no OpenMP runtime found; set \$OpenMP_ROOT to its prefix" >&2
            echo "warpx:   macOS needs a separate libomp — AppleClang does not ship one" >&2
        fi
    fi

    # Prepend the first prefix that exists, so CMake can find FFTW and friends.
    # Harmless when the deps are in system paths; that is what /usr/local covers.
    for d in $(warpx_pkg_candidates); do
        if [ -n "$d" ] && [ -d "$d/lib" ] && [ -d "$d/include" ]; then
            warpx_prepend_prefix_path "$d"
            break
        fi
    done
}

warpx_ncpu() {
    if command -v sysctl >/dev/null 2>&1 && sysctl -n hw.ncpu >/dev/null 2>&1; then
        sysctl -n hw.ncpu
    elif command -v nproc >/dev/null 2>&1; then
        nproc
    else
        echo 4
    fi
}

# vendor/warpx is a submodule; a fresh clone without --recurse-submodules is empty.
warpx_require_submodule() {
    local root="$1"
    if [ ! -f "$root/vendor/warpx/CMakeLists.txt" ]; then
        echo "warpx: vendor/warpx is empty — run: git submodule update --init --recursive" >&2
        return 1
    fi
}

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
warpx_export_toolchain() {
    local brew_prefix
    if command -v brew >/dev/null 2>&1; then
        brew_prefix=$(brew --prefix)
        export OpenMP_ROOT="${OpenMP_ROOT:-$(brew --prefix libomp)}"
        # Prepend rather than overwrite, so an existing prefix path survives.
        if [ -n "$CMAKE_PREFIX_PATH" ]; then
            export CMAKE_PREFIX_PATH="$brew_prefix:$CMAKE_PREFIX_PATH"
        else
            export CMAKE_PREFIX_PATH="$brew_prefix"
        fi
    elif [ -z "$OpenMP_ROOT" ]; then
        echo "warpx: no brew found; set \$OpenMP_ROOT if OpenMP is not on the default path" >&2
    fi
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

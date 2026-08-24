# Fish functions

One file per function in ~/.config/fish/functions/.

## warpx-root.fish

```fish
function warpx-root --description 'Locate the WarpX project root'
    if set -q WARPX_PROJECT
        echo $WARPX_PROJECT
        return 0
    end

    set -l dir (pwd -P)
    while test "$dir" != /
        if test -d "$dir/vendor/warpx" -a -f "$dir/pyproject.toml"
            echo $dir
            return 0
        end
        set dir (path dirname $dir)
    end

    echo "warpx-root: not inside a WarpX project; set \$WARPX_PROJECT" >&2
    return 1
end
```

##warpx-sync.fish

```fish
function warpx-sync --description 'Sync the WarpX uv environment'
    set -l root (warpx-root); or return 1

    set -lx WARPX_MPI OFF
    set -lx WARPX_COMPUTE OMP
    set -lx WARPX_DIMS "3"
    set -lx OpenMP_ROOT (brew --prefix libomp)
    set -lx CMAKE_PREFIX_PATH (brew --prefix)

    uv sync --project $root $argv
end
```
## warpx-rebuild.fish

```fish
function warpx-rebuild --description 'Force a pywarpx rebuild from vendor/warpx'
    warpx-sync --reinstall-package pywarpx $argv
end
```
## warpx-build.fish

```fish
function warpx-build --description 'Build the standalone WarpX executable'
    set -l root (warpx-root); or return 1
    set -l src $root/vendor/warpx

    set -lx OpenMP_ROOT (brew --prefix libomp)
    set -lx --path CMAKE_PREFIX_PATH (brew --prefix) $CMAKE_PREFIX_PATH

    cmake -S $src -B $src/build -G Ninja \
        -DWarpX_MPI=OFF -DWarpX_COMPUTE=OMP -DWarpX_DIMS=3 -DWarpX_FFT=ON $argv
    and cmake --build $src/build -j (sysctl -n hw.ncpu)
end
```
## warpx3d.fish

```fish
function warpx3d --description 'Run the WarpX 3D solver'
    set -l root (warpx-root); or return 1
    set -l bin $root/vendor/warpx/build/bin/warpx.3d

    if not test -x $bin
        echo "warpx3d: not built — run warpx-build" >&2
        return 1
    end

    $bin $argv
end
```

Fish autoloads these; no source or shell restart needed.

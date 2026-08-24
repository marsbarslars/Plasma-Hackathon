#!/usr/bin/env python3
"""
Animate proton trajectories in the WarpX magnetic mirror example.

Run from the simulation directory (the one containing diags/).

    python animate_mirror.py                 # interactive window
    python animate_mirror.py --gif out.gif   # write an animated GIF
    python animate_mirror.py --mp4 out.mp4   # needs: uv pip install imageio-ffmpeg

The mirror axis (z) is rendered horizontally.
"""

import argparse

import numpy as np
import pyvista as pv
from openpmd_viewer import OpenPMDTimeSeries

# ---------------------------------------------------------------- parameters

DIAG_PATH = "diags/diag1"
N_TRACKS = 60      # particles to draw; all 1000 is unreadable
STRIDE = 2         # use every Nth iteration
TRAIL = 80         # trail length in frames; None = full history
ISOSURFACES = 4    # |B| contour levels


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--gif", metavar="PATH")
    p.add_argument("--mp4", metavar="PATH")
    p.add_argument("--path", default=DIAG_PATH)
    p.add_argument("--n-tracks", type=int, default=N_TRACKS)
    p.add_argument("--stride", type=int, default=STRIDE)
    return p.parse_args()


# ------------------------------------------------------------------ B field

def load_field(ts, iteration):
    """Return a PyVista ImageData of |B| with axes ordered (x, y, z)."""
    comps = {}
    for c in ("x", "y", "z"):
        comps[c], info = ts.get_field(field="B", coord=c, iteration=iteration)

    bmag = np.sqrt(comps["x"] ** 2 + comps["y"] ** 2 + comps["z"] ** 2)

    # openPMD stores array axes in file order, not necessarily (x, y, z).
    axes = [info.axes[i] for i in range(3)]
    bmag = np.transpose(bmag, [axes.index(a) for a in ("x", "y", "z")])

    coords = {a: getattr(info, a) for a in ("x", "y", "z")}
    origin = tuple(coords[a][0] for a in ("x", "y", "z"))
    spacing = tuple(
        (coords[a][1] - coords[a][0]) if len(coords[a]) > 1 else 1.0
        for a in ("x", "y", "z")
    )

    grid = pv.ImageData(dimensions=bmag.shape, origin=origin, spacing=spacing)
    grid["Bmag"] = bmag.ravel(order="F")
    return grid


# --------------------------------------------------------------- trajectories

def load_tracks(ts, iterations, n_tracks):
    """(n_frames, n_tracks, 3) array of positions; NaN where absorbed."""
    ids0 = ts.get_particle(["id"], species="protons", iteration=iterations[0])[0]
    keep = np.sort(ids0)[:n_tracks]          # stable subset across frames
    order = np.argsort(keep)
    sorted_keep = keep[order]

    tracks = np.full((len(iterations), len(keep), 3), np.nan)

    for k, it in enumerate(iterations):
        x, y, z, ids = ts.get_particle(
            ["x", "y", "z", "id"], species="protons", iteration=it
        )
        pos = np.searchsorted(sorted_keep, ids)
        pos_c = np.clip(pos, 0, len(sorted_keep) - 1)
        hit = sorted_keep[pos_c] == ids
        tracks[k, order[pos_c[hit]]] = np.column_stack([x[hit], y[hit], z[hit]])

    return tracks


def trail_mesh(tracks, frame, trail):
    """Polyline mesh of each particle's recent history up to `frame`."""
    start = 0 if trail is None else max(0, frame - trail)
    blocks = []
    for t in tracks[start : frame + 1].transpose(1, 0, 2):
        good = t[~np.isnan(t).any(axis=1)]
        if len(good) > 1:
            blocks.append(pv.lines_from_points(good))
    if not blocks:
        return None
    return pv.MultiBlock(blocks).combine()


def head_mesh(tracks, frame):
    pts = tracks[frame]
    pts = pts[~np.isnan(pts).any(axis=1)]
    return pv.PolyData(pts) if len(pts) else None


# ------------------------------------------------------------------- camera

def side_on_camera(plotter, bounds):
    """Look down -y so the mirror axis (z) runs horizontally across the view."""
    xmin, xmax, ymin, ymax, zmin, zmax = bounds
    cx, cy, cz = (xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2
    span = max(xmax - xmin, zmax - zmin)
    plotter.camera_position = [
        (cx, cy - 2.2 * span, cz),   # eye
        (cx, cy, cz),                # focal point
        (1.0, 0.0, 0.0),             # view up = +x  ->  z is horizontal
    ]


# --------------------------------------------------------------------- main

def main():
    args = parse_args()

    ts = OpenPMDTimeSeries(args.path)
    iterations = list(ts.iterations)[:: args.stride]
    if len(iterations) < 2:
        raise SystemExit(
            f"Only {len(iterations)} iteration(s) in {args.path}. "
            "Re-run WarpX with diag1.intervals = 1."
        )

    print(f"{len(iterations)} frames, {args.n_tracks} tracks")
    grid = load_field(ts, iterations[0])
    tracks = load_tracks(ts, iterations, args.n_tracks)

    off_screen = bool(args.gif or args.mp4)
    p = pv.Plotter(off_screen=off_screen, window_size=(1400, 700))
    p.set_background("black")

    p.add_mesh(
        grid.contour(isosurfaces=ISOSURFACES, scalars="Bmag"),
        scalars="Bmag", cmap="cividis", opacity=0.18,
        show_scalar_bar=False, name="field",
    )
    p.add_mesh(pv.Box(grid.bounds), style="wireframe",
               color="gray", opacity=0.3, name="box")

    side_on_camera(p, grid.bounds)

    if args.gif:
        p.open_gif(args.gif, fps=25)
    elif args.mp4:
        p.open_movie(args.mp4, framerate=30)
    else:
        p.show(interactive_update=True, auto_close=False)

    for frame in range(len(tracks)):
        trails = trail_mesh(tracks, frame, TRAIL)
        if trails is not None:
            p.add_mesh(trails, color="orange", line_width=1.5,
                       opacity=0.8, name="trails")

        heads = head_mesh(tracks, frame)
        if heads is not None:
            p.add_mesh(heads, color="red", point_size=8,
                       render_points_as_spheres=True, name="heads")

        p.add_text(f"step {iterations[frame]}", position="upper_left",
                   font_size=10, color="white", name="label")

        if off_screen:
            p.write_frame()
        else:
            p.update()

    if off_screen:
        p.close()
        print(f"wrote {args.gif or args.mp4}")
    else:
        p.show()


if __name__ == "__main__":
    main()

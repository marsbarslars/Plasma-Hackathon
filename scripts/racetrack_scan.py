#!/usr/bin/env python3
"""Beam-energy scan for a SLAM racetrack straight leg.

From inside runs/racetrack-leg:

    ../../.venv/bin/python ../../scripts/racetrack_scan.py --plot racetrack.png

The device sets a hard geometric limit that has nothing to do with the loss
cone: a fast ion's gyroradius has to fit the vessel bore. At the leg midplane
B = 0.103 T, so a 30 keV deuteron gyrates with r = 0.34 m in a 0.23 m bore and
walks into the wall regardless of its pitch.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plasma import confined_fraction, load_scraped  # noqa: E402

E_KEV = [3, 8, 15, 30]
Q = 1.602176634e-19
M_D = 2.014 * 1.66053907e-27
BORE = 0.230          # m, measured from SLAM_VV.stl
FIELD_FILE = "SLAM_vC5_warpX.h5"
STL_FILE = "SLAM_VV.stl"


def leg_axis_field(path=FIELD_FILE, yaxis=0.5421):
    import h5py
    f = h5py.File(path, "r")
    B = f["data/0/meshes/B"]
    off, sp = B.attrs["gridGlobalOffset"], B.attrs["gridSpacing"]
    bx, by, bz = (B[k][:] for k in "xyz")
    n = bx.shape
    X = off[0] + sp[0] * np.arange(n[0])
    Y = off[1] + sp[1] * np.arange(n[1])
    Z = off[2] + sp[2] * np.arange(n[2])
    j = int(np.argmin(np.abs(Y - yaxis)))
    k = int(np.argmin(np.abs(Z)))
    bmag = np.sqrt(bx[:, j, k] ** 2 + by[:, j, k] ** 2 + bz[:, j, k] ** 2)
    return X, bmag


def vessel_outline(path=STL_FILE):
    with open(path, "rb") as fh:
        fh.read(80)
        nb = struct.unpack("<I", fh.read(4))[0]
        d = np.frombuffer(fh.read(),
                          dtype=np.dtype([("n", "<3f4"), ("v", "<3,3f4"),
                                          ("a", "<u2")]), count=nb)
    return d["v"].astype(np.float64) / 1000.0     # mm -> m


def analyse(energies):
    rows = []
    for E in energies:
        t = f"E{E:g}"
        if not os.path.isdir(f"diags/{t}_reduced"):
            continue
        _, frac = confined_fraction(f"diags/{t}_reduced")
        s, w = load_scraped(f"diags/{t}_scraped", "ions", ())
        cnt = (lambda keys: int(np.isin(w, keys).sum())) if s is not None else (lambda k: 0)
        v = np.sqrt(2 * E * 1e3 * Q / M_D)
        rows.append(dict(E=E, final=float(frac[-1]) if frac is not None else np.nan,
                         wall=cnt(["eb"]), bend=cnt(["xlo", "xhi"]),
                         zedge=cnt(["zlo", "zhi"]),
                         rg=M_D * v / (Q * 0.1030)))
    return rows


def make_figure(rows, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    E = np.array([r["E"] for r in rows], float)
    final = np.array([r["final"] for r in rows])
    wall = np.array([r["wall"] for r in rows], float)
    bend = np.array([r["bend"] for r in rows], float)
    zedge = np.array([r["zedge"] for r in rows], float)
    n0 = wall + bend + zedge + final * 20000

    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9))
    fig.suptitle("SLAM racetrack · one straight mirror leg, real field and vessel",
                 fontsize=13, y=0.98)

    # -- A: the vessel we actually loaded --------------------------------
    ax = axes[0, 0]
    tris = vessel_outline()
    segs = []
    for t in tris[::3]:
        p = t[:, :2]
        segs += [[p[0], p[1]], [p[1], p[2]], [p[2], p[0]]]
    ax.add_collection(LineCollection(np.array(segs), linewidths=0.12,
                                     colors="#8894A8", alpha=0.6))
    ax.add_patch(plt.Rectangle((-0.75, -0.75), 1.5, 1.5, fill=False,
                               edgecolor="#B03A2E", lw=1.8, ls="--"))
    ax.text(0.0, 0.0, "modelled\nregion", ha="center", va="center",
            color="#B03A2E", fontsize=9)
    ax.set_xlim(-1.5, 1.5); ax.set_ylim(-0.95, 0.95)
    ax.set_aspect("equal")
    ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
    ax.set_title("A · Vessel, and the field's reach", loc="left", fontsize=11)

    # -- B: field along the leg ------------------------------------------
    ax = axes[0, 1]
    X, bmag = leg_axis_field()
    ax.plot(X, bmag, color="#00224E", lw=2)
    ratio = bmag.max() / bmag.min()
    lc = np.degrees(np.arcsin(np.sqrt(1 / ratio)))
    ax.fill_between(X, bmag, bmag.min(), alpha=0.12, color="#00224E")
    ax.set_xlabel("x along the leg [m]"); ax.set_ylabel("|B| on the leg axis [T]")
    ax.set_title("B · Each leg is a mirror", loc="left", fontsize=11)
    ax.annotate(f"$R_m$ = {ratio:.2f}\nloss cone {lc:.1f}$^\\circ$",
                xy=(0.5, 0.75), xycoords="axes fraction", ha="center",
                fontsize=10)

    # -- C: the geometric constraint -------------------------------------
    ax = axes[1, 0]
    Ec = np.linspace(0.5, 40, 200)
    v = np.sqrt(2 * Ec * 1e3 * Q / M_D)
    rg = M_D * v / (Q * 0.1030)
    ax.plot(Ec, rg, color="#00224E", lw=2, label="gyroradius at $90^\\circ$")
    ax.plot(Ec, rg * np.sin(np.radians(lc)), color="#A69D75", lw=1.8, ls="--",
            label=f"at the loss-cone edge ({lc:.0f}$^\\circ$)")
    ax.axhline(BORE, color="#B03A2E", lw=2)
    ax.annotate(f"vessel bore {BORE:.3f} m", xy=(0.98, BORE), xycoords=("axes fraction", "data"),
                ha="right", va="bottom", color="#B03A2E", fontsize=9)
    ax.fill_between(Ec, BORE, 0.6, color="#B03A2E", alpha=0.08)
    ax.scatter(E, [r["rg"] for r in rows], color="#00224E", zorder=5, s=28)
    ax.set_xlabel("beam energy [keV]"); ax.set_ylabel("gyroradius [m]")
    ax.set_ylim(0, 0.55)
    ax.set_title("C · The orbit has to fit the bore", loc="left", fontsize=11)
    ax.legend(fontsize=8.5, frameon=False, loc="upper left")

    # -- D: what that costs ----------------------------------------------
    ax = axes[1, 1]
    ax.bar(np.arange(len(E)), wall / n0, color="#B03A2E", label="vessel wall")
    ax.bar(np.arange(len(E)), zedge / n0, bottom=wall / n0, color="#D9A441",
           label="z domain edge (artefact)")
    ax.bar(np.arange(len(E)), bend / n0, bottom=(wall + zedge) / n0,
           color="#8894A8", label="entered the bend")
    ax.bar(np.arange(len(E)), final, bottom=(wall + zedge + bend) / n0,
           color="#00224E", label="still confined")
    ax.set_xticks(np.arange(len(E)))
    ax.set_xticklabels([f"{e:g}" for e in E])
    ax.set_xlabel("beam energy [keV]"); ax.set_ylabel("fraction")
    ax.set_ylim(0, 1)
    ax.set_title("D · Fate after 32 $\\mu$s", loc="left", fontsize=11)
    ax.legend(fontsize=8.5, frameon=False, loc="lower left")

    for a in axes.flat:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(out, dpi=150)
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", default="racetrack.png")
    ap.add_argument("--energies", type=float, nargs="*", default=None)
    a = ap.parse_args()
    rows = analyse(a.energies if a.energies is not None else E_KEV)
    if not rows:
        raise SystemExit("no completed runs found")
    print(f"{'E[keV]':>7} {'confined':>9} {'wall':>7} {'zedge':>7} {'bend':>7} {'rg[m]':>7}")
    for r in rows:
        print(f"{r['E']:7g} {r['final']:9.3f} {r['wall']:7d} {r['zedge']:7d} "
              f"{r['bend']:7d} {r['rg']:7.3f}")
    make_figure(rows, a.plot)


if __name__ == "__main__":
    main()

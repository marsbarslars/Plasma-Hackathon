# runs/racetrack-leg

The SLAM racetrack, using the real coil field (`SLAM_vC5_warpX.h5`) and the real
vacuum vessel (`SLAM_VV.stl`) from `SLAM_specs/`.

## What the data actually contains

The vessel is a complete racetrack: two straight legs running along **x** at
`y = ±0.500`, circular bore **radius 0.230 m**, joined by 180° bends at
`|x| = 0.75 … 1.355`. The loop lies in the x–y plane.

The field export covers `x ∈ [-0.75, +0.75]` — **exactly the straight sections**.
Field lines traced from a leg axis leave the grid at `x = ±0.75`, where the bends
begin. So this deck models **one straight mirror cell**, and treats `x = ±0.75` as
"entered the bend" rather than as a wall.

On the +y leg magnetic axis (`y = +0.5421`, 4 cm off the tube centre) `|B|` runs
0.1030 T at the leg midplane to 0.2546 T at its ends: **mirror ratio 2.471, loss
cone 39.50°**.

## Three things in the files that silently break a run

- **The STL is in millimetres.** Loaded as metres it is a 2.7 km machine.
  `eb2.stl_scale = 0.001`.
- **Its normals point the wrong way for WarpX.** The CAD normals face out of the
  vessel, so WarpX takes the tube interior to be solid and deletes every particle
  at initialisation — a run that exits 0 with an empty diagnostic rather than an
  error. `eb2.stl_reverse_normal = 1`.
- **The field and the vessel share an axis convention** (identity mapping), but the
  field grid extends to `y = ±2.55` while the vessel only reaches `y = ±0.73`. The
  padding makes the field look mis-oriented until you notice `|Bx|/|B| = 0.91` in
  the strong-field region, which is B running along the legs.

## Result: the orbit does not fit the bore

| Beam energy | Confined | Vessel wall | z-edge (artefact) | Entered bend | Gyroradius |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 3 keV | 0.398 | 3 965 | 3 093 | 4 985 | 0.109 m |
| 8 keV | 0.154 | 8 111 | 5 024 | 3 778 | 0.177 m |
| 15 keV | 0.071 | 10 040 | 5 733 | 2 803 | 0.243 m |
| 30 keV | 0.028 | 11 237 | 6 218 | 1 993 | 0.344 m |

At the leg midplane B is only 0.103 T, so a 30 keV deuteron gyrates with
**r = 0.344 m inside a 0.230 m bore**. It reaches the wall regardless of pitch —
this is a geometric limit, not the loss cone.

The two criteria do not overlap at 30 keV. Mirror confinement needs pitch > 39.5°;
fitting the bore with margin needs `r_g sin α < ~0.115 m`, i.e. α < 20° at this
energy. Something has to give: **more field, lower energy, or a wider bore.**
Scaling the field ×3 or dropping to ~8 keV both open a usable window.

## Two gaps in the exported data

1. **No field in the bends** (`|x| > 0.75`). The loop cannot be closed, so this is a
   single mirror cell rather than a racetrack. Whether the bends confine or spill
   the ions the mirror rejects is the actual question the geometry poses, and it
   cannot be answered from this export.
2. **The field is thinner than the vessel in z.** The grid covers `|z| ≤ 0.20` but
   the bore reaches 0.230, so the top and bottom of the tube fall outside the
   domain. Those particles leave through the z boundary instead of hitting the
   wall — 31% of all losses at 30 keV. Wall loads here are **underestimates** and
   confined fractions are lower bounds.

An export covering `|x| ≤ 1.40` and `|z| ≤ 0.25` would close both.

## Reproducing

```bash
for E in 3 8 15 30; do ../../scripts/warpx run inputs_3d_racetrack.txt Ekev=$E diag1.file_prefix=diags/E$E scraped.file_prefix=diags/E${E}_scraped reduced_diags.path=./diags/E${E}_reduced/; done
```

```bash
../../.venv/bin/python ../../scripts/racetrack_scan.py --plot racetrack.png
```

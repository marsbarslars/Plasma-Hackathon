# runs/racetrack

The SLAM racetrack as a **closed loop**, using the real coil field and the real
vacuum vessel from `SLAM_specs/`.

## The field had to be regenerated first

The original `SLAM_vC5_warpX.h5` had its grid ranges on the wrong axes. The coil
set spans `x −1.400…+1.400`, `y −0.714…+0.908`, `z −0.412…+0.396`, and the vessel
spans `x ±1.355`, `y ±0.730`, `z ±0.230` — the machine's long axis is **x**. But
the export used `x ±0.75` (less than half the machine) and `y ±2.55` (three times
wider than the coils occupy, in a region where `|B|` had fallen to 2 × 10⁻⁴ T).

`make_field_file_with_DESC.py` now uses:

```python
xmin, xmax, nx = -1.45, 1.45, 146
ymin, ymax, ny = -0.95, 0.95,  96
zmin, zmax, nz = -0.28, 0.28,  29
```

Same ~2 cm resolution, 406 k points against the old 382 k — it covers the whole
machine for essentially the same cost. The field file is derived, so it is
gitignored; regenerate it with

```bash
cd SLAM_specs && uv run --no-project --python 3.12 --with desc-opt --with openpmd-api --with numpy python make_field_file_with_DESC.py
```

**The test that it worked:** a field line seeded on the magnetic axis now closes
after **6.388 m**, running right around the loop through both bends. With the old
export it ran out of grid after 0.75 m.

## The device

One lap contains **two mirror cells** — the two straight legs — joined by
low-field bends. Around the closed axis `|B|` runs 0.1030 T at a leg midplane to
0.2583 T at the throats: ratio **2.508**, loss cone **39.15°**.

Because the loop is closed there is no axial loss channel. Particles the mirror
rejects do not leave the machine; they carry on into a bend. **The vessel wall is
the only way out**, and the runs confirm it: zero particles reach a domain
boundary at any energy, and the particle balance closes exactly.

## Result

| Beam energy | Confined | Vessel wall | Domain edge | Gyroradius at 0.103 T |
| ---: | ---: | ---: | ---: | ---: |
| 3 keV | 0.458 | 10 844 | 0 | 0.108 m |
| 8 keV | 0.183 | 16 335 | 0 | 0.177 m |
| 15 keV | 0.086 | 18 272 | 0 | 0.242 m |
| 30 keV | 0.034 | 19 320 | 0 | 0.343 m |

Closing the loop helps, but only modestly — 30 keV confinement goes from 0.028
(straight leg alone, with artefacts) to 0.034. **The binding constraint is
geometric, not magnetic.** At the leg midplane B is 0.103 T, so a 30 keV deuteron
gyrates with r = 0.343 m inside a 0.230 m bore and reaches the wall whatever its
pitch angle. Mirror confinement needs pitch > 39°, fitting the bore needs well
under that at this energy, and the two do not overlap.

Roughly ×3 on the field, or dropping the beam to ~8 keV, opens a usable window.

## Caveats

- DESC coils are infinitely thin filaments, so `|B|` diverges near a winding. A
  few reach several tesla inside the bore, but they are **0.09%** of bore cells
  (99th percentile 0.399 T, median 0.111 T) and sit against the wall. `dt = 6 ns`
  gives ~55 steps per orbit at 0.4 T.
- Test particles: no collisions, no self-fields, no beam attenuation.
- 30 µs of physical time, which is prompt-loss territory — see §1 of
  `docs/nbi-plan.md` for why that is the honest limit of full-orbit WarpX here.

## Reproducing

```bash
for E in 3 8 15 30; do ../../scripts/warpx run inputs_3d_racetrack.txt Ekev=$E diag1.file_prefix=diags/E$E scraped.file_prefix=diags/E${E}_scraped reduced_diags.path=./diags/E${E}_reduced/; done
```

```bash
../../.venv/bin/python ../../scripts/racetrack_scan.py --plot racetrack.png
```

# runs/nbi-angle-scan

Phase 2 of `docs/nbi-plan.md`: a directed 30 keV deuterium beam injected into the
mirror at a range of aiming angles.

Only the **fast-ion leg** is simulated. A neutral beam travels in a straight line
and is invisible to a PIC code, so the beam is injected as ions already at their
birth points — see §1 and §5 of the plan. The Gaussian along the beam axis stands
in for a deposition profile; Beer–Lambert attenuation is Phase 4.

On axis **B** lies along +z, so the injection angle *is* the pitch angle, and the
loss-cone criterion `sin²α > B_birth/B_max` predicts a transition at **34.7°** —
the same number Phase 0 validated.

## Caveat: no vessel yet

Phase 1 has not been built, so the domain edge is the wall. Radial losses in this
scan are an artefact of the 1 m box rather than a real vacuum vessel, and they
matter most at large injection angles where the gyroradius is largest. Panel B
separates the two channels so the mirror physics stays readable.

## Aiming the beam

`gaussian_beam` is built along +z and then rotated bodily:

```
beam.do_gaussian_beam_rotation = 1
beam.gaussian_beam_rotation_axis = 0. 1. 0.
beam.gaussian_beam_rotation_angle = alpha
beam.do_gaussian_beam_rotation_momenta = 1
```

`do_gaussian_beam_rotation_momenta` is the one that matters — without it only the
footprint turns and the beam still flies along +z. WarpX applies `x/y/z_rms`
*before* the rotation, so those sizes are specified pre-rotation and axis-aligned.

Verified at 45°: mean angle from +z is 45.01°, `ux/uz` = 0.9999, `uy` ≈ 0.

## Result

| Injection angle | Confined | Guiding-centre prediction | Axial loss | Radial loss |
| ---: | ---: | ---: | ---: | ---: |
| 0-25° | 0.000 | 0.000 | 20 000 | 0 |
| 30° | 0.031 | 0.003 | 19 389 | 0 |
| 32.5° | 0.334 | 0.100 | 13 320 | 0 |
| 35° | 0.924 | 0.771 | 1 521 | 3 |
| 37.5° | 0.999 | 0.999 | 5 | 7 |
| 45° | 0.998 | 1.000 | 0 | 32 |
| 90° | 0.972 | 1.000 | 0 | 562 |

The transition is **sharp** — nothing survives below 25°, essentially everything
above 37.5° — and loss is **prompt**: at 0-30° the population collapses inside
2 µs, roughly one transit, then flattens. Aiming an NBI is close to a binary
choice, not a gradual trade-off.

### The 50% crossing is at 33.2°, not 34.7°

Two loss-cone angles bracket the answer, depending on which `B_max` a particle
actually reaches:

| `B_max` used | Loss cone |
| --- | --- |
| on-axis, 0.4610 T | 34.70° |
| global maximum in the domain, 0.8948 T | 24.12° |

The observed 33.2° sits between them, and the guiding-centre prediction using
on-axis `B_max` is systematically **pessimistic** near the boundary — 0.10 against
0.33 at 32.5°, 0.77 against 0.92 at 35°.

That is finite gyroradius. At 0.149 T a 30 keV deuteron has a 24 cm gyroradius
against a field scale length of order 1 m, so `rg/L ≈ 0.24`: μ is only
approximately conserved, and an orbit that wanders off axis near a throat samples
more field than the on-axis value, mirroring earlier than the guiding-centre
criterion allows for. Expect the two to converge at higher field or lower beam
energy, and to diverge further in a compact device.

### Radial losses grow with angle

They are zero below 35° and reach 562 at 90°. Perpendicular injection is perfectly
confined *against the mirror* but has the largest gyroradius, so it walks into the
radial boundary. With no vessel yet that boundary is the 1 m box, so treat the
number as a placeholder — but the trend is real, and it is exactly the effect the
Phase 1 vessel is for.

## Reproducing

```bash
../../.venv/bin/python ../../scripts/nbi_scan.py --run
```

```bash
../../.venv/bin/python ../../scripts/nbi_scan.py --plot nbi_scan.png
```

The sweep needs no templating — WarpX takes ParmParse overrides directly, so one
deck serves every angle. Each angle writes to `diags/<tag>`, `diags/<tag>_scraped`
and `diags/<tag>_reduced` so runs cannot overwrite one another; forgetting the
last of those is what silently clobbers the previous run's `confined.txt`.

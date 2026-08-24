# runs/mirror-validation

Phase 0 of `docs/nbi-plan.md`: check that the mirror physics is right before any
beam geometry or vessel boundary is layered on top.

20 000 isotropic 30 keV deuterons at the midplane of the FEMM mirror field,
scaled ×100 to 0.149 T at the midplane and 0.461 T at the throats. Test
particles, so only the applied B matters — the electrostatic solver correctly
reports `Max norm of rho is 0`.

This supersedes `runs/magnetic-mirror`, which used 8 eV protons in a 5 mT field:
at that scale a fast ion has a 7 m gyroradius in a 5 m box and is not magnetised
at all.

## Result

On-axis mirror ratio **3.086**, so the loss cone is at **34.7°**.

| Quantity | Value |
| --- | --- |
| Per-particle fate predicted by `sin²θ < B_birth/B_max` | **97.1% correct** |
| Confined fraction, simulated | 0.795 |
| Confined fraction, isotropic on-axis prediction `cos(θ_lc)` | 0.822 |
| Axial losses (`zlo`/`zhi`) | 3873, median birth pitch 24.9° |
| Radial losses (`x`/`y`) | 233, median birth pitch 76.0° |

The 2.7-point deficit against the analytic prediction is physical, not numerical.
The radial losses are near-**perpendicular** particles — deeply confined against
the mirror, but with a 24 cm gyroradius in a 1 m bore they reach the radial
boundary anyway. That is a finite-orbit-width loss, and it is exactly the effect
that motivates a real vessel boundary in Phase 1.

## Reproducing

```bash
../../scripts/warpx run inputs_3d_mirror_validation.txt
```

```bash
../../.venv/bin/python ../../scripts/plot_mirror.py --out mirror.png
```

`mirror.png` is the six-panel physics figure: field profile, velocity space
before and after, pitch-angle distribution, confinement history, and loss versus
birth pitch against theory.

For the 3D view, the main run's 200-step diagnostic interval is far too coarse to
resolve a ~71-step gyro-orbit, so orbits alias into zigzags. Use a short, finely
sampled run instead:

```bash
../../scripts/warpx run inputs_3d_mirror_validation.txt max_step=2400 ions.npart=400 diag1.intervals=4 diag1.file_prefix=diags/orbits diagnostics.diags_names=diag1 reduced_diags.path=./diags/orbits_reduced/
```

```bash
../../.venv/bin/python ../../scripts/animate_mirror.py --path diags/orbits --mp4 system.mp4 --n-tracks 30 --stride 2 --trail 120 --zoom 1.9 --opacity 0.32
```

Note `reduced_diags.path` — without it the second run overwrites the first run's
`diags/reducedfiles/confined.txt`, which panel E reads.

## Gotchas found here

- **`addRealAttributes` must declare a custom attribute** before
  `attribute.<name>(...)` will define it; otherwise the diagnostic aborts with
  "not an existing attribute".
- **The attribute parser's `ux,uy,uz` are γv in m/s**, not the γβ the
  documentation states. `pitch0` is a ratio so it is unaffected; `speed0` comes
  back in m/s.
- **Mesh arrays are written in `(z,y,x)` order.** Indexing them as `(x,y,z)`
  silently profiles the wrong axis — it made the mirror ratio look like 1.28
  instead of 3.09. `scripts/plasma/field.py` normalises on load.
- **Reduced diagnostics land in `diags/reducedfiles/`**, not `reduced_diags/`.

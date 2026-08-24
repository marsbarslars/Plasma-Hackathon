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
../../scripts/warpx run inputs_3d_mirror_validation.txt max_step=2400 diag1.intervals=8 diag1.file_prefix=diags/orbits diagnostics.diags_names=diag1 reduced_diags.path=./diags/orbits_reduced/
```

```bash
../../.venv/bin/python ../../scripts/animate_mirror.py --path diags/orbits --mp4 system.mp4 --n-tracks 30 --stride 2 --trail 120
```

`system.mp4` pairs the 3D view with a static `|B|` scale bar and the live (v∥, v⊥)
distribution emptying its loss cone. Keep the full 20 000 particles for that panel
even though only 30 tracks are drawn — at 400 the histogram is too sparse to read.
It reads every particle each frame, so it is the slow part of the render;
`--no-charts` skips it. Note the animation covers 2400 steps (9.6 us), not the
main run's 40 us.

The density panel is a *smoothed* estimate with its colour ceiling calibrated
across six frames spread through the run. Both matter: raw counts at this sample
size are ~4 per bin, so Poisson noise is the same size as the signal, and a
ceiling locked on frame 0 clips badly once the distribution concentrates. Drawn
naively the panel shows contour-like bands that are pure shot noise.

That run writes ~1.5 GB, nearly all of it the grid `B` field repeated per frame
rather than the particles.

Note `reduced_diags.path` — without it the second run overwrites the first run's
`diags/reducedfiles/confined.txt`, which panel E reads.

## Bounce-phase structure

The velocity distribution is not smooth at early times. Along `v_par ~ 0` the
counts show a real peak-trough-peak, ~6 sigma in the raw histogram and not an
artifact of binning or smoothing. It decays as the run proceeds — peak/trough
2.54 at 9.6 us against 1.82 at 40 us.

That is bounce-phase coherence. Every particle starts at t = 0 from the midplane
and there are no collisions, so the population keeps its phase memory and only
mixes as particles with different bounce periods drift apart. Expect it to matter
whenever a run is read before a few bounce times have passed, and expect a beam —
which is far more monoenergetic than this Maxwellian — to show it much more
strongly.

A useful consistency check fell out of this: the orbit render run and the main run
give *bit-identical* velocity histograms at the same step, so the short run is a
faithful sub-sample of the long one rather than a separate realisation.

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

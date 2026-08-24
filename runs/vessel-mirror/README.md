# runs/vessel-mirror

Phase 1 of `docs/nbi-plan.md`: put a real wall in. Until now the domain edge stood
in for a vessel, so every radial loss was an artefact of the box.

Isotropic 30 keV deuterons in the ×100 FEMM mirror — the Phase 0 population — now
inside an embedded-boundary vacuum vessel, scanned over vessel radius.

## The vessel

One expression covers both shapes the project needs. `ra = rb` gives a cylinder and
the twist term drops out; `ra ≠ rb` with `kz ≠ 0` gives the rotating ellipse a
stellarator section needs.

```
warpx.eb_implicit_function = "((x*cos(kz*z) + y*sin(kz*z))/ra)^2 + ((-x*sin(kz*z) + y*cos(kz*z))/rb)^2 - 1"
warpx.eb_potential(x,y,z,t) = 0.
boundary.particle_eb = Absorbing
```

**WarpX puts the plasma where the function is negative**, so this is the volume
inside the surface. `rb` defaults to `ra` in the deck, so overriding `ra` alone
keeps the vessel circular across a sweep.

Embedded boundaries work with `warpx.grid_type = collocated` and the labframe
electrostatic solver — that combination was untested here before.

## Result

| Vessel radius | Launched | Confined | Axial loss | Wall loss | Domain edge |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.25 m | 19 094 | 0.151 | 2 429 | 13 784 | 0 |
| 0.35 m | 19 953 | 0.313 | 3 287 | 10 426 | 0 |
| 0.45 m | 19 999 | 0.481 | 3 538 | 6 835 | 0 |
| 0.55 m | 20 000 | 0.613 | 3 615 | 4 125 | 0 |
| 0.70 m | 20 000 | 0.734 | 3 653 | 1 671 | 0 |
| 0.90 m | 20 000 | 0.795 | 3 677 | 429 | 0 |

**Nothing reaches the domain edge at any radius** — the vessel is genuinely doing
the absorbing. The particle balance closes exactly at every point.

Confinement rises monotonically toward the mirror-only limit `cos(θ_lc)` = 0.822,
and at 0.9 m it reaches 0.795 — the same number Phase 0 measured with the bare
1 m box, which is the consistency check that says the two setups agree where they
should.

**Axial losses are nearly independent of radius** (3 287 → 3 677 from 0.35 m
upward). The loss cone does not care how wide the vessel is. Everything the wall
costs is *additional*, so vessel radius and mirror ratio are close to independent
design knobs over this range.

## Wall load peaks at the midplane, not the throats

Panel D is the engineering-relevant result: the load is sharply peaked at z = 2.5,
where `|B|` is *lowest*. Gyroradius goes as 1/B, so orbits are widest exactly where
the field is weakest, and that is where they reach the wall. The profile is almost
unchanged in shape across every vessel radius.

That is the opposite of the intuition that the throats — where field lines converge
and particles turn around — take the beating. Azimuthally the load is uniform, as an
axisymmetric field with an axisymmetric vessel requires; panel C is mostly a check
that nothing is broken.

## A vessel narrower than the beam clips it

At `ra = 0.25` m, 906 of 20 000 particles are born **outside** the vessel and are
deleted at initialisation, never reaching the scraping buffer. The source has
σ = 0.10 m in x and y, so `exp(-r²/2σ²)` predicts 879 — it matches.

They are silently gone: they appear in no loss channel, and the only trace is that
`ParticleNumber` starts below `npart`. Normalise confined fractions by the step-0
count rather than by the requested `npart`, or a narrow vessel will look better
than it is.

## Reproducing

```bash
../../.venv/bin/python ../../scripts/vessel_scan.py --run
```

```bash
../../.venv/bin/python ../../scripts/vessel_scan.py --plot vessel.png
```

Read the scraping output only after the run has fully exited — reading it while
WarpX is still flushing gives short counts that look like a physics discrepancy.

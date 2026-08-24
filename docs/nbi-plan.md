# Neutral beam injection: implementation plan

Fast-ion deposition and loss in a mirror–stellarator hybrid, benchmarked against W7-X.

## 1. Scope: what full-orbit WarpX can and cannot deliver

Settle this before building anything, because it determines whether the whole
approach is sound.

WarpX pushes **full orbits** — every gyration is resolved in time. At W7-X field
strength (2.5 T) a 60 keV deuteron has a 52.5 ns gyroperiod, so even a permissive
20 steps per orbit puts `dt` around 2.6e-9 s:

| Physical time | What it buys | Steps |
| --- | --- | --- |
| 14 µs — one toroidal transit | first-orbit losses | 1.4e4 |
| ~100 µs | prompt loss fraction, wall load map | 1e5 |
| 1 ms | marginal orbits | 9.5e5 |
| ~50 ms — slowing-down time | thermalisation, steady-state fast-ion tail | 5e7 |

**The feasible window is roughly 100 µs.** That covers prompt and first-orbit
losses, which is precisely the regime where full-orbit matters — finite gyroradius
near the wall is exactly what guiding-centre codes approximate away. It does *not*
cover slowing-down-timescale confinement.

This is a scoping boundary, not a defect. Fast-ion confinement over a slowing-down
time is the job of a guiding-centre code (ASCOT, BEAMS3D, SIMPLE); those exist
because full-orbit is the wrong tool there. Frame the WarpX work as **deposition
and prompt loss**, and treat long-time confinement as a separate question.

If long-time confinement is the actual goal, stop and reconsider the tool before
investing in the geometry pipeline.

## 2. Resolution: driven by field structure, not gyroradius

A useful consequence of test-particle mode. With an applied field and
`do_not_deposit = 1`, the grid is used only to *interpolate B* and to *define the
embedded boundary*. The gyro-orbit is resolved in time by the pusher, not in space
by the mesh. So cell size is set by how fast **B** varies and by the vessel's
geometric features — not by the 1.4 cm gyroradius.

That matters because WarpX interpolates a `read_from_file` field onto the
simulation grid, so grid resolution caps field fidelity regardless of how fine the
source map is.

Full W7-X torus in a Cartesian box (12.4 × 12.4 × 2.4 m):

| dx | Cells | B map |
| --- | --- | --- |
| 5 cm | 2.9e6 | 0.07 GB |
| 2 cm | 46e6 | 1.11 GB |
| 1 cm | 369e6 | 8.9 GB |

**2 cm is the working point** — it resolves the ~0.5 m minor radius and the field
period comfortably. 1 cm is only worth it if vessel features demand it, and it is
where MPI stops being optional.

The racetrack hybrid is cheaper than W7-X only in proportion to its footprint —
being a closed loop, it still needs the whole device in the box, not one cell.

## 3. Geometry: two different problems

### Hybrid — a racetrack, not a linear machine

The hybrid is a **racetrack**: two magnetic mirrors joined by short stellarator
sections that close the device into a loop. That closed topology changes the
problem in three ways:

- There are no open ends, so loss-cone particles are not simply lost — they pass
  into the stellarator links, and what happens there is the actual question.
- The stellarator sections supply rotational transform between the mirror cells,
  so confinement is not the single-cell mirror criterion of §Phase 0.
- The vessel cannot be written as one implicit function along a single axis.

A rotating-ellipse expression still describes a *straight* mirror cell, and is
worth building first as a component — `warpx.eb_implicit_function` takes a parser
expression, and **WarpX puts the plasma where the function is negative**:

```
warpx.eb_implicit_function = "((x*cos(k*z) + y*sin(k*z))/a)^2
                            + ((-x*sin(k*z) + y*cos(k*z))/b)^2 - 1"
```

But the full racetrack needs either a piecewise construction (straight mirror
cells joined by curved stellarator links, combined with min/max operations in the
parser) or an STL mesh. Assume STL until a piecewise analytic form is shown to
work — which makes the hybrid and W7-X share the same geometry pipeline rather
than being cheap and expensive cases.

### W7-X — STL

W7-X's vessel is a 5-field-period, non-axisymmetric surface with a bean cross
section that deforms as it goes round. It is a Fourier series in (θ, φ), not a
closed-form implicit function. That means `eb2.geom_type = stl` and
`eb2.stl_file`.

Requirements to verify before relying on it, since none are checked here yet:

- The mesh must be **closed, watertight, and consistently oriented**. A leaky or
  normal-flipped mesh produces a silently wrong EB rather than an error.
- Confirm AMReX's STL options (scale, centre, normal reversal) against the
  vendored AMReX in `vendor/warpx` at the version actually pinned.
- Check EB interacts correctly with `warpx.grid_type = collocated`, which the
  current mirror deck uses.

Generate the STL from the boundary surface in Python and validate it — watertight
check, normal orientation, and a WarpX run on a coarse grid confirming particles
are absorbed where expected — *before* any physics run.

## 4. Fields

### Superposition is free, and worth exploiting

`read_from_file` has a multi-field mode that loads several maps independently, each
with its own scaling:

```
particles.B_ext_particle_init_style = read_from_file
particles.B_ext_particle_fields = mirror helical
particles.mirror.read_fields_from_path  = fields/mirror
particles.mirror.read_fields_B_dependency(t)  = mirror_scale
particles.helical.read_fields_from_path = fields/helical
particles.helical.read_fields_B_dependency(t) = helical_scale
```

For a hybrid this is exactly the right structure: generate the mirror-coil map and
the helical-winding map **once**, then scan the hybrid balance by varying two
constants. No field regeneration per run. The dependency is a function of `t`, and
a constant expression is a valid one.

### W7-X field must be a vacuum field from coils

Take the field from **Biot–Savart on the coil set**, not from a VMEC interior
equilibrium. Lost orbits leave the last closed flux surface by definition, and a
VMEC solution has nothing outside it — the region where the losses actually happen.

Field-map generation is a Python pre-processing step writing openPMD, the same
shape as the existing `example-femm-3d.h5`.

## 5. The diagnostic constraint that shapes everything

**The reduced-diagnostic parser cannot see B.** `ParticleHistogram2D`'s
`histogram_function_abs/ord` take `(t, x, y, z, ux, uy, uz, w)` and nothing else.
Pitch angle needs the local field, so it cannot be computed in-line from a field
map.

Two consequences:

- **Analytic field** (hybrid model case): paste the same B expression into the
  histogram function and get live pitch-angle histograms for free.
- **File-based field** (W7-X, FEMM): impossible in-line. Dump `x y z ux uy uz w`
  and compute pitch angle offline against the field map.

So **the offline analysis path is the primary one** — it is the only one that works
for both. In-line histograms are a cheap live monitor for the analytic case, not
the measurement of record.

## 6. Velocity-space diagnostics

Offline, from full particle dumps plus the field map:

- **(v∥, v⊥) distribution** — the canonical fast-ion plot. Loss-cone structure
  appears directly as a depleted wedge.
- **Pitch vs energy**, for the confined population and separately for the scraped
  population.
- **Birth vs. loss distributions**, which together give the loss cone empirically
  rather than by assuming the analytic criterion.

From `BoundaryScraping`, per lost particle:

- `timeScraped` → loss-time distribution, separating prompt from delayed losses.
- `nx, ny, nz` (EB normals) → **wall load map**, the engineering-relevant output.

Reduced diagnostics for cheap time series: `ParticleNumber` (confined fraction),
`ParticleEnergy`, and `ParticleHistogram` for a live monitor.

**Caveat:** with test particles and no collisions the distribution does not relax.
What is visible is orbit topology and prompt loss, nothing more. Pitch-angle
scattering and slowing down need `collisions.type = pairwisecoulomb`, which is a
later phase and runs into the timestep wall from §1.

## 7. Phases

Each phase ends in something checkable. Do not start a phase before its predecessor
gives the expected answer.

**Phase 0 — validation. DONE.** See `runs/mirror-validation/`. FEMM mirror scaled
×100 (0.149 T midplane, 0.461 T throats), `dt = 4 ns`, 20 000 isotropic 30 keV
deuterons. On-axis mirror ratio is **3.086**, so the loss cone is at **34.7°** —
not the 39.2° first estimated from a coarsely sampled field. The per-particle
criterion `sin²θ < B_birth/B_max` predicts the simulated fate of **97.1%** of
particles; confined fraction 0.795 against 0.822 predicted for isotropic on-axis
birth. The residual is real physics: 233 particles leave radially with a median
birth pitch of 76°, i.e. well confined against the mirror but lost to a 24 cm
gyroradius in a 1 m bore.

**Phase 1 — vessel boundary.** Start with a single straight mirror cell using the
rotating-ellipse EB, `boundary.particle_eb = Absorbing`, scraping diagnostic.
**Exit test:** loss fraction changes sensibly with vessel radius; particles are
absorbed at the wall rather than at domain edges. Then extend to the racetrack,
which is where the geometry question actually gets decided.

**Phase 2 — beam injection and angle scan.** `gaussian_beam` with
`do_gaussian_beam_rotation` and `do_gaussian_beam_rotation_momenta`. Angle as a
`my_constants` entry overridden on the command line — WarpX takes ParmParse
overrides directly (`warpx run inputs alpha=0.3`), so a sweep needs no templating.
**Exit test:** confined fraction vs. angle is smooth and reproduces Phase 0's
loss-cone angle where the fields are comparable.

**Phase 3 — velocity-space analysis.** Offline pipeline: load openPMD, interpolate
B at particle positions, compute pitch/energy, plot (v∥, v⊥) and wall loads.
**Exit test:** birth distribution matches the injector geometry; loss distribution
shows a loss cone consistent with the field.

**Phase 4 — realistic deposition.** Replace the rotated Gaussian with Beer–Lambert
sampling along the chord, written to openPMD and loaded via
`injection_style = external_file`. **Exit test:** deposition profile matches the
analytic exponential.

**Phase 5 — W7-X.** Coil field, STL vessel, MPI build. Highest risk and highest
cost; everything before it is reusable regardless of how it goes.

## 8. Repo and build changes

- **A shared analysis package.** `animate_mirror.py` is standalone; Phases 3–5 need
  common code for openPMD loading, field interpolation, pitch-angle computation and
  distribution plots. Factor this out rather than copying between run directories.
- **Field-map generation scripts** producing openPMD, one per field source.
- **Run directories per case**, as now. Command-line ParmParse overrides mean one
  deck can serve a whole sweep.
- **MPI.** Phase 5 at 2 cm needs it. `warpx --mpi ON build` already exists, but it
  needs an MPI implementation installed, and pywarpx separately if PICMI is used.
- Keep `warpx.do_electrostatic = labframe` with `const_dt`: no CFL constraint, so
  `dt` is set purely by gyro-orbit resolution.

## 9. Open questions

1. **Is prompt loss the actual question?** If slowing-down confinement is the goal,
   §1 says full-orbit WarpX is the wrong tool and the plan should change.
2. **Hybrid machine parameters** — length, field strength, mirror ratio, helical
   period, vessel dimensions. Every number in §1–2 is illustrative until these are
   fixed.
3. **W7-X comparison target** — benchmarking against published loss fractions is a
   very different exercise from qualitative comparison, and it sets how faithful the
   vessel and field have to be.
4. **Beam parameters** — species, energy, whether full/half/third energy components
   matter, injector geometry and aiming.

#!/usr/bin/env python3
"""
Write a coil magnetic field to an openPMD HDF5 file that WarpX can load via
picmi.LoadInitialField(read_fields_from_path=...) (i.e. B_ext_grid_init_style
= read_from_file).

Requirements: pip install openpmd-api numpy
"""
import numpy as np
import openpmd_api as io
from desc.coils import CoilSet, MixedCoilSet, FourierPlanarCoil

coils = CoilSet.load("SLAM0_coilset_fb_1p52_psi2p2e-3_C5.h5")

name = "SLAM_vC5_warpX.h5"
# ----------------------------------------------------------------------
# 1. Define the grid the field will be tabulated on.
#    This must COVER the whole WarpX simulation domain (>= prob_lo/prob_hi).
#    Resolution does NOT have to match WarpX; it interpolates to its own grid.
#    Use a NODAL (collocated) grid: values live at the grid points x[i],y[j],z[k].
# ----------------------------------------------------------------------
# The device's long axis is x. The coil set spans x -1.400..+1.400,
# y -0.714..+0.908, z -0.412..+0.396, and SLAM_VV.stl spans x +-1.355,
# y +-0.730, z +-0.230 (that file is in millimetres).
#
# The previous ranges had the long extent on y: x was cut at +-0.75,
# less than half the machine, while 255 nodes covered a y range three
# times wider than the coils occupy and where |B| had fallen to 2e-4 T.
# Grid resolution is ~2 cm in every direction, as before.
xmin, xmax, nx = -1.45, 1.45, 146    # metres, number of NODES
ymin, ymax, ny = -0.95, 0.95,  96
zmin, zmax, nz = -0.28, 0.28,  29

x = np.linspace(xmin, xmax, nx)
y = np.linspace(ymin, ymax, ny)
z = np.linspace(zmin, zmax, nz)

dx = (xmax - xmin) / (nx - 1)
dy = (ymax - ymin) / (ny - 1)
dz = (zmax - zmin) / (nz - 1)

# ----------------------------------------------------------------------
# 2. Evaluate YOUR B(x,y,z) on that grid, in Tesla.
#    Arrays are indexed [ix, iy, iz]  (axisLabels = x, y, z below).
#    Replace this block with a call to your own coil field routine.
# ----------------------------------------------------------------------
X, Y, Z = np.meshgrid(x, y, z, indexing="ij")   # each (nx, ny, nz)
grid_shape = X.shape

# flat list of [x, y, z] triples, shape (nx*ny*nz, 3)
points = np.column_stack([X.ravel(order="C"),
                          Y.ravel(order="C"),
                          Z.ravel(order="C")])

# --- call your coil field code on the list of points ---
# It should return B as (N, 3) with columns [Bx, By, Bz] in Tesla.
# Evaluate in chunks: 400k points x 61 coils at once is a large temporary.
_chunks = []
_step = 20000
for _i in range(0, points.shape[0], _step):
    _chunks.append(np.asarray(
        coils.compute_magnetic_field(points[_i:_i + _step], basis='xyz'),
        dtype=np.float64))
    print(f"  {min(_i + _step, points.shape[0])}/{points.shape[0]} points", flush=True)
B = np.concatenate(_chunks, axis=0)
assert B.shape == (points.shape[0], 3), f"expected (N,3), got {B.shape}"

# reshape each component back onto the (nx, ny, nz) grid
Bx = np.ascontiguousarray(B[:, 0].reshape(grid_shape, order="C"))
By = np.ascontiguousarray(B[:, 1].reshape(grid_shape, order="C"))
Bz = np.ascontiguousarray(B[:, 2].reshape(grid_shape, order="C"))


# ----------------------------------------------------------------------
# 3. Write the openPMD series.  One iteration (0) with a vector mesh "B".
# ----------------------------------------------------------------------
series = io.Series(name, io.Access.create)
series.set_openPMD("1.1.0")
series.set_software("coil-field-export")

it = series.iterations[0]

B = it.meshes["B"]
B.geometry = io.Geometry.cartesian
B.axis_labels = ["x", "y", "z"]                 # order matches array axes
B.grid_spacing = [dx, dy, dz]                   # in grid_unit_SI units
B.grid_global_offset = [xmin, ymin, zmin]       # position of node [0,0,0]
B.grid_unit_SI = 1.0                            # spacing/offset already in metres
B.unit_dimension = {io.Unit_Dimension.M:  1,
                    io.Unit_Dimension.I: -1,
                    io.Unit_Dimension.T: -2}    # Tesla = kg / (A s^2)

dset = io.Dataset(Bx.dtype, Bx.shape)
for comp, data in (("x", Bx), ("y", By), ("z", Bz)):
    rc = B[comp]
    rc.reset_dataset(dset)
    rc.unit_SI = 1.0                            # data already in Tesla
    # nodal grid: sample point sits ON the node -> position 0.0
    rc.position = [0.0, 0.0, 0.0]
    rc.store_chunk(data)

series.flush()
del series
print(f"wrote bfield to {name}")
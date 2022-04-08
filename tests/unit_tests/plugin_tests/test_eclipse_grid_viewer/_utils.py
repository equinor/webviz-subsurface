import numpy as np
import pyvista as pv


def create_explicit_structured_grid(
    ni: int, nj: int, nk: int, si: float, sj: float, sk: float
) -> pv.ExplicitStructuredGrid:

    si = float(si)
    sj = float(sj)
    sk = float(sk)

    # create raw coordinate grid
    grid_ijk = np.mgrid[
        : (ni + 1) * si : si, : (nj + 1) * sj : sj, : (nk + 1) * sk : sk
    ]

    # repeat array along each Cartesian axis for connectivity
    for axis in range(1, 4):
        grid_ijk = grid_ijk.repeat(2, axis=axis)

    # slice off unnecessarily doubled edge coordinates
    grid_ijk = grid_ijk[:, 1:-1, 1:-1, 1:-1]

    # reorder and reshape to VTK order
    corners = grid_ijk.transpose().reshape(-1, 3)

    dims = np.array([ni, nj, nk]) + 1

    grid = pv.ExplicitStructuredGrid(dims, corners)
    grid = grid.compute_connectivity()
    grid.ComputeFacesConnectivityFlagsArray()

    return grid

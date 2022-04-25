import xtgeo
import pyvista as pv

# The hack implementation requires both updated xtgeo and VTK version 9.2
# from ._xtgeo_to_explicit_structured_grid_hack import (
#     xtgeo_grid_to_explicit_structured_grid_hack,
# )

# Requires updated xtgeo
from ._xtgeo_to_vtk_explicit_structured_grid import (
    xtgeo_grid_to_vtk_explicit_structured_grid,
)


def xtgeo_grid_to_explicit_structured_grid(
    xtg_grid: xtgeo.Grid,
) -> pv.ExplicitStructuredGrid:

    # return xtgeo_grid_to_explicit_structured_grid_hack(xtg_grid)
    return xtgeo_grid_to_vtk_explicit_structured_grid(xtg_grid)

    dims, corners, inactive = xtg_grid.get_vtk_geometries()
    corners[:, 2] *= -1
    esg_grid = pv.ExplicitStructuredGrid(dims, corners)
    esg_grid = esg_grid.compute_connectivity()
    # esg_grid.ComputeFacesConnectivityFlagsArray()
    esg_grid = esg_grid.hide_cells(inactive)
    # esg_grid.flip_z(inplace=True)
    return esg_grid

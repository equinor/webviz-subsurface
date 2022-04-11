import xtgeo
import pyvista as pv


def xtgeo_grid_to_explicit_structured_grid(
    xtg_grid: xtgeo.Grid,
) -> pv.ExplicitStructuredGrid:
    dims, corners, inactive = xtg_grid.get_vtk_geometries()
    corners[:, 2] *= -1
    esg_grid = pv.ExplicitStructuredGrid(dims, corners)
    esg_grid = esg_grid.compute_connectivity()
    # esg_grid.ComputeFacesConnectivityFlagsArray()
    esg_grid = esg_grid.hide_cells(inactive)
    # esg_grid.flip_z(inplace=True)
    return esg_grid

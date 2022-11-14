import logging

import numpy as np
import xtgeo
from vtkmodules.util.numpy_support import (
    numpy_to_vtk,
    numpy_to_vtkIdTypeArray,
    vtk_to_numpy,
)

# pylint: disable=no-name-in-module,
from vtkmodules.vtkCommonCore import vtkPoints

# pylint: disable=no-name-in-module,
from vtkmodules.vtkCommonDataModel import (
    vtkCellArray,
    vtkDataSetAttributes,
    vtkExplicitStructuredGrid,
)

from webviz_subsurface._utils.perf_timer import PerfTimer

LOGGER = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
def xtgeo_grid_to_vtk_explicit_structured_grid(
    xtg_grid: xtgeo.Grid,
) -> vtkExplicitStructuredGrid:

    timer = PerfTimer()

    # Create geometry data suitable for use with VTK's explicit structured grid
    # based on the specified xtgeo 3d grid
    pt_dims, vertex_arr, conn_arr, inactive_arr = xtg_grid.get_vtk_esg_geometry_data()
    vertex_arr[:, 2] *= -1
    et_get_esg_geo_data_ms = timer.lap_ms()

    # LOGGER.debug(f"pt_dims={pt_dims}")
    # LOGGER.debug(f"vertex_arr.shape={vertex_arr.shape}")
    # LOGGER.debug(f"vertex_arr.dtype={vertex_arr.dtype}")
    # LOGGER.debug(f"conn_arr.shape={conn_arr.shape}")
    # LOGGER.debug(f"conn_arr.dtype={conn_arr.dtype}")

    vtk_esgrid = _create_vtk_esgrid_from_verts_and_conn(pt_dims, vertex_arr, conn_arr)
    et_create_vtk_esg_ms = timer.lap_ms()

    # Make sure we hide the inactive cells.
    # First we let VTK allocate cell ghost array, then we obtain a numpy view
    # on the array and write to that (we're actually modifying the native VTK array)
    ghost_arr_vtk = vtk_esgrid.AllocateCellGhostArray()
    ghost_arr_np = vtk_to_numpy(ghost_arr_vtk)
    ghost_arr_np[inactive_arr] = vtkDataSetAttributes.HIDDENCELL

    LOGGER.debug(
        f"xtgeo_grid_to_vtk_explicit_structured_grid() took {timer.elapsed_s():.2f}s "
        f"(get_esg_geo_data={et_get_esg_geo_data_ms}ms, "
        f"create_vtk_esg={et_create_vtk_esg_ms}ms)"
    )

    return vtk_esgrid


# -----------------------------------------------------------------------------
def _create_vtk_esgrid_from_verts_and_conn(
    point_dims: np.ndarray, vertex_arr_np: np.ndarray, conn_arr_np: np.ndarray
) -> vtkExplicitStructuredGrid:

    vertex_arr_np = vertex_arr_np.reshape(-1, 3)
    points_vtkarr = numpy_to_vtk(vertex_arr_np, deep=1)
    vtk_points = vtkPoints()
    vtk_points.SetData(points_vtkarr)

    # conn_idarr = numpy_to_vtk(conn_arr_np, deep=1, array_type=vtkConstants.VTK_ID_TYPE)
    conn_idarr = numpy_to_vtkIdTypeArray(conn_arr_np, deep=1)
    vtk_cell_array = vtkCellArray()
    vtk_cell_array.SetData(8, conn_idarr)

    vtk_esgrid = vtkExplicitStructuredGrid()
    vtk_esgrid.SetDimensions(point_dims)
    vtk_esgrid.SetPoints(vtk_points)
    vtk_esgrid.SetCells(vtk_cell_array)

    vtk_esgrid.ComputeFacesConnectivityFlagsArray()

    return vtk_esgrid

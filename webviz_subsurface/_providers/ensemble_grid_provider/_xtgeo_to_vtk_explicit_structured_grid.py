import xtgeo
import numpy as np

# pylint: disable=no-name-in-module,
from vtkmodules.vtkCommonDataModel import vtkExplicitStructuredGrid
from vtkmodules.vtkCommonDataModel import vtkCellArray
from vtkmodules.vtkCommonDataModel import vtkDataSetAttributes
from vtkmodules.vtkCommonCore import vtkPoints
from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.util.numpy_support import numpy_to_vtkIdTypeArray
from vtkmodules.util.numpy_support import vtk_to_numpy
from vtkmodules.util import vtkConstants

from webviz_subsurface._utils.perf_timer import PerfTimer

# from ._xtgeo_to_explicit_structured_grid_hack import (
#     _clean_vtk_ug,
#     _vtk_esg_to_ug,
#     _vtk_ug_to_esg,
# )


# -----------------------------------------------------------------------------
def xtgeo_grid_to_vtk_explicit_structured_grid(
    xtg_grid: xtgeo.Grid,
) -> vtkExplicitStructuredGrid:

    print("entering xtgeo_grid_to_vtk_explicit_structured_grid()")
    t = PerfTimer()

    pt_dims, vertex_arr, conn_arr, inactive_arr = xtg_grid.get_vtk_esg_geometry_data()
    vertex_arr[:, 2] *= -1
    print(f"get_vtk_esg_geometry_data() took {t.lap_s():.2f}s")

    print(f"{pt_dims=}")
    print(f"{vertex_arr.shape=}")
    print(f"{vertex_arr.dtype=}")
    print(f"{conn_arr.shape=}")
    print(f"{conn_arr.dtype=}")

    vtk_esgrid = _create_vtk_esgrid_from_verts_and_conn(pt_dims, vertex_arr, conn_arr)
    print(f"create vtk_esgrid : {t.lap_s():.2f}s")

    # Make sure we hide the inactive cells.
    # First we let VTK allocate cell ghost array, then we obtain a numpy view
    # on the array and write to that (we're actually modifying the native VTK array)
    ghost_arr_vtk = vtk_esgrid.AllocateCellGhostArray()
    ghost_arr_np = vtk_to_numpy(ghost_arr_vtk)
    ghost_arr_np[inactive_arr] = vtkDataSetAttributes.HIDDENCELL
    print(f"hide {len(inactive_arr)} inactive cells : {t.lap_s():.2f}s")

    print(f"memory used by vtk_esgrid: {vtk_esgrid.GetActualMemorySize()/1024.0:.2f}MB")

    print(f"xtgeo_grid_to_vtk_explicit_structured_grid() - DONE: {t.elapsed_s():.2f}s")

    # print("==================================================================")
    # print(pv.ExplicitStructuredGrid(vtk_esgrid))
    # print("==================================================================")

    return vtk_esgrid


# -----------------------------------------------------------------------------
def _create_vtk_esgrid_from_verts_and_conn(
    point_dims: np.ndarray, vertex_arr_np: np.ndarray, conn_arr_np: np.ndarray
) -> vtkExplicitStructuredGrid:

    print("_create_vtk_esgrid_from_verts_and_conn() - entering")

    t = PerfTimer()

    vertex_arr_np = vertex_arr_np.reshape(-1, 3)
    points_vtkarr = numpy_to_vtk(vertex_arr_np, deep=1)
    vtk_points = vtkPoints()
    vtk_points.SetData(points_vtkarr)
    print(f"_create_vtk_esgrid_from_verts_and_conn() - vtk_points: {t.lap_s():.2f}s")

    # conn_idarr = numpy_to_vtk(conn_arr_np, deep=1, array_type=vtkConstants.VTK_ID_TYPE)
    conn_idarr = numpy_to_vtkIdTypeArray(conn_arr_np, deep=1)
    vtk_cellArray = vtkCellArray()
    vtk_cellArray.SetData(8, conn_idarr)
    print(f"_create_vtk_esgrid_from_verts_and_conn() - vtk_cellArray: {t.lap_s():.2f}s")

    vtk_esgrid = vtkExplicitStructuredGrid()
    vtk_esgrid.SetDimensions(point_dims)
    vtk_esgrid.SetPoints(vtk_points)
    vtk_esgrid.SetCells(vtk_cellArray)
    print(f"_create_vtk_esgrid_from_verts_and_conn() - vtk_esgrid: {t.lap_s():.2f}s")

    vtk_esgrid.ComputeFacesConnectivityFlagsArray()
    print(f"_create_vtk_esgrid_from_verts_and_conn() - conn flags: {t.lap_s():.2f}s")

    # print(pv.ExplicitStructuredGrid(vtk_esgrid))
    # ugrid = _vtk_esg_to_ug(vtk_esgrid)
    # ugrid = _clean_vtk_ug(ugrid)
    # vtk_esgrid = _vtk_ug_to_esg(ugrid)
    # print(pv.ExplicitStructuredGrid(vtk_esgrid))

    print(f"_create_vtk_esgrid_from_verts_and_conn() - DONE: {t.elapsed_s():.2f}s")

    return vtk_esgrid

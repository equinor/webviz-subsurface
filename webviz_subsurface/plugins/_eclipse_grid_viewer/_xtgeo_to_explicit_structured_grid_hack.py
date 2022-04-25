import xtgeo
import pyvista as pv
import numpy as np

# pylint: disable=no-name-in-module,
from vtkmodules.vtkFiltersCore import vtkStaticCleanUnstructuredGrid
from vtkmodules.vtkFiltersCore import vtkUnstructuredGridToExplicitStructuredGrid
from vtkmodules.vtkFiltersCore import vtkExplicitStructuredGridToUnstructuredGrid
from vtkmodules.vtkCommonDataModel import vtkUnstructuredGrid
from vtkmodules.vtkCommonDataModel import vtkExplicitStructuredGrid
from vtkmodules.vtkCommonDataModel import vtkCellArray
from vtkmodules.vtkCommonCore import vtkPoints

from vtkmodules.util.numpy_support import numpy_to_vtk
from vtkmodules.util.numpy_support import numpy_to_vtkIdTypeArray
from vtkmodules.util import vtkConstants

from webviz_subsurface._utils.perf_timer import PerfTimer


# Note that this implementation requires both:
#  * hacked xtgeo
#  * VTK version 9.2
# -----------------------------------------------------------------------------
def xtgeo_grid_to_explicit_structured_grid_hack(
    xtg_grid: xtgeo.Grid,
) -> pv.ExplicitStructuredGrid:

    print("entering xtgeo_grid_to_explicit_structured_grid_hack()")
    t = PerfTimer()

    dims, corners, inactive = xtg_grid.get_vtk_geometries_hack()
    corners[:, 2] *= -1
    print(f"call to get_vtk_geometries_hack() took {t.lap_s():.2f}s")

    # print(f"{dims=}")
    # print(f"{type(corners)=}")
    # print(f"{corners.shape=}")
    # print(f"{corners.dtype=}")

    vtk_esgrid = _make_clean_vtk_esgrid(dims, corners)
    print(f"create vtk_esgrid : {t.lap_s():.2f}s")

    pv_esgrid = pv.ExplicitStructuredGrid(vtk_esgrid)
    print(f"create pv grid from vtk grid: {t.lap_s():.2f}s")

    pv_esgrid = pv_esgrid.hide_cells(inactive)
    print(f"pv_esgrid.hide_cells(inactive) : {t.lap_s():.2f}s")

    print(f"xtgeo_grid_to_explicit_structured_grid_hack() - DONE: {t.elapsed_s():.2f}s")

    print("==================================================================")
    print(pv_esgrid)
    print("==================================================================")

    return pv_esgrid


# -----------------------------------------------------------------------------
def _make_clean_vtk_esgrid(dims, corners):

    print("entering _make_clean_vtk_esgrid()")

    timer = PerfTimer()

    points_np = corners
    points_np = points_np.reshape(-1, 3)
    # points_np = points_np.astype(np.float32)

    points_vtkarr = numpy_to_vtk(points_np, deep=1)
    vtk_points = vtkPoints()
    vtk_points.SetData(points_vtkarr)

    print(f"_make_clean_vtk_esgrid() - create points: {timer.lap_s():.2f}s")

    # Dims are number of points, so subtract 1 to get cell counts
    num_conn = (dims[0] - 1) * (dims[1] - 1) * (dims[2] - 1) * 8
    conn_np = np.arange(0, num_conn)

    # cellconn_idarr = numpy_to_vtk(conn_np, deep=1, array_type=vtkConstants.VTK_ID_TYPE)
    cellconn_idarr = numpy_to_vtkIdTypeArray(conn_np, deep=1)

    vtk_cellArray = vtkCellArray()
    vtk_cellArray.SetData(8, cellconn_idarr)

    print(f"_make_clean_vtk_esgrid() - create cells: {timer.lap_s():.2f}s")

    vtk_esgrid = vtkExplicitStructuredGrid()
    vtk_esgrid.SetDimensions(dims)
    vtk_esgrid.SetPoints(vtk_points)
    vtk_esgrid.SetCells(vtk_cellArray)

    print(f"_make_clean_vtk_esgrid() - create initial grid: {timer.lap_s():.2f}s")

    # print(pv.ExplicitStructuredGrid(vtk_esgrid))

    ugrid = _vtk_esg_to_ug(vtk_esgrid)
    print(f"_make_clean_vtk_esgrid() - esg to ug: {timer.lap_s():.2f}s")
    ugrid = _clean_vtk_ug(ugrid)
    print(f"_make_clean_vtk_esgrid() - clean ug: {timer.lap_s():.2f}s")
    vtk_esgrid = _vtk_ug_to_esg(ugrid)
    print(f"_make_clean_vtk_esgrid() - ug to esg: {timer.lap_s():.2f}s")

    # print(pv.ExplicitStructuredGrid(vtk_esgrid))

    print(f"_make_clean_vtk_esgrid() - clean: {timer.lap_s():.2f}s")

    vtk_esgrid.ComputeFacesConnectivityFlagsArray()

    print(f"_make_clean_vtk_esgrid() - conn flags: {timer.lap_s():.2f}s")

    print(f"_make_clean_vtk_esgrid() - DONE: {timer.elapsed_s():.2f}s")

    return vtk_esgrid


# -----------------------------------------------------------------------------
def _vtk_esg_to_ug(vtk_esgrid: vtkExplicitStructuredGrid) -> vtkUnstructuredGrid:
    convertFilter = vtkExplicitStructuredGridToUnstructuredGrid()
    convertFilter.SetInputData(vtk_esgrid)
    convertFilter.Update()
    vtk_ugrid = convertFilter.GetOutput()

    return vtk_ugrid


# -----------------------------------------------------------------------------
def _vtk_ug_to_esg(vtk_ugrid: vtkUnstructuredGrid) -> vtkExplicitStructuredGrid:
    convertFilter = vtkUnstructuredGridToExplicitStructuredGrid()
    convertFilter.SetInputData(vtk_ugrid)
    convertFilter.SetInputArrayToProcess(0, 0, 0, 1, "BLOCK_I")
    convertFilter.SetInputArrayToProcess(1, 0, 0, 1, "BLOCK_J")
    convertFilter.SetInputArrayToProcess(2, 0, 0, 1, "BLOCK_K")
    convertFilter.Update()
    vtk_esgrid = convertFilter.GetOutput()

    return vtk_esgrid


# -----------------------------------------------------------------------------
def _clean_vtk_ug(vtk_ugrid: vtkUnstructuredGrid) -> vtkUnstructuredGrid:

    # !!!!!!
    # Requires newer version of VTK
    cleanfilter = vtkStaticCleanUnstructuredGrid()
    # print(cleanfilter)

    cleanfilter.SetInputData(vtk_ugrid)
    cleanfilter.SetAbsoluteTolerance(0.0)
    cleanfilter.SetTolerance(0.0)
    cleanfilter.SetToleranceIsAbsolute(True)
    cleanfilter.GetLocator().SetTolerance(0.0)
    cleanfilter.Update()

    # print(cleanfilter)
    # print(cleanfilter.GetLocator())

    vtk_ugrid_out = cleanfilter.GetOutput()

    return vtk_ugrid_out

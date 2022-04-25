from typing import List, Optional, Tuple

import numpy as np

# pylint: disable=no-name-in-module, import-error
from vtk.util.numpy_support import vtk_to_numpy
from vtkmodules.vtkCommonCore import reference  # , vtkIdList

# pylint: disable=no-name-in-module,
from vtkmodules.vtkCommonDataModel import (
    vtkCellLocator,
    vtkExplicitStructuredGrid,
    vtkGenericCell,
    vtkPolyData,
)

# pylint: disable=no-name-in-module,
from vtkmodules.vtkFiltersCore import vtkExplicitStructuredGridCrop

# pylint: disable=no-name-in-module,
from vtkmodules.vtkFiltersGeometry import vtkExplicitStructuredGridSurfaceFilter

from webviz_subsurface._utils.perf_timer import PerfTimer


class ExplicitStructuredGridAccessor:
    def __init__(self, es_grid: vtkExplicitStructuredGrid) -> None:
        self.es_grid = es_grid
        self.cell_dimensions = [-1, -1, -1]
        self.es_grid.GetCellDims(self.cell_dimensions)

        self.extract_skin_filter = (
            vtkExplicitStructuredGridSurfaceFilter()
        )  # Is this thread safe?

    def crop(
        self, irange: List[int], jrange: List[int], krange: List[int]
    ) -> vtkExplicitStructuredGrid:
        """Crops grids within specified ijk ranges. Original cell indices
        kept as vtkOriginalCellIds CellArray"""
        crop_filter = vtkExplicitStructuredGridCrop()
        crop_filter.SetInputData(self.es_grid)
        crop_filter.SetOutputWholeExtent(
            irange[0],
            irange[1] + 1,
            jrange[0],
            jrange[1] + 1,
            krange[0],
            krange[1] + 1,
        )
        crop_filter.Update()

        grid = crop_filter.GetOutput()
        timer = PerfTimer()
        print(f"to pyvista {timer.lap_s()}")
        return grid

    def extract_skin(
        self, grid: vtkExplicitStructuredGrid = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Extracts skin from a provided cropped grid or the entire grid if
        no grid is given.

        Returns polydata and indices of original cell ids"""
        grid = grid if grid is not None else self.es_grid

        self.extract_skin_filter.SetInputData(grid)
        self.extract_skin_filter.PassThroughCellIdsOn()
        self.extract_skin_filter.Update()
        polydata: vtkPolyData = self.extract_skin_filter.GetOutput()
        polys = vtk_to_numpy(polydata.GetPolys().GetData())
        points = vtk_to_numpy(polydata.GetPoints().GetData()).ravel()
        indices = vtk_to_numpy(
            polydata.GetCellData().GetAbstractArray("vtkOriginalCellIds")
        )
        return (
            polys,
            points.astype(np.float32),
            indices,
        )

    def find_closest_cell_to_ray(
        self, grid: vtkExplicitStructuredGrid, ray: List[float]
    ) -> Tuple[Optional[int], List[Optional[int]]]:
        """Find the active cell closest to the given ray."""
        timer = PerfTimer()
        locator = vtkCellLocator()

        locator.SetDataSet(grid)
        locator.BuildLocator()

        # cell_ids = vtkIdList()
        tolerance = reference(0.0)

        _t = reference(0)
        _x = np.array([0, 0, 0])
        _pcoords = np.array([0, 0, 0])
        _sub_id = reference(0)
        cell_id = reference(0)
        _cell = vtkGenericCell()

        locator.IntersectWithLine(
            ray[0], ray[1], tolerance, _t, _x, _pcoords, _sub_id, cell_id, _cell
        )

        # # Check if an array with OriginalCellIds is present, and if so use
        # # that as the cell index, if not assume the grid is not cropped.
        if grid.GetCellData().HasArray("vtkOriginalCellIds") == 1:
            cell_id = vtk_to_numpy(
                grid.GetCellData().GetAbstractArray("vtkOriginalCellIds")
            )[cell_id]

        i = reference(0)
        j = reference(0)
        k = reference(0)

        # Find the ijk of the cell in the full grid
        self.es_grid.ComputeCellStructuredCoords(cell_id, i, j, k, False)
        print(f"Get ijk in  {timer.lap_s():.2f}")

        return cell_id, [int(i), int(j), int(k)]

    @property
    def imin(self) -> int:
        return 0

    @property
    def imax(self) -> int:
        return self.cell_dimensions[0] - 1

    @property
    def jmin(self) -> int:
        return 0

    @property
    def jmax(self) -> int:
        return self.cell_dimensions[1] - 1

    @property
    def kmin(self) -> int:
        return 0

    @property
    def kmax(self) -> int:
        return self.cell_dimensions[2] - 1

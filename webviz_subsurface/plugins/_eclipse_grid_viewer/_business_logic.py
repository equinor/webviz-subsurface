from pathlib import Path
from typing import List, Tuple

import numpy as np
import pyvista as pv
import xtgeo

# pylint: disable=no-name-in-module, import-error
from vtk.util.numpy_support import vtk_to_numpy

# pylint: disable=no-name-in-module,
from vtkmodules.vtkCommonDataModel import (
    vtkExplicitStructuredGrid,
    vtkCellLocator,
    vtkGenericCell,
)
from vtkmodules.vtkCommonCore import mutable, vtkIdList

# pylint: disable=no-name-in-module,
from vtkmodules.vtkFiltersCore import vtkExplicitStructuredGridCrop

# pylint: disable=no-name-in-module,
from vtkmodules.vtkFiltersGeometry import vtkExplicitStructuredGridSurfaceFilter
from dash_vtk.utils.vtk import b64_encode_numpy

from webviz_subsurface._utils.perf_timer import PerfTimer


def xtgeo_grid_to_explicit_structured_grid(
    xtg_grid: xtgeo.Grid,
) -> pv.ExplicitStructuredGrid:
    dims, corners, inactive = xtg_grid.get_vtk_geometries()
    corners[:, 2] *= -1
    esg_grid = pv.ExplicitStructuredGrid(dims, corners)
    esg_grid = esg_grid.compute_connectivity()
    esg_grid.ComputeFacesConnectivityFlagsArray()
    esg_grid = esg_grid.hide_cells(inactive)
    # esg_grid.flip_z(inplace=True)
    return esg_grid


class ExplicitStructuredGridProvider:
    def __init__(self, esg_grid: pv.ExplicitStructuredGrid) -> None:
        self.esg_grid = esg_grid
        self.extract_skin_filter = vtkExplicitStructuredGridSurfaceFilter()

    def crop(
        self, irange: List[int], jrange: List[int], krange: List[int]
    ) -> vtkExplicitStructuredGrid:
        """Crops grids within specified ijk ranges. Original cell indices
        kept as vtkOriginalCellIds CellArray"""
        crop_filter = vtkExplicitStructuredGridCrop()
        crop_filter.SetInputData(self.esg_grid)
        crop_filter.SetOutputWholeExtent(
            irange[0], irange[1] + 1, jrange[0], jrange[1] + 1, krange[0], krange[1] + 1
        )
        crop_filter.Update()

        grid = crop_filter.GetOutput()
        timer = PerfTimer()
        grid = pv.ExplicitStructuredGrid(grid)
        print(f"to pyvista {timer.lap_s()}")
        return grid

    def extract_skin(
        self, grid: pv.ExplicitStructuredGrid = None
    ) -> Tuple[str, str, np.ndarray]:
        """Extracts skin from a provided cropped grid or the entire grid if
        no grid is given.

        Returns polydata and indices of original cell ids"""
        grid = grid if grid is not None else self.esg_grid

        self.extract_skin_filter.SetInputData(grid)
        self.extract_skin_filter.PassThroughCellIdsOn()
        self.extract_skin_filter.Update()
        polydata = self.extract_skin_filter.GetOutput()
        polydata = pv.PolyData(polydata)
        polys = vtk_to_numpy(polydata.GetPolys().GetData())
        points = vtk_to_numpy(polydata.points).ravel()
        indices = polydata["vtkOriginalCellIds"]

        return (
            b64_encode_numpy(polys),
            b64_encode_numpy(points.astype(np.float32)),
            indices,
        )

    def find_closest_cell_ray_to_ray(self, grid, ray):
        """OBS! OBS! Currently picks the layer above the visualized layer.
        Solve by e.g. shifting the z value? Getting cell neighbours?..."""
        timer = PerfTimer()
        locator = vtkCellLocator()
        locator.SetDataSet(grid)
        locator.BuildLocator()

        cell_ids = vtkIdList()
        tolerance = mutable(0.0)

        # Find the closest cell in the cropped grid
        locator.FindCellsAlongLine(ray[0], ray[1], tolerance, cell_ids)

        # Find the closest active cell index in the full grid
        relative_cell_id = None
        for cell_idx in range(0, cell_ids.GetNumberOfIds()):
            cell_id = cell_ids.GetId(cell_idx)
            if grid["vtkGhostType"][cell_id] == 0:
                relative_cell_id = cell_id
                break

        # If no cells are found return None
        if relative_cell_id is None:
            return None, [None, None, None]

        absolute_cell_id = grid["vtkOriginalCellIds"][relative_cell_id]

        print(f"Closest cell in {timer.lap_s():.2f}")

        i = mutable(0)
        j = mutable(0)
        k = mutable(0)
        pcoords = mutable([0, 0, 0])

        # Find the ijk of the cell in the full grid
        self.esg_grid.ComputeCellStructuredCoords(absolute_cell_id, i, j, k, False)
        print(f"Get ijk in  {timer.lap_s():.2f}")

        return absolute_cell_id, [int(i), int(j), int(k)]

    @staticmethod
    def array_to_base64(array: np.ndarray) -> str:
        return b64_encode_numpy(array.astype(np.float32))

    @property
    def imin(self) -> int:
        return 0

    @property
    def imax(self) -> int:
        return self.esg_grid.dimensions[0] - 2

    @property
    def jmin(self) -> int:
        return 0

    @property
    def jmax(self) -> int:
        return self.esg_grid.dimensions[1] - 2

    @property
    def kmin(self) -> int:
        return 0

    @property
    def kmax(self) -> int:
        return self.esg_grid.dimensions[2] - 2


class EclipseGridDataModel:
    def __init__(
        self,
        egrid_file: Path,
        init_file: Path,
        restart_file: Path,
        init_names: List[str],
        restart_names: List[str],
    ):
        self._egrid_file = egrid_file
        self._init_file = init_file
        self._restart_file = restart_file
        self._init_names = init_names
        self._restart_names = restart_names

        # Eclipse grid geometry required when loading grid properties later on
        self._xtg_grid = xtgeo.grid_from_file(egrid_file, fformat="egrid")

        timer = PerfTimer()
        print("Converting egrid to VTK ExplicitStructuredGrid")
        self.esg_provider = ExplicitStructuredGridProvider(
            xtgeo_grid_to_explicit_structured_grid(self._xtg_grid)
        )
        print(f"Conversion complete in : {timer.lap_s():.2f}s")
        self._restart_dates = self._get_restart_dates()

    def _get_restart_dates(self) -> List[str]:
        return xtgeo.GridProperties.scan_dates(self._restart_file, datesonly=True)

    @property
    def init_names(self) -> List[str]:
        return self._init_names

    @property
    def restart_names(self) -> List[str]:
        return self._restart_names

    @property
    def restart_dates(self) -> List[str]:
        return self._restart_dates

    def get_init_property(self, prop_name: str) -> np.ndarray:

        prop = xtgeo.gridproperty_from_file(
            self._init_file, fformat="init", name=prop_name, grid=self._xtg_grid
        )
        return prop

    def get_restart_property(self, prop_name: str, prop_date: int) -> np.ndarray:
        timer = PerfTimer()
        prop = xtgeo.gridproperty_from_file(
            self._restart_file,
            fformat="unrst",
            name=prop_name,
            date=prop_date,
            grid=self._xtg_grid,
        )
        return prop

    def get_init_values(self, prop_name: str):
        prop = self.get_init_property(prop_name)
        return prop.get_npvalues1d(order="F").ravel()

    def get_restart_values(self, prop_name: str, prop_date: int):
        prop = self.get_restart_property(prop_name, prop_date)
        return prop.get_npvalues1d(order="F").ravel()

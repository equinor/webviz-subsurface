from pathlib import Path
from typing import List, Tuple

import numpy as np
import pyvista as pv
import xtgeo

# pylint: disable=no-name-in-module, import-error
from vtk.util.numpy_support import vtk_to_numpy

# pylint: disable=no-name-in-module,
from vtkmodules.vtkCommonDataModel import vtkExplicitStructuredGrid

# pylint: disable=no-name-in-module,
from vtkmodules.vtkFiltersCore import vtkExplicitStructuredGridCrop

# pylint: disable=no-name-in-module,
from vtkmodules.vtkFiltersGeometry import vtkExplicitStructuredGridSurfaceFilter

from webviz_subsurface._utils.perf_timer import PerfTimer


def xtgeo_grid_to_explicit_structured_grid(
    xtg_grid: xtgeo.Grid,
) -> pv.ExplicitStructuredGrid:
    dims, corners, inactive = xtg_grid.get_vtk_geometries()
    esg_grid = pv.ExplicitStructuredGrid(dims, corners)

    esg_grid = esg_grid.compute_connectivity()
    esg_grid.ComputeFacesConnectivityFlagsArray()
    esg_grid = esg_grid.hide_cells(inactive)
    esg_grid.flip_z(inplace=True)
    return esg_grid


class ExplicitStructuredGridProvider:
    def __init__(self, esg_grid: pv.ExplicitStructuredGrid) -> None:
        self.esg_grid = esg_grid

    def crop(
        self, irange: List[int], jrange: List[int], krange: List[int]
    ) -> vtkExplicitStructuredGrid:
        crop_filter = vtkExplicitStructuredGridCrop()
        crop_filter.SetInputData(self.esg_grid)
        crop_filter.SetOutputWholeExtent(
            irange[0], irange[1], jrange[0], jrange[1], krange[0], krange[1]
        )
        crop_filter.Update()
        grid = crop_filter.GetOutput()
        return self.extract_skin(grid)

    def extract_skin(
        self, grid: vtkExplicitStructuredGrid = None
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        grid = grid if grid is not None else self.esg_grid
        extract_skin_filter = vtkExplicitStructuredGridSurfaceFilter()
        extract_skin_filter.SetInputData(grid)
        extract_skin_filter.PassThroughCellIdsOn()
        extract_skin_filter.Update()
        polydata = extract_skin_filter.GetOutput()
        polydata = pv.PolyData(polydata)
        polys = vtk_to_numpy(polydata.GetPolys().GetData())
        points = vtk_to_numpy(polydata.points).ravel()
        indices = polydata["vtkOriginalCellIds"]
        return polys, points, indices

    @property
    def imin(self) -> int:
        return 0

    @property
    def imax(self) -> int:
        return self.esg_grid.dimensions[0] - 1

    @property
    def jmin(self) -> int:
        return 0

    @property
    def jmax(self) -> int:
        return self.esg_grid.dimensions[1] - 1

    @property
    def kmin(self) -> int:
        return 0

    @property
    def kmax(self) -> int:
        return self.esg_grid.dimensions[2] - 1


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
        return prop.get_npvalues1d(order="F").ravel()

    def get_restart_property(self, prop_name: str, prop_date: int) -> np.ndarray:
        timer = PerfTimer()
        prop = xtgeo.gridproperty_from_file(
            self._restart_file,
            fformat="unrst",
            name=prop_name,
            date=prop_date,
            grid=self._xtg_grid,
        )
        print(
            f"Read {prop_name}, {prop_date} from restart file in {timer.lap_s():.2f}s"
        )
        vals = prop.get_npvalues1d(order="F")

        return vals

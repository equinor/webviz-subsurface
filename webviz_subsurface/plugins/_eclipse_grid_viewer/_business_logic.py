from pathlib import Path
from typing import List

import numpy as np
import pyvista as pv
import xtgeo

# pylint: disable=no-name-in-module, import-error
from vtk.util.numpy_support import vtk_to_numpy

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
        timer = PerfTimer()
        self.surface_polydata = self._extract_surface()
        print(f"Extracted grid skin in : {timer.lap_s():.2f}s")
        self.surface_polys = vtk_to_numpy(self.surface_polydata.GetPolys().GetData())

        self.surface_points = vtk_to_numpy(self.surface_polydata.points).ravel()

    def _extract_surface(
        self,
    ) -> pv.PolyData:
        """Extract and keep the grid surface. Also keep track of cell indices, to be used
        to extract indices from the scalar arrays"""
        extract_skin_filter = vtkExplicitStructuredGridSurfaceFilter()
        extract_skin_filter.SetInputData(self.esg_grid)
        extract_skin_filter.PassThroughCellIdsOn()
        extract_skin_filter.Update()
        return pv.PolyData(extract_skin_filter.GetOutput())


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

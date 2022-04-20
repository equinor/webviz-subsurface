from pathlib import Path
from typing import Callable, List, Tuple

import numpy as np
import xtgeo

from webviz_subsurface._utils.perf_timer import PerfTimer
from webviz_subsurface._utils.webvizstore_functions import get_path

from ._xtgeo_to_explicit_structured_grid import xtgeo_grid_to_explicit_structured_grid
from ._explicit_structured_grid_accessor import ExplicitStructuredGridAccessor


class EclipseGridDataModel:
    def __init__(
        self,
        egrid_file: Path,
        init_file: Path,
        restart_file: Path,
        init_names: List[str],
        restart_names: List[str],
    ):
        self.add_webviz_store(egrid_file, init_file, restart_file)
        self._egrid_file = get_path(egrid_file)
        self._init_file = get_path(init_file)
        self._restart_file = get_path(restart_file)
        self._init_names = init_names
        self._restart_names = restart_names

        # Eclipse grid geometry required when loading grid properties later on
        self._xtg_grid = xtgeo.grid_from_file(egrid_file, fformat="egrid")

        timer = PerfTimer()
        print("Converting egrid to VTK ExplicitStructuredGrid")
        self.esg_accessor = ExplicitStructuredGridAccessor(
            xtgeo_grid_to_explicit_structured_grid(self._xtg_grid)
        )
        print(f"Conversion complete in : {timer.lap_s():.2f}s")
        self._restart_dates = self._get_restart_dates()

    def add_webviz_store(
        self, egrid_file: Path, init_file: Path, restart_file: Path
    ) -> None:
        self._webviz_store: List[Tuple[Callable, List[dict]]] = [
            (
                get_path,
                [{"path": path} for path in [egrid_file, init_file, restart_file]],
            )
        ]

    @property
    def webviz_store(self) -> List[Tuple[Callable, List[dict]]]:
        return self._webviz_store

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

    def get_init_property(self, prop_name: str) -> xtgeo.GridProperty:

        prop = xtgeo.gridproperty_from_file(
            self._init_file, fformat="init", name=prop_name, grid=self._xtg_grid
        )
        return prop

    def get_restart_property(
        self, prop_name: str, prop_date: int
    ) -> xtgeo.GridProperty:
        prop = xtgeo.gridproperty_from_file(
            self._restart_file,
            fformat="unrst",
            name=prop_name,
            date=prop_date,
            grid=self._xtg_grid,
        )
        return prop

    def get_init_values(self, prop_name: str) -> np.ndarray:
        prop = self.get_init_property(prop_name)
        return prop.get_npvalues1d(order="F").ravel()

    def get_restart_values(self, prop_name: str, prop_date: int) -> np.ndarray:
        prop = self.get_restart_property(prop_name, prop_date)
        return prop.get_npvalues1d(order="F").ravel()

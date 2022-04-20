from pathlib import Path
from typing import Callable, List, Tuple

import numpy as np
import xtgeo

from webviz_subsurface._utils.perf_timer import PerfTimer
from webviz_subsurface._utils.webvizstore_functions import get_path

from ._xtgeo_to_explicit_structured_grid import xtgeo_grid_to_explicit_structured_grid
from ._explicit_structured_grid_accessor import ExplicitStructuredGridAccessor


def get_static_parameter_names(folder: Path, grid_name: str):
    return list(
        set(
            fn.stem.split("--")[1]
            for fn in Path(folder).glob(f"{grid_name}*.roff")
            if len(fn.stem.split("--")) == 2
        )
    )


def get_dynamic_parameter_names(folder: Path, grid_name: str):
    return list(
        set(
            fn.stem.split("--")[1]
            for fn in Path(folder).glob(f"{grid_name}*.roff")
            if len(fn.stem.split("--")) == 3
        )
    )


def get_dynamic_parameter_dates(folder: Path, grid_name: str):

    return list(
        set(
            fn.stem.split("--")[2]
            for fn in Path(folder).glob(f"{grid_name}*.roff")
            if len(fn.stem.split("--")) == 3
        )
    )


class RoffGridDataModel:
    def __init__(
        self,
        folder: Path,
        grid_name: Path,
    ):

        # self.add_webviz_store(egrid_file, init_file, restart_file)

        self.folder = folder
        self.grid_name = grid_name
        # Grid required when loading grid properties later on
        self._xtg_grid = xtgeo.grid_from_file(Path(folder / f"{grid_name}.roff"))

        timer = PerfTimer()
        print("Converting egrid to VTK ExplicitStructuredGrid")
        self.esg_accessor = ExplicitStructuredGridAccessor(
            xtgeo_grid_to_explicit_structured_grid(self._xtg_grid)
        )
        print(f"Conversion complete in : {timer.lap_s():.2f}s")
        self._restart_dates = self

    @property
    def init_names(self) -> List[str]:
        return get_static_parameter_names(self.folder, self.grid_name)

    @property
    def restart_names(self) -> List[str]:
        return get_dynamic_parameter_names(self.folder, self.grid_name)

    @property
    def restart_dates(self) -> List[str]:
        return get_dynamic_parameter_dates(self.folder, self.grid_name)

    def get_init_property(self, prop_name: str) -> xtgeo.GridProperty:
        path = Path(self.folder / f"{self.grid_name}--{prop_name}.roff")
        prop = xtgeo.gridproperty_from_file(path)
        return prop

    def get_restart_property(
        self, prop_name: str, prop_date: int
    ) -> xtgeo.GridProperty:
        path = Path(self.folder / f"{self.grid_name}--{prop_name}--{prop_date}.roff")
        prop = xtgeo.gridproperty_from_file(path)
        return prop

    def get_init_values(self, prop_name: str) -> np.ndarray:
        prop = self.get_init_property(prop_name)
        return prop.get_npvalues1d(order="F").ravel()

    def get_restart_values(self, prop_name: str, prop_date: int) -> np.ndarray:
        prop = self.get_restart_property(prop_name, prop_date)
        return prop.get_npvalues1d(order="F").ravel()

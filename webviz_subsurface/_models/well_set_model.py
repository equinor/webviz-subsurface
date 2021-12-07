import warnings
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import xtgeo
from webviz_config.common_cache import CACHE

from webviz_subsurface._utils.webvizstore_functions import get_path


class WellSetModel:
    """Class to load and store Xtgeo Wells"""

    def __init__(
        self,
        wellfiles: List[Path],
        zonelog: str = None,
        mdlog: str = None,
        tvdmin: float = None,
        tvdmax: float = None,
        downsample_interval: int = None,
    ):
        self._wellfiles = wellfiles
        self._zonelog = zonelog
        self._mdlog = mdlog
        self._tvdmin = tvdmin
        self._tvdmax = tvdmax
        self._downsample = downsample_interval
        self._wells = self._load_wells()

    def _load_wells(self) -> Dict[str, xtgeo.Well]:
        """Load all wells, performing optional truncation and
        coarsening"""

        wells: List[xtgeo.Well] = []
        for wellpath in self._wellfiles:
            try:
                well = load_well(
                    get_path(wellpath), zonelogname=self._zonelog, mdlogname=self._mdlog
                )
            except ValueError:
                warnings.warn(f"Cannot load invalid well: {str(wellpath)}")
                continue
            if self._tvdmin is not None:
                well.dataframe = well.dataframe[
                    well.dataframe["Z_TVDSS"] >= self._tvdmin
                ]
                well.dataframe.reset_index(drop=True, inplace=True)
            if self._tvdmax is not None:
                well.dataframe = well.dataframe[
                    well.dataframe["Z_TVDSS"] <= self._tvdmax
                ]
                well.dataframe.reset_index(drop=True, inplace=True)
            if self._downsample is not None:
                well.downsample(interval=self._downsample)
            if self._mdlog is None:
                well.geometrics()
            # Create a relative XYLENGTH vector (0.0 where well starts)
            well.create_relative_hlen()
            wells.append(well)
        return {well.name: well for well in wells}

    @property
    def wells(self) -> Dict[str, xtgeo.Well]:
        """Return a dictionary of well names and well objects"""
        return self._wells

    def get_well(self, well_name: str) -> xtgeo.Well:
        """Returns a well object given a well name"""
        return self.wells[well_name]

    @property
    def well_names(self) -> List[str]:
        """Returns list of well names"""
        return list(self._wells.keys())

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def get_fence(
        self,
        well_name: str,
        distance: float = 20,
        atleast: int = 5,
        nextend: int = 2,
    ) -> np.ndarray:
        """Creates a fence specification from a well"""
        if not self._is_vertical(well_name):
            return self.wells[well_name].get_fence_polyline(
                nextend=nextend, sampling=distance, asnumpy=True
            )
        # If well is completely vertical extend well fence
        poly = self.wells[well_name].get_fence_polyline(
            nextend=0.1, sampling=distance, asnumpy=False
        )

        return poly.get_fence(
            distance=distance, atleast=atleast, nextend=nextend, asnumpy=True
        )

    def _is_vertical(self, well_name: str) -> bool:
        return (
            self.wells[well_name].dataframe["X_UTME"].nunique() == 1
            and self.wells[well_name].dataframe["Y_UTMN"].nunique() == 1
        )

    @property
    def is_truncated(self) -> bool:
        return self._tvdmin is not None


def load_well(
    wfile: Union[str, Path],
    zonelogname: Optional[str] = None,
    mdlogname: Optional[str] = None,
) -> xtgeo.Well:
    return xtgeo.well_from_file(
        wfile=wfile, zonelogname=zonelogname, mdlogname=mdlogname
    )

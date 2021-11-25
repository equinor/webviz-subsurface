import io
import json
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict


import numpy as np
import pandas as pd
import xtgeo
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


class FMU(str, Enum):
    ENSEMBLE = "ENSEMBLE"
    REALIZATION = "REAL"


class FMUSurface(str, Enum):
    ATTRIBUTE = "attribute"
    NAME = "name"
    DATE = "date"


class SurfaceMode(str, Enum):
    REALIZATION = "Single realization"
    MINIMUM = "Minimum"
    MAXIMUM = "Maximum"
    P10 = "P10"
    P90 = "P90"
    MEAN = "Mean"
    STDDEV = "StdDev"


@dataclass
class SurfaceContext:
    ensemble: str
    realizations: List[int]
    attribute: str
    name: str
    date: Optional[str]
    mode: str


class SurfaceSetModel:
    """Class to load and calculate statistical surfaces from an FMU Ensemble"""

    def __init__(self, surface_table: pd.DataFrame):
        self._surface_table = surface_table

    @property
    def realizations(self) -> list:
        """Returns surface attributes"""
        return sorted(list(self._surface_table[FMU.REALIZATION].unique()))

    @property
    def attributes(self) -> list:
        """Returns surface attributes"""
        return sorted(list(self._surface_table[FMUSurface.ATTRIBUTE].unique()))

    def names_in_attribute(self, attribute: str) -> list:
        """Returns surface names for a given attribute"""

        return sorted(
            list(
                self._surface_table.loc[
                    self._surface_table[FMUSurface.ATTRIBUTE] == attribute
                ][FMUSurface.NAME].unique()
            )
        )

    def dates_in_attribute(self, attribute: str) -> list:
        """Returns surface dates for a given attribute"""
        dates = sorted(
            list(
                self._surface_table.loc[
                    self._surface_table[FMUSurface.ATTRIBUTE] == attribute
                ][FMUSurface.DATE].unique()
            )
        )
        if len(dates) == 1 and dates[0] is None:
            dates = None
        return dates

    def get_surface(self, surface: SurfaceContext) -> xtgeo.RegularSurface:
        surface.mode = SurfaceMode(surface.mode)
        if surface.mode == SurfaceMode.REALIZATION:
            return self.get_realization_surface(surface)
        else:
            return self.calculate_statistical_surface(surface)

    def get_realization_surface(
        self, surface_context: SurfaceContext
    ) -> xtgeo.RegularSurface:
        """Returns a Xtgeo surface instance of a single realization surface"""

        df = self._filter_surface_table(surface_context=surface_context)
        if len(df.index) == 0:
            warnings.warn(f"No surface found for {surface_context}")
            return xtgeo.RegularSurface(
                ncol=1, nrow=1, xinc=1, yinc=1
            )  # 1's as input is required
        if len(df.index) > 1:
            warnings.warn(
                f"Multiple surfaces found for: {surface_context}"
                "Returning first surface."
            )
        return xtgeo.surface_from_file(get_stored_surface_path(df.iloc[0]["path"]))

    def _filter_surface_table(self, surface_context: SurfaceContext) -> pd.DataFrame:
        """Returns a dataframe of surfaces for the provided filters"""
        columns: List[str] = [FMUSurface.NAME, FMUSurface.ATTRIBUTE]
        column_values: List[Any] = [surface_context.name, surface_context.attribute]
        if surface_context.date is not None:
            columns.append(FMUSurface.DATE)
            column_values.append(surface_context.date)
        if surface_context.realizations is not None:
            columns.append(FMU.REALIZATION)
            column_values.append(surface_context.realizations)
        df = self._surface_table.copy()
        for filt, col in zip(column_values, columns):
            if isinstance(filt, list):
                df = df.loc[df[col].isin(filt)]
            else:
                df = df.loc[df[col] == filt]
        return df

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def calculate_statistical_surface(
        self, surface_context: SurfaceContext
    ) -> xtgeo.RegularSurface:
        """Returns a Xtgeo surface instance for a calculated surface"""
        calculation = surface_context.mode

        df = self._filter_surface_table(surface_context)
        # When portable check if the surface has been stored
        # if not calculate
        try:
            surface_stream = save_statistical_surface(
                sorted(list(df["path"])), calculation
            )
        except OSError:
            surface_stream = save_statistical_surface_no_store(
                sorted(list(df["path"])), calculation
            )

        return xtgeo.surface_from_file(surface_stream, fformat="irap_binary")

    def webviz_store_statistical_calculation(
        self,
        calculation: Optional[str] = SurfaceMode.MEAN,
        realizations: Optional[List[int]] = None,
    ) -> Tuple[Callable, list]:
        """Returns a tuple of functions to calculate statistical surfaces for
        webviz store"""
        df = (
            self._surface_table.loc[self._surface_table["REAL"].isin(realizations)]
            if realizations is not None
            else self._surface_table
        )
        stored_functions_args = []
        for _attr, attr_df in df.groupby(FMUSurface.ATTRIBUTE):
            for _name, name_df in attr_df.groupby(FMUSurface.NAME):

                if name_df[FMUSurface.DATE].isnull().values.all():
                    stored_functions_args.append(
                        {
                            "fns": sorted(list(name_df["path"].unique())),
                            "calculation": calculation,
                        }
                    )
                else:
                    for _date, date_df in name_df.groupby(FMUSurface.DATE):
                        stored_functions_args.append(
                            {
                                "fns": sorted(list(date_df["path"].unique())),
                                "calculation": calculation,
                            }
                        )

        return (
            save_statistical_surface,
            stored_functions_args,
        )

    def webviz_store_realization_surfaces(self) -> Tuple[Callable, list]:
        """Returns a tuple of functions to store all realization surfaces for
        webviz store"""
        return (
            get_stored_surface_path,
            [{"runpath": path} for path in list(self._surface_table["path"])],
        )

    @property
    def first_surface_geometry(self) -> Dict:
        surface = xtgeo.surface_from_file(
            get_stored_surface_path(self._surface_table.iloc[0]["path"])
        )
        return {
            "xmin": surface.xmin,
            "xmax": surface.xmax,
            "ymin": surface.ymin,
            "ymax": surface.ymax,
            "xori": surface.xori,
            "yori": surface.yori,
            "ncol": surface.ncol,
            "nrow": surface.nrow,
            "xinc": surface.xinc,
            "yinc": surface.yinc,
        }


@webvizstore
def get_stored_surface_path(runpath: Path) -> Path:
    """Returns path of a stored surface"""
    return Path(runpath)


def save_statistical_surface_no_store(
    fns: List[str], calculation: Optional[str] = SurfaceMode.MEAN
) -> io.BytesIO:
    """Wrapper function to store a calculated surface as BytesIO"""

    surfaces = xtgeo.Surfaces([get_stored_surface_path(fn) for fn in fns])
    if len(surfaces.surfaces) == 0:
        surface = xtgeo.RegularSurface(
            ncol=1, nrow=1, xinc=1, yinc=1
        )  # 1's as input is required
    elif calculation in SurfaceMode:
        # Suppress numpy warnings when surfaces have undefined z-values
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "All-NaN slice encountered")
            warnings.filterwarnings("ignore", "Mean of empty slice")
            warnings.filterwarnings("ignore", "Degrees of freedom <= 0 for slice")
            surface = get_statistical_surface(surfaces, calculation)
    else:
        surface = xtgeo.RegularSurface(
            ncol=1, nrow=1, xinc=1, yinc=1
        )  # 1's as input is required
    stream = io.BytesIO()
    surface.to_file(stream, fformat="irap_binary")
    return stream


@webvizstore
def save_statistical_surface(fns: List[str], calculation: str) -> io.BytesIO:
    """Wrapper function to store a calculated surface as BytesIO"""
    surfaces = xtgeo.Surfaces(fns)
    if len(surfaces.surfaces) == 0:
        surface = xtgeo.RegularSurface(
            ncol=1, nrow=1, xinc=1, yinc=1
        )  # 1's as input is required
    elif calculation in SurfaceMode:
        # Suppress numpy warnings when surfaces have undefined z-values
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "All-NaN slice encountered")
            warnings.filterwarnings("ignore", "Mean of empty slice")
            warnings.filterwarnings("ignore", "Degrees of freedom <= 0 for slice")
            surface = get_statistical_surface(surfaces, calculation)
    else:
        surface = xtgeo.RegularSurface(
            ncol=1, nrow=1, xinc=1, yinc=1
        )  # 1's as input is required
    stream = io.BytesIO()
    surface.to_file(stream, fformat="irap_binary")
    return stream


# pylint: disable=too-many-return-statements
def get_statistical_surface(
    surfaces: xtgeo.Surfaces, calculation: str
) -> xtgeo.RegularSurface:
    """Calculates a statistical surface from a list of Xtgeo surface instances"""
    if calculation == SurfaceMode.MEAN:
        return surfaces.apply(np.nanmean, axis=0)
    if calculation == SurfaceMode.STDDEV:
        return surfaces.apply(np.nanstd, axis=0)
    if calculation == SurfaceMode.MINIMUM:
        return surfaces.apply(np.nanmin, axis=0)
    if calculation == SurfaceMode.MAXIMUM:
        return surfaces.apply(np.nanmax, axis=0)
    if calculation == SurfaceMode.P10:
        return surfaces.apply(np.nanpercentile, 10, axis=0)
    if calculation == SurfaceMode.P90:
        return surfaces.apply(np.nanpercentile, 90, axis=0)
    return xtgeo.RegularSurface(
        ncol=1, nrow=1, xinc=1, yinc=1
    )  # 1's as input is required

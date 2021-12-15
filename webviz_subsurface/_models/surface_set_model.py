import io
import warnings
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xtgeo
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore


class SurfaceSetModel:
    """Class to load and calculate statistical surfaces from an FMU Ensemble"""

    def __init__(self, surface_table: pd.DataFrame):
        self._surface_table = surface_table

    @property
    def realizations(self) -> list:
        """Returns surface attributes"""
        return sorted(list(self._surface_table["REAL"].unique()))

    @property
    def attributes(self) -> list:
        """Returns surface attributes"""
        return list(self._surface_table["attribute"].unique())

    def names_in_attribute(self, attribute: str) -> list:
        """Returns surface names for a given attribute"""
        return list(
            self._surface_table.loc[self._surface_table["attribute"] == attribute][
                "name"
            ].unique()
        )

    def dates_in_attribute(self, attribute: str) -> list:
        """Returns surface dates for a given attribute"""
        return list(
            self._surface_table.loc[self._surface_table["attribute"] == attribute][
                "date"
            ].unique()
        )

    def get_realization_surfaces(
        self,
        name: str,
        attribute: str,
        realizations: List[int],
        date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return [
            {
                "REAL": realization,
                "surface": self.get_realization_surface(
                    name=name,
                    attribute=attribute,
                    realization=int(realization),
                    date=date,
                ),
            }
            for realization in realizations
        ]

    def get_realization_surface(
        self, name: str, attribute: str, realization: int, date: Optional[str] = None
    ) -> xtgeo.RegularSurface:
        """Returns a Xtgeo surface instance of a single realization surface"""

        columns = ["name", "attribute", "REAL"]
        column_values = [name, attribute, realization]
        if date is not None:
            columns.append("date")
            column_values.append(date)

        df = self._filter_surface_table(
            name=name, attribute=attribute, date=date, realizations=[int(realization)]
        )
        if len(df.index) == 0:
            warnings.warn(
                f"No surface found for name: {name}, attribute: {attribute}, date: {date}, "
                f"realization: {realization}"
            )
            return xtgeo.RegularSurface(
                ncol=1, nrow=1, xinc=1, yinc=1
            )  # 1's as input is required
        if len(df.index) > 1:
            warnings.warn(
                f"Multiple surfaces found for name: {name}, attribute: {attribute}, date: {date}, "
                f"realization: {realization}. Returning first surface"
            )
        return xtgeo.surface_from_file(get_stored_surface_path(df.iloc[0]["path"]))

    def _filter_surface_table(
        self,
        name: str,
        attribute: str,
        date: Optional[str] = None,
        realizations: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Returns a dataframe of surfaces for the provided filters"""
        columns: List[str] = ["name", "attribute"]
        column_values: List[Any] = [name, attribute]
        if date is not None:
            columns.append("date")
            column_values.append(date)
        if realizations is not None:
            columns.append("REAL")
            column_values.append(realizations)
        df = self._surface_table.copy()
        for filt, col in zip(column_values, columns):
            if isinstance(filt, list):
                df = df.loc[df[col].isin(filt)]
            else:
                df = df.loc[df[col] == filt]
        return df

    @CACHE.memoize(timeout=CACHE.TIMEOUT)
    def calculate_statistical_surface(
        self,
        name: str,
        attribute: str,
        calculation: Optional[str] = "Mean",
        date: Optional[str] = None,
        realizations: Optional[List[int]] = None,
    ) -> xtgeo.RegularSurface:
        """Returns a Xtgeo surface instance for a calculated surface"""
        df = self._filter_surface_table(
            name=name, attribute=attribute, date=date, realizations=realizations
        )
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
        calculation: Optional[str] = "Mean",
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
        for _attr, attr_df in df.groupby("attribute"):
            for _name, name_df in attr_df.groupby("name"):

                if name_df["date"].isnull().values.all():
                    stored_functions_args.append(
                        {
                            "fns": sorted(list(name_df["path"].unique())),
                            "calculation": calculation,
                        }
                    )
                else:
                    for _date, date_df in name_df.groupby("date"):
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
    fns: List[str], calculation: Optional[str] = "Mean"
) -> io.BytesIO:
    """Wrapper function to store a calculated surface as BytesIO"""

    surfaces = xtgeo.Surfaces([get_stored_surface_path(fn) for fn in fns])
    if len(surfaces.surfaces) == 0:
        surface = xtgeo.RegularSurface(
            ncol=1, nrow=1, xinc=1, yinc=1
        )  # 1's as input is required
    elif calculation in ["Mean", "StdDev", "Min", "Max", "P10", "P90"]:
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
    elif calculation in ["Mean", "StdDev", "Min", "Max", "P10", "P90"]:
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
    if calculation == "Mean":
        return surfaces.apply(np.mean, axis=0)
    if calculation == "StdDev":
        return surfaces.apply(np.std, axis=0)
    if calculation == "Min":
        return surfaces.apply(np.min, axis=0)
    if calculation == "Max":
        return surfaces.apply(np.max, axis=0)
    if calculation == "P10":
        return surfaces.apply(np.percentile, 10, axis=0)
    if calculation == "P90":
        return surfaces.apply(np.percentile, 90, axis=0)
    return xtgeo.RegularSurface(
        ncol=1, nrow=1, xinc=1, yinc=1
    )  # 1's as input is required

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)
from webviz_subsurface._models.parameter_model import ParametersModel
from webviz_subsurface._utils.unique_theming import unique_colors


class RftPlotterDataModel:
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: Optional[List[str]],
        formations: Path = None,
        faultlines: Path = None,
        obsdata: Path = None,
        csvfile_rft: Path = None,
        csvfile_rft_ert: Path = None,
    ):
        self.formations = formations
        self.faultlines = faultlines
        self.obsdata = obsdata
        self.csvfile_rft = csvfile_rft
        self.csvfile_rft_ert = csvfile_rft_ert

        if csvfile_rft_ert and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_rft_ert" or "ensembles"'
            )

        self.simdf = read_csv(self.csvfile_rft) if csvfile_rft is not None else None
        self.formationdf = read_csv(self.formations) if self.formations else None
        self.faultlinesdf = read_csv(self.faultlines) if self.faultlines else None
        self.obsdatadf = read_csv(self.obsdata) if self.obsdata else None
        self.ertdatadf = pd.DataFrame()

        if csvfile_rft_ert is not None:
            self.ertdatadf = read_csv(self.csvfile_rft_ert)
            self.param_model = ParametersModel(pd.DataFrame())

        if ensembles is not None:
            ens_paths = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.emodel: EnsembleSetModel = (
                caching_ensemble_set_model_factory.get_or_create_model(
                    ensemble_paths=ens_paths,
                )
            )
            try:
                self.simdf = self.emodel.load_csv(Path("share/results/tables/rft.csv"))
            except (KeyError, OSError):
                self.simdf = None

            self.param_model = ParametersModel(
                dataframe=self.emodel.load_parameters(),
                drop_constants=True,
                keep_numeric_only=True,
            )

            try:
                self.ertdatadf = self.emodel.load_csv(
                    Path("share/results/tables/rft_ert.csv")
                )
            except KeyError as exc:
                raise KeyError(
                    "CSV file for ERT RFT observations/simulations "
                    "(share/results/tables/rft_ert.csv) not found!"
                ) from exc

        self.ertdatadf = self.ertdatadf.rename(
            columns={
                "time": "DATE",
                "is_active": "ACTIVE",
                "isactive": "ACTIVE",
                "well": "WELL",
                "zone": "ZONE",
                "pressure": "SIMULATED",
                "true_vertical_depth": "TVD",
                "measured_depth": "MD",
                "observed": "OBSERVED",
                "obs": "OBSERVED",
                "error": "OBSERVED_ERR",
                "utm_x": "EAST",
                "utm_y": "NORTH",
            }
        )
        self.ertdatadf["DIFF"] = (
            self.ertdatadf["SIMULATED"] - self.ertdatadf["OBSERVED"]
        )
        self.ertdatadf["ABSDIFF"] = abs(
            self.ertdatadf["SIMULATED"] - self.ertdatadf["OBSERVED"]
        )
        self.ertdatadf["YEAR"] = pd.to_datetime(self.ertdatadf["DATE"]).dt.year
        self.ertdatadf = self.ertdatadf.sort_values(by="DATE")
        self.ertdatadf["DATE_IDX"] = self.ertdatadf["DATE"].apply(
            lambda x: list(self.ertdatadf["DATE"].unique()).index(x)
        )
        self.date_marks = self.set_date_marks()
        self.ertdatadf = filter_frame(
            self.ertdatadf,
            {
                "ACTIVE": 1,
            },
        )
        self.ertdatadf["STDDEV"] = self.ertdatadf.groupby(
            ["WELL", "DATE", "ZONE", "ENSEMBLE", "TVD"]
        )["SIMULATED"].transform("std")

    @property
    def well_names(self) -> List[str]:
        return sorted(list(self.ertdatadf["WELL"].unique()))

    @property
    def zone_names(self) -> List[str]:
        return sorted(list(self.ertdatadf["ZONE"].unique()))

    @property
    def dates(self) -> List[str]:
        return sorted(list(self.ertdatadf["DATE"].unique()))

    def ensemble_wells(self, ensemble: str):
        df = self.ertdatadf[self.ertdatadf["ENSEMBLE"] == ensemble]
        return sorted(list(df["WELL"].unique()))

    def ensemble_parameters(self, ensemble: str):
        df = self.param_model.dataframe.copy()
        df = df[df["ENSEMBLE"] == ensemble].dropna(axis=1)
        return list(set(df.columns) & set(self.param_model.parameters))

    def date_in_well(self, well: str) -> List[str]:
        df = self.ertdatadf.loc[self.ertdatadf["WELL"] == well]
        return [str(d) for d in list(df["DATE"].unique())]

    def well_dates_and_zones(self, well: str) -> Tuple[List[str], List[str]]:
        df = self.ertdatadf.loc[self.ertdatadf["WELL"] == well]
        return [str(d) for d in list(df["DATE"].unique())], list(df["ZONE"].unique())

    @property
    def ensembles(self) -> List[str]:
        return list(self.ertdatadf["ENSEMBLE"].unique())

    @property
    def enscolors(self) -> dict:
        return unique_colors(self.ensembles)

    @property
    def parameters(self) -> List[str]:
        return self.param_model.parameters

    def set_date_marks(self) -> Dict[str, Dict[str, Any]]:
        marks = {}
        idx_steps = np.linspace(
            start=0,
            stop=self.ertdatadf["DATE_IDX"].max(),
            num=min(4, len(self.ertdatadf["DATE_IDX"].unique())),
            dtype=int,
        )
        date_steps = self.ertdatadf.loc[self.ertdatadf["DATE_IDX"].isin(idx_steps)][
            "DATE"
        ].unique()

        for i, date_index in enumerate(idx_steps):
            marks[str(date_index)] = {
                "label": f"{date_steps[i]}",
                "style": {
                    "white-space": "nowrap",
                    "font-weight": "bold",
                },
            }
        return marks

    def get_param_real_and_value_df(
        self, ensemble: str, parameter: str, normalize: bool = False
    ) -> pd.DataFrame:
        """
        Return dataframe with ralization and values for selected parameter for an ensemble.
        A column with normalized parameter values can be added.
        """
        df = self.param_model.dataframe.melt(
            id_vars=["ENSEMBLE", "REAL"], var_name="PARAMETER", value_name="VALUE"
        )
        df = df[["VALUE", "REAL"]].loc[
            (df["ENSEMBLE"] == ensemble) & (df["PARAMETER"] == parameter)
        ]
        if normalize:
            df["VALUE_NORM"] = (df["VALUE"] - df["VALUE"].min()) / (
                df["VALUE"].max() - df["VALUE"].min()
            )
        return df.reset_index(drop=True)

    @property
    def webviz_store(self) -> List[Tuple[Callable, List[Dict[str, Any]]]]:
        functions: List[Tuple[Callable, List[Dict[str, Any]]]] = [
            (
                read_csv,
                [
                    {"csv_file": path}
                    for path in [
                        self.faultlines,
                        self.formations,
                        self.obsdata,
                        self.csvfile_rft,
                        self.csvfile_rft_ert,
                    ]
                    if path is not None
                ],
            )
        ]
        if self.csvfile_rft_ert is None:
            functions.extend(self.emodel.webvizstore)
        return functions


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: str) -> pd.DataFrame:
    return pd.read_csv(csv_file)


def interpolate_depth(df: pd.DataFrame) -> pd.DataFrame:
    df = (
        df.pivot_table(index=["DEPTH"], columns=["REAL"], values="PRESSURE")
        .interpolate(limit_direction="both")
        .stack("REAL")
    )
    return df.to_frame().rename(columns={0: "PRESSURE"}).reset_index()


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_frame(
    dframe: pd.DataFrame, column_values: Dict[str, Union[List[str], str]]
) -> pd.DataFrame:
    df = dframe.copy()
    for column, value in column_values.items():
        if isinstance(value, list):
            df = df.loc[df[column].isin(value)]
        else:
            df = df.loc[df[column] == value]
    return df


def correlate(df: pd.DataFrame, response: str) -> pd.Series:
    """Returns the correlation matrix for a dataframe

    This function is the same as in ParameterAnalysis and should be generalized
    """
    df = df[df.columns[df.nunique() > 1]].copy()
    if response not in df.columns:
        df[response] = np.nan
    series = df[response]
    df = df.drop(columns=[response])
    corrdf = df.corrwith(series)
    return corrdf.reindex(corrdf.abs().sort_values().index)

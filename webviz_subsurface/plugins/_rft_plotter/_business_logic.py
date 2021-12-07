from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._datainput.fmu_input import load_csv
from webviz_subsurface._utils.unique_theming import unique_colors

from ._processing import filter_frame


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

        self.simdf = read_csv(self.csvfile_rft) if csvfile_rft is not None else None
        self.formationdf = read_csv(self.formations) if self.formations else None
        self.faultlinesdf = read_csv(self.faultlines) if self.faultlines else None
        self.obsdatadf = read_csv(self.obsdata) if self.obsdata else None
        self.ertdatadf = pd.DataFrame()

        if csvfile_rft_ert and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_rft_ert" or "ensembles"'
            )

        if csvfile_rft_ert is not None:
            self.ertdatadf = read_csv(self.csvfile_rft_ert)

        if ensembles is not None:
            self.ens_paths = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }

            try:
                self.simdf = load_csv(self.ens_paths, "share/results/tables/rft.csv")
            except (KeyError, OSError):
                self.simdf = None

            try:
                self.ertdatadf = load_csv(
                    self.ens_paths, "share/results/tables/rft_ert.csv"
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

    def date_in_well(self, well: str) -> List[str]:
        df = self.ertdatadf.loc[self.ertdatadf["WELL"] == well]
        return [str(d) for d in list(df["DATE"].unique())]

    @property
    def ensembles(self) -> List[str]:
        return list(self.ertdatadf["ENSEMBLE"].unique())

    @property
    def enscolors(self) -> dict:
        return unique_colors(self.ensembles)

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
            functions.append(
                (
                    load_csv,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "csv_file": "share/results/tables/rft_ert.csv",
                        },
                    ],
                )
            )
            try:
                load_csv(self.ens_paths, "share/results/tables/rft.csv")
                functions.append(
                    (
                        load_csv,
                        [
                            {
                                "ensemble_paths": self.ens_paths,
                                "csv_file": "share/results/tables/rft.csv",
                            },
                        ],
                    )
                )
            except KeyError:
                pass

        return functions


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: str) -> pd.DataFrame:
    return pd.read_csv(csv_file)

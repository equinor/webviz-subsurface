from typing import Any, Dict, List

import numpy as np
import pandas as pd

from webviz_subsurface._utils.unique_theming import unique_colors

from ._processing import filter_frame


class RftPlotterDataModel:
    def __init__(
        self,
        formations,
        ertdatadf,
        simdf,
        formationdf,
        faultlinesdf,
        obsdatadf,
    ):
        self.formations = formations
        self.ertdatadf = ertdatadf
        self.simdf = simdf
        self.formationdf = formationdf
        self.faultlinesdf = faultlinesdf
        self.obsdatadf = obsdatadf

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
            num=min(5, len(self.ertdatadf["DATE_IDX"].unique())),
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

from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ..._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    TraceDirection,
    get_fanchart_traces,
)
from ._processing import filter_frame, interpolate_depth


class FormationFigure:
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        well: str,
        ertdf: pd.DataFrame,
        enscolors: dict,
        depth_option: str,
        date: str,
        ensembles: List[str],
        simdf: Optional[pd.DataFrame] = None,
        obsdf: Optional[pd.DataFrame] = None,
    ) -> None:
        self.well = well
        self.simdf = (
            filter_frame(simdf, {"WELL": well, "DATE": date, "ENSEMBLE": ensembles})
            if simdf is not None
            else None
        )
        self.obsdf = (
            filter_frame(obsdf, {"WELL": well, "DATE": date})
            if obsdf is not None
            else None
        )
        self.ertdf = filter_frame(
            ertdf, {"WELL": well, "DATE": date, "ENSEMBLE": ensembles}
        )
        self.depth_option = depth_option
        self.enscolors = enscolors
        self.set_depth_columns()

        self.traces: List[Dict[str, Any]] = []
        self._layout = {
            "yaxis": {"autorange": "reversed", "title": "Depth", "showgrid": False},
            "xaxis": {
                "title": "Pressure",
                "showgrid": False,
                "range": [
                    (self.pressure_range[0] - self.xaxis_extension),
                    (self.pressure_range[1] + self.xaxis_extension),
                ],
            },
            "height": 800,
            "legend": {"orientation": "h"},
            "margin": {"t": 50},
            "hovermode": "closest",
            "uirevision": f"{well}{depth_option}",
        }

    @property
    def layout(self) -> Dict[str, Any]:
        return self._layout

    @property
    def xaxis_extension(self) -> float:
        min_x, max_x = self.pressure_range
        return (max_x - min_x) * 0.5

    @property
    def pressure_range(self) -> List[float]:
        min_sim = (
            self.ertdf["SIMULATED"].min()
            if self.use_ertdf
            else self.simdf["PRESSURE"].min()
        )
        max_sim = (
            self.ertdf["SIMULATED"].max()
            if self.use_ertdf
            else self.simdf["PRESSURE"].max()
        )
        min_obs = (self.ertdf["OBSERVED"] - self.ertdf["OBSERVED_ERR"]).min()
        max_obs = (self.ertdf["OBSERVED"] + self.ertdf["OBSERVED_ERR"]).max()

        return [
            min(
                min_sim,
                min_obs,
            ),
            max(
                max_sim,
                max_obs,
            ),
        ]

    @property
    def simdf_has_md(self) -> bool:
        if (
            self.simdf is not None
            and "CONMD" in self.simdf
            and len(self.simdf["CONMD"].unique()) == len(self.simdf["DEPTH"].unique())
        ):
            return True
        return False

    @property
    def use_ertdf(self) -> bool:
        return self.simdf is None or (
            self.depth_option == "MD" and not self.simdf_has_md
        )

    def set_depth_columns(self) -> None:
        """Set depth columns (md vs tvd)"""
        self.ertdf["DEPTH"] = self.ertdf["TVD"]

        if self.depth_option == "MD":
            self.ertdf["DEPTH"] = self.ertdf["MD"]
            if self.simdf_has_md:
                self.simdf["DEPTH"] = self.simdf["CONMD"]
            if self.obsdf is not None and "MD" in self.obsdf:
                self.obsdf["DEPTH"] = self.obsdf["MD"]

    def add_formation(self, df: pd.DataFrame) -> None:
        """Plot zonation"""
        formation_names = []
        formation_colors = [
            f"hsl({210*(1-x) + 202*x}, {100*(1-x) + 56*x}%, {98*(1-x) + 62*x}%)"
            for x in np.linspace(0, 1, len(df["ZONE"].unique()))
        ]

        top_col = "TOP_TVD" if self.depth_option == "TVD" else "TOP_MD"
        base_col = "BASE_TVD" if self.depth_option == "TVD" else "BASE_MD"

        df = filter_frame(df, {"WELL": self.well})
        df = df[df["TOP_MD"] != df["BASE_MD"]]

        for (_index, row) in df.iterrows():
            if pd.isnull(row[base_col]):
                raise KeyError(f"{base_col} has missing information")

            formation_names.append(
                {
                    "xref": "paper",
                    "yref": "y",
                    "x0": 0,
                    "x1": 1,
                    "name": row["ZONE"],
                    "y0": row[top_col],
                    "y1": row[base_col],
                    "linecolor": formation_colors[
                        list(df["ZONE"].unique()).index(row["ZONE"])
                    ],
                    "fillcolor": formation_colors[
                        list(df["ZONE"].unique()).index(row["ZONE"])
                    ],
                    "type": "rect",
                    "layer": "below",
                }
            )
            # Add formation names
            self.traces.append(
                {
                    "showlegend": _index - 1 == df.index.min(),
                    "name": "Formations",
                    "legendgroup": "name",
                    "type": "scatter",
                    "y": [abs((row[base_col] + row[top_col]) / 2)],
                    "x": [self.pressure_range[1] + (self.xaxis_extension / 1.2)],
                    "text": f"<b>{row['ZONE']}</b>",
                    "textfont": {"size": 14, "color": "#E50000"},
                    "textposition": "middle left",
                    "mode": "text",
                    "hoverinfo": "skip",
                }
            )
        self._layout.update({"shapes": formation_names})

    def add_additional_observations(self) -> None:
        if self.obsdf is not None:
            self.traces.append(
                {
                    "x": self.obsdf["PRESSURE"],
                    "y": self.obsdf["DEPTH"],
                    "type": "scatter",
                    "mode": "markers",
                    "name": "Observations",
                    "marker": {"color": "Black", "size": 20},
                }
            )

    def add_ert_observed(self) -> None:
        df = self.ertdf.copy()
        df = filter_frame(
            df,
            {
                "REAL": df["REAL"].unique()[0],
                "ENSEMBLE": df["ENSEMBLE"].unique()[0],
            },
        )
        self.traces.append(
            {
                "x": df["OBSERVED"],
                "y": df["DEPTH"],
                "type": "scatter",
                "mode": "markers",
                "name": "Ert observations",
                "marker": {
                    "color": "#2584DE",
                    "size": 20,
                },
                "error_x": {
                    "type": "data",
                    "array": df["OBSERVED_ERR"],
                    "visible": True,
                    "thickness": 6,
                },
            }
        )

    def add_simulated_lines(self, linetype: str) -> None:
        if self.use_ertdf:
            for ensemble, ensdf in self.ertdf.groupby("ENSEMBLE"):
                self.traces.append(
                    {
                        "x": ensdf["SIMULATED"],
                        "y": ensdf["DEPTH"],
                        "type": "scatter",
                        "mode": "markers",
                        "name": ensemble,
                        "marker": {
                            "color": self.enscolors[ensemble],
                            "size": 20,
                            "line": {"width": 1, "color": "grey"},
                        },
                    }
                )
        else:
            if linetype == "realization":
                for ensemble, ensdf in self.simdf.groupby("ENSEMBLE"):
                    for i, (real, realdf) in enumerate(ensdf.groupby("REAL")):
                        self.traces.append(
                            {
                                "x": realdf["PRESSURE"],
                                "y": realdf["DEPTH"],
                                "hoverinfo": "y+x+text",
                                "hovertext": f"Realization: {real}, Ensemble: {ensemble}",
                                "type": "scatter",
                                "mode": "lines",
                                "line": {"color": self.enscolors[ensemble]},
                                "name": ensemble,
                                "showlegend": i == 0,
                                "legendgroup": ensemble,
                            }
                        )
            if linetype == "fanchart":
                for ensemble, ensdf in self.simdf.groupby("ENSEMBLE"):
                    quantiles = [10, 90]
                    dframe = (
                        interpolate_depth(ensdf).drop(columns=["REAL"]).groupby("DEPTH")
                    )
                    # Build a dictionary of dataframes to be concatenated
                    dframes = {}
                    dframes["mean"] = dframe.mean()
                    for quantile in quantiles:
                        quantile_str = "p" + str(quantile)
                        dframes[quantile_str] = dframe.quantile(q=quantile / 100.0)
                    dframes["maximum"] = dframe.max()
                    dframes["minimum"] = dframe.min()
                    self.traces.extend(
                        _get_fanchart_traces(
                            pd.concat(dframes, names=["STATISTIC"], sort=False)[
                                "PRESSURE"
                            ],
                            self.enscolors[ensemble],
                            ensemble,
                        )
                    )


def _get_fanchart_traces(
    vector_stats: pd.DataFrame, color: str, legend_group: str
) -> List[Dict[str, Any]]:
    """Renders a fanchart for an ensemble vector"""

    # Retrieve indices from one of the keys
    x = vector_stats["maximum"].index.tolist()

    data = FanchartData(
        samples=x,
        low_high=LowHighData(
            low_data=vector_stats["p90"].values,
            low_name="P90",
            high_data=vector_stats["p10"].values,
            high_name="P10",
        ),
        minimum_maximum=MinMaxData(
            minimum=vector_stats["minimum"].values,
            maximum=vector_stats["maximum"].values,
        ),
        free_line=FreeLineData("Mean", vector_stats["mean"].values),
    )

    return get_fanchart_traces(
        data=data,
        color=color,
        legend_group=legend_group,
        direction=TraceDirection.VERTICAL,
    )

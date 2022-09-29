from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from ...._utils.colors import find_intermediate_color, rgba_to_str
from ...._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    TraceDirection,
    get_fanchart_traces,
)
from .._types import DepthType, LineType
from ._rft_plotter_data_model import filter_frame, interpolate_depth


class FormationFigure:
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        well: str,
        ertdf: pd.DataFrame,
        enscolors: dict,
        depthtype: DepthType,
        date: str,
        ensembles: List[str],
        simdf: Optional[pd.DataFrame] = None,
        obsdf: Optional[pd.DataFrame] = None,
        reals: Optional[Sequence] = None,
    ) -> None:
        self._well = well
        rft_filter = {"WELL": well, "DATE": date, "ENSEMBLE": ensembles}
        if reals is not None:
            rft_filter.update({"REAL": reals})

        self._simdf = filter_frame(simdf, rft_filter) if simdf is not None else None
        self._obsdf = (
            filter_frame(obsdf, {"WELL": well, "DATE": date})
            if obsdf is not None
            else None
        )
        self._ertdf = filter_frame(ertdf, rft_filter)
        self._depthtype = depthtype
        self._enscolors = enscolors
        self._set_depth_columns()

        self._traces: List[Dict[str, Any]] = []
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
            "legend": {"orientation": "h"},
            "margin": {"t": 50},
            "hovermode": "closest",
            "uirevision": f"{well}{depthtype.value}",
            "title": f"{well} at {date}",
        }

    @property
    def figure(self) -> Dict[str, Any]:
        return {"data": self._traces, "layout": self._layout}

    @property
    def xaxis_extension(self) -> float:
        min_x, max_x = self.pressure_range
        return (max_x - min_x) * 0.5

    @property
    def pressure_range(self) -> List[float]:
        min_sim = (
            self._ertdf["SIMULATED"].min()
            if self.use_ertdf
            else self._simdf["PRESSURE"].min()
        )
        max_sim = (
            self._ertdf["SIMULATED"].max()
            if self.use_ertdf
            else self._simdf["PRESSURE"].max()
        )
        min_obs = (self._ertdf["OBSERVED"] - self._ertdf["OBSERVED_ERR"]).min()
        max_obs = (self._ertdf["OBSERVED"] + self._ertdf["OBSERVED_ERR"]).max()

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
            self._simdf is not None
            and "CONMD" in self._simdf
            and len(self._simdf["CONMD"].unique()) == len(self._simdf["DEPTH"].unique())
        ):
            return True
        return False

    @property
    def use_ertdf(self) -> bool:
        return self._simdf is None or (
            self._depthtype == DepthType.MD.value and not self.simdf_has_md
        )

    @property
    def ertdf_empty(self) -> bool:
        return self._ertdf.empty

    def _set_depth_columns(self) -> None:
        """Set depth columns (md vs tvd)"""
        self._ertdf["DEPTH"] = self._ertdf["TVD"]

        if self._depthtype == DepthType.MD:
            self._ertdf["DEPTH"] = self._ertdf[DepthType.MD.value]
            if self.simdf_has_md:
                self._simdf["DEPTH"] = self._simdf["CONMD"]
            if self._obsdf is not None and DepthType.MD.value in self._obsdf:
                self._obsdf["DEPTH"] = self._obsdf[DepthType.MD.value]

    def add_formation(self, df: pd.DataFrame, fill_color: bool = True) -> None:
        """Plot zonation"""
        formation_names = []
        formation_colors = [
            f"hsl({210*(1-x) + 202*x}, {100*(1-x) + 56*x}%, {98*(1-x) + 62*x}%)"
            for x in np.linspace(0, 1, len(df["ZONE"].unique()))
        ]

        top_col = "TOP_TVD" if self._depthtype == DepthType.TVD else "TOP_MD"
        base_col = "BASE_TVD" if self._depthtype == DepthType.TVD else "BASE_MD"

        df = filter_frame(df, {"WELL": self._well})
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
                    "line": dict(color="#646567", width=1.0),
                    "fillcolor": formation_colors[
                        list(df["ZONE"].unique()).index(row["ZONE"])
                    ]
                    if fill_color
                    else None,
                    "type": "rect",
                    "layer": "below",
                }
            )
            # Add formation names
            self._traces.append(
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
        if self._obsdf is not None:
            self._traces.append(
                {
                    "x": self._obsdf["PRESSURE"],
                    "y": self._obsdf["DEPTH"],
                    "type": "scatter",
                    "mode": "markers",
                    "name": "Observations",
                    "marker": {"color": "Black", "size": 20},
                }
            )

    def add_ert_observed(self) -> None:
        df = self._ertdf
        if not df.empty:
            df = filter_frame(
                df,
                {
                    "REAL": df["REAL"].unique()[0],
                    "ENSEMBLE": df["ENSEMBLE"].unique()[0],
                },
            )
            self._traces.append(
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

    def add_simulated_lines(self, linetype: LineType) -> None:
        if self.use_ertdf:
            for ensemble, ensdf in self._ertdf.groupby("ENSEMBLE"):
                self._traces.append(
                    {
                        "x": ensdf["SIMULATED"],
                        "y": ensdf["DEPTH"],
                        "type": "scatter",
                        "mode": "markers",
                        "name": ensemble,
                        "marker": {
                            "color": self._enscolors[ensemble],
                            "size": 20,
                            "line": {"width": 1, "color": "grey"},
                        },
                    }
                )
        else:
            if linetype == LineType.REALIZATION:
                for ensemble, ensdf in self._simdf.groupby("ENSEMBLE"):
                    for i, (real, realdf) in enumerate(ensdf.groupby("REAL")):
                        self._traces.append(
                            {
                                "x": realdf["PRESSURE"],
                                "y": realdf["DEPTH"],
                                "hoverinfo": "y+x+text",
                                "hovertext": f"Realization: {real}, Ensemble: {ensemble}",
                                "type": "scatter",
                                "mode": "lines",
                                "line": {"color": self._enscolors[ensemble]},
                                "name": ensemble,
                                "showlegend": i == 0,
                                "legendgroup": ensemble,
                                "customdata": real,
                            }
                        )
            if linetype == LineType.FANCHART:
                for ensemble, ensdf in self._simdf.groupby("ENSEMBLE"):
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
                    self._traces.extend(
                        _get_fanchart_traces(
                            pd.concat(dframes, names=["STATISTIC"], sort=False)[
                                "PRESSURE"
                            ],
                            self._enscolors[ensemble],
                            ensemble,
                        )
                    )

    def color_by_param_value(self, df_norm: pd.DataFrame, selected_param: str) -> None:
        """This method colors the RFT traces according to the value of the input
        selected_param
        """
        for trace in self._traces:
            if "customdata" in trace:
                trace["line"]["color"] = set_real_color(
                    real_no=trace["customdata"], df_norm=df_norm
                )
                trace["hovertext"] = (
                    f"Real: {str(trace['customdata'])}, {selected_param}: "
                    f"{df_norm.loc[df_norm['REAL'] == trace['customdata']].iloc[0]['VALUE']}"
                )

        self._layout["title"] = {
            "text": f"{self._well} colored by {selected_param}",
        }


def set_real_color(df_norm: pd.DataFrame, real_no: str) -> str:
    """
    Return color for trace based on normalized parameter value.
    Midpoint for the colorscale is set on the average value
    Same function as in Parameter Analysis. Shout be generalized
    """
    red = rgba_to_str((255, 18, 67, 1))
    mid_color = rgba_to_str((220, 220, 220, 1))
    green = rgba_to_str((62, 208, 62, 1))

    mean = df_norm["VALUE_NORM"].mean()

    norm_value = df_norm.loc[df_norm["REAL"] == real_no].iloc[0]["VALUE_NORM"]
    if norm_value <= mean:
        intermed = norm_value / mean
        return find_intermediate_color(red, mid_color, intermed)

    intermed = (norm_value - mean) / (1 - mean)
    return find_intermediate_color(mid_color, green, intermed)


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
        hex_color=color,
        legend_group=legend_group,
        direction=TraceDirection.VERTICAL,
    )

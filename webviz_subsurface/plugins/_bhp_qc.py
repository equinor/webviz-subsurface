from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE

from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)

from .._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    get_fanchart_traces,
)
from .._utils.unique_theming import unique_colors


class BhpQc(WebvizPluginABC):
    """QC simulated bottom hole pressures (BHP) from reservoir simulations.

    Can be used to check if your simulated BHPs are in a realistic range.
    E.g. check if your simulated bottom hole pressures are very low in producers,
    or very high injectors.
    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    ---
    Data is read directly from the UNSMRY files with the raw frequency (not resampled).
    Resampling and csvs are not supported to avoid potential of interpolation, which
    might cover extreme BHP values.

    !> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
    individual realizations. You should therefore not have more than one `UNSMRY` file in this \
    folder, to avoid risk of not extracting the right data.
    """

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        wells: Optional[List[str]] = None,
    ):
        super().__init__()
        if wells is None:
            self.column_keys = ["WBHP:*"]
        else:
            self.column_keys = [f"WBHP:{well}" for well in wells]

        self.emodel: EnsembleSetModel = (
            caching_ensemble_set_model_factory.get_or_create_model(
                ensemble_paths={
                    ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                    for ens in ensembles
                },
                time_index="raw",
                column_keys=self.column_keys,
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.theme = webviz_settings.theme
        self.set_callbacks(app)

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard for BHP QC:"
                    "Check that simulated bottom hole pressures are realistic."
                ),
            },
            {"id": self.uuid("ensemble"), "content": "Select ensemble to QC."},
            {
                "id": self.uuid("sort_by"),
                "content": "Sort wells left to right according to this value.",
            },
            {
                "id": self.uuid("n_wells"),
                "content": (
                    "Show max selected number of top ranked wells after sorting and filtering."
                ),
            },
            {"id": self.uuid("wells"), "content": "Filter wells."},
        ]

    @property
    def ensembles(self) -> List[str]:
        return list(self.smry["ENSEMBLE"].unique())

    @property
    def wells(self) -> List[set]:
        return sorted(
            list(set(col[5:] for col in self.smry.columns if col.startswith("WBHP:")))
        )

    @property
    def ens_colors(self) -> dict:
        return unique_colors(self.ensembles, self.theme)

    @property
    def label_map(self) -> Dict[str, str]:
        return {
            "Mean": "mean",
            "Count (data points)": "count",
            "Stddev": "std",
            "Minimum": "min",
            "Maximum": "max",
            "P10 (high)": "high_p10",
            "P50": "p50",
            "P90 (low)": "low_p90",
        }

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "45vh"},
                    children=[
                        wcc.Dropdown(
                            label="Ensemble",
                            id=self.uuid("ensemble"),
                            options=[{"label": i, "value": i} for i in self.ensembles],
                            value=self.ensembles[0],
                            clearable=False,
                            multi=False,
                        ),
                        wcc.Dropdown(
                            label="Plot type",
                            id=self.uuid("plot_type"),
                            options=[
                                {"label": i, "value": i}
                                for i in [
                                    "Fan chart",
                                    "Bar chart",
                                    "Line chart",
                                ]
                            ],
                            clearable=False,
                            value="Fan chart",
                        ),
                        html.Div(
                            id=self.uuid("select_stat"),
                            style={"display": "none"},
                            children=[
                                wcc.SelectWithLabel(
                                    label="Select statistics",
                                    id=self.uuid("stat_bars"),
                                    options=[
                                        {"label": key, "value": value}
                                        for key, value in self.label_map.items()
                                    ],
                                    size=8,
                                    value=["count", "low_p90", "p50"],
                                ),
                            ],
                        ),
                        wcc.Dropdown(
                            label="Sort by",
                            id=self.uuid("sort_by"),
                            options=[
                                {"label": key, "value": value}
                                for key, value in self.label_map.items()
                            ],
                            clearable=False,
                            value="low_p90",
                        ),
                        wcc.RadioItems(
                            vertical=False,
                            id=self.uuid("ascending"),
                            options=[
                                {"label": "Ascending", "value": True},
                                {"label": "Descending", "value": False},
                            ],
                            value=True,
                            labelStyle={"display": "inline-block"},
                        ),
                        wcc.Slider(
                            label="Max number of wells in plot",
                            id=self.uuid("n_wells"),
                            min=1,
                            max=len(self.wells),
                            step=1,
                            value=min(10, len(self.wells)),
                            marks={1: 1, len(self.wells): len(self.wells)},
                        ),
                        wcc.SelectWithLabel(
                            label="Wells",
                            id=self.uuid("wells"),
                            options=[{"label": i, "value": i} for i in self.wells],
                            size=min([len(self.wells), 20]),
                            value=self.wells,
                        ),
                    ],
                ),
                wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"flex": 6, "height": "45vh"},
                    children=[
                        wcc.Graph(id=self.uuid("graph")),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.uuid("graph"), "figure"),
            Input(self.uuid("ensemble"), "value"),
            Input(self.uuid("plot_type"), "value"),
            Input(self.uuid("n_wells"), "value"),
            Input(self.uuid("wells"), "value"),
            Input(self.uuid("sort_by"), "value"),
            Input(self.uuid("stat_bars"), "value"),
            Input(self.uuid("ascending"), "value"),
        )
        def _update_graph(
            ensemble: str,
            plot_type: str,
            n_wells: int,
            wells: Union[str, List[str]],
            sort_by: str,
            stat_bars: Union[str, List[str]],
            ascending: bool,
        ) -> dict:
            wells = wells if isinstance(wells, list) else [wells]
            stat_bars = stat_bars if isinstance(stat_bars, list) else [stat_bars]
            df = filter_df(df=self.smry, ensemble=ensemble, wells=wells)
            stat_df = (
                calc_statistics(df)
                .sort_values(sort_by, ascending=ascending)
                .iloc[0:n_wells, :]
            )
            traces = []
            if plot_type == "Fan chart":
                traces.extend(
                    _get_fanchart_traces(
                        ens_stat_df=stat_df,
                        color=self.ens_colors[ensemble],
                        legend_group=ensemble,
                    )
                )
            elif plot_type in ["Bar chart", "Line chart"]:
                for stat in stat_bars:
                    yaxis = "y2" if stat == "count" else "y"

                    if plot_type == "Bar chart":

                        traces.append(
                            {
                                "x": [vec[5:] for vec in stat_df.index],  # strip WBHP:
                                "y": stat_df[stat],
                                "name": [
                                    key
                                    for key, value in self.label_map.items()
                                    if value == stat
                                ][0],
                                "yaxis": yaxis,
                                "type": "bar",
                                "offsetgroup": stat,
                                "showlegend": True,
                            }
                        )
                    elif plot_type == "Line chart":
                        traces.append(
                            {
                                "x": [vec[5:] for vec in stat_df.index],  # strip WBHP:
                                "y": stat_df[stat],
                                "name": [
                                    key
                                    for key, value in self.label_map.items()
                                    if value == stat
                                ][0],
                                "yaxis": yaxis,
                                "type": "line",
                                "offsetgroup": stat,
                                "showlegend": True,
                            }
                        )
                    else:
                        raise ValueError("Invalid plot type.")

            layout = self.theme.create_themed_layout(
                {
                    "yaxis": {
                        "side": "left",
                        "title": "Bottom hole pressure",
                        "showgrid": False,
                    },
                    "yaxis2": {
                        "side": "right",
                        "overlaying": "y",
                        "title": "Count (data points)",
                        "showgrid": False,
                    },
                    "xaxis": {"showgrid": False},
                    "barmode": "group",
                    "legend": {"x": 1.05},
                }
            )
            return {"data": traces, "layout": layout}

        @app.callback(
            Output(self.uuid("select_stat"), "style"),
            Input(self.uuid("plot_type"), "value"),
        )
        def _update_stat_selector(plot_type: str) -> dict:
            return (
                {"display": "none"}
                if plot_type == "Fan chart"
                else {"display": "block"}
            )

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return self.emodel.webvizstore


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_df(df: pd.DataFrame, ensemble: str, wells: List[str]) -> pd.DataFrame:
    """Filter dataframe for current ensembles and wells.
    Replacing zeroes (well not open) with np.NaN to not be accounted for
    in statistics.
    """
    columns = ["ENSEMBLE"] + [f"WBHP:{well}" for well in wells]
    return df.loc[df["ENSEMBLE"] == ensemble][columns].replace(0, np.NaN)


def calc_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate statistics for given vectors over the ensembles
    refaxis is used if another column than DATE should be used to groupby.
    """
    # Invert p10 and p90 due to oil industry convention.
    def p10(x: np.ndarray) -> float:
        return np.nanpercentile(x, q=90)

    def p50(x: np.ndarray) -> float:
        return np.nanpercentile(x, q=50)

    def p90(x: np.ndarray) -> float:
        return np.nanpercentile(x, q=10)

    # Calculate statistics, ignoring NaNs.
    stat_df = (
        df.groupby("ENSEMBLE")
        .agg([np.nanmean, "count", np.nanstd, np.nanmin, np.nanmax, p10, p50, p90])
        .reset_index(drop=True, level="ENSEMBLE")
    )
    # Rename nanmin, nanmax and nanmean to min, max and mean.
    col_stat_label_map = {
        "nanmin": "min",
        "nanmax": "max",
        "nanmean": "mean",
        "nanstd": "std",
        "p10": "high_p10",
        "p90": "low_p90",
    }
    stat_df.rename(columns=col_stat_label_map, level=1, inplace=True)
    stat_df = stat_df.transpose().unstack()
    stat_df.columns = stat_df.columns.get_level_values(1)  # Remove 0 index column
    return stat_df


def _get_fanchart_traces(
    ens_stat_df: pd.DataFrame,
    color: str,
    legend_group: str,
) -> List[dict]:
    """Renders a fanchart for an ensemble vector"""

    x = [vec[5:] for vec in ens_stat_df.index]

    data = FanchartData(
        samples=x,
        low_high=LowHighData(
            low_data=ens_stat_df["low_p90"].values,
            low_name="P90 (low)",
            high_data=ens_stat_df["high_p10"].values,
            high_name="P10 (high)",
        ),
        minimum_maximum=MinMaxData(
            minimum=ens_stat_df["min"].values,
            maximum=ens_stat_df["max"].values,
        ),
        free_line=FreeLineData("Mean", ens_stat_df["mean"].values),
    )

    return get_fanchart_traces(
        data=data,
        hex_color=color,
        legend_group=legend_group,
        hovermode="x",
    )

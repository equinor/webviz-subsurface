from typing import List, Optional

import pandas as pd
import numpy as np
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC

from .._datainput.fmu_input import load_smry
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
        app,
        ensembles: list,
        wells: Optional[List[str]] = None,
    ):
        super().__init__()
        self.ens_paths = {
            ensemble: app.webviz_settings["shared_settings"]["scratch_ensembles"][
                ensemble
            ]
            for ensemble in ensembles
        }
        if wells is None:
            self.column_keys = ["WBHP:*"]
        else:
            self.column_keys = [f"WBHP:{well}" for well in wells]

        self.smry = load_smry(
            ensemble_paths=self.ens_paths,
            time_index="raw",
            column_keys=self.column_keys,
        )
        self.theme = app.webviz_settings["theme"]
        self.set_callbacks(app)

    @property
    def tour_steps(self):
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
    def ensembles(self):
        return list(self.smry["ENSEMBLE"].unique())

    @property
    def wells(self):
        return sorted(
            list(set(col[5:] for col in self.smry.columns if col.startswith("WBHP:")))
        )

    @property
    def ens_colors(self):
        return unique_colors(self.ensembles, self.theme)

    @property
    def label_map(self):
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
    def layout(self):
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(
                    style={"flex": 1},
                    children=[
                        html.Label(
                            children=[
                                html.Span(
                                    "Ensemble:",
                                    style={"font-weight": "bold"},
                                ),
                                dcc.Dropdown(
                                    id=self.uuid("ensemble"),
                                    options=[
                                        {"label": i, "value": i} for i in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                    multi=False,
                                ),
                            ],
                        ),
                        html.Label(
                            children=[
                                html.Span("Plot type:", style={"font-weight": "bold"}),
                                dcc.Dropdown(
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
                            ],
                        ),
                        html.Label(
                            id=self.uuid("select_stat"),
                            style={"display": "none"},
                            children=[
                                html.Span(
                                    "Select statistics:", style={"font-weight": "bold"}
                                ),
                                wcc.Select(
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
                        html.Label(
                            children=[
                                html.Span("Sort by:", style={"font-weight": "bold"}),
                                dcc.Dropdown(
                                    id=self.uuid("sort_by"),
                                    options=[
                                        {"label": key, "value": value}
                                        for key, value in self.label_map.items()
                                    ],
                                    clearable=False,
                                    value="low_p90",
                                ),
                            ],
                        ),
                        dcc.RadioItems(
                            id=self.uuid("ascending"),
                            options=[
                                {"label": "Ascending", "value": True},
                                {"label": "Descending", "value": False},
                            ],
                            value=True,
                            labelStyle={"display": "inline-block"},
                        ),
                        html.Label(
                            children=[
                                html.Span(
                                    "Max number of wells in plot:",
                                    style={"font-weight": "bold"},
                                ),
                                dcc.Slider(
                                    id=self.uuid("n_wells"),
                                    min=1,
                                    max=len(self.wells),
                                    value=min(10, len(self.wells)),
                                    marks={1: 1, len(self.wells): len(self.wells)},
                                ),
                            ]
                        ),
                        html.Label(
                            children=[
                                html.Span("Wells:", style={"font-weight": "bold"}),
                                wcc.Select(
                                    id=self.uuid("wells"),
                                    options=[
                                        {"label": i, "value": i} for i in self.wells
                                    ],
                                    size=min([len(self.wells), 20]),
                                    value=self.wells,
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    style={"flex": 3},
                    children=[
                        html.Div(
                            # style={"height": "300px"},
                            children=wcc.Graph(id=self.uuid("graph")),
                        ),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app):
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
            ensemble, plot_type, n_wells, wells, sort_by, stat_bars, ascending
        ):
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
                    add_fanchart_traces(
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
        def _update_stat_selector(plot_type):
            return (
                {"display": "none"}
                if plot_type == "Fan chart"
                else {"display": "block"}
            )

    def add_webvizstore(self):
        return [
            (
                load_smry,
                [
                    {
                        "ensemble_paths": self.ens_paths,
                        "column_keys": self.column_keys,
                        "time_index": "raw",
                    }
                ],
            ),
        ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_df(df, ensemble, wells):
    """Filter dataframe for current ensembles and wells.
    Replacing zeroes (well not open) with np.NaN to not be accounted for
    in statistics.
    """
    columns = ["ENSEMBLE"] + [f"WBHP:{well}" for well in wells]
    return df.loc[df["ENSEMBLE"] == ensemble][columns].replace(0, np.NaN)


def calc_statistics(df: pd.DataFrame):
    """Calculate statistics for given vectors over the ensembles
    refaxis is used if another column than DATE should be used to groupby.
    """
    # Invert p10 and p90 due to oil industry convention.
    def p10(x):
        return np.nanpercentile(x, q=90)

    def p50(x):
        return np.nanpercentile(x, q=50)

    def p90(x):
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


def add_fanchart_traces(
    ens_stat_df: pd.DataFrame,
    color: str,
    legend_group: str,
):
    """Renders a fanchart for an ensemble vector"""

    fill_color = hex_to_rgb(color, 0.3)
    line_color = hex_to_rgb(color, 1)
    x = [vec[5:] for vec in ens_stat_df.index]

    return [
        {
            "name": legend_group,
            "hovertext": "Maximum",
            "x": x,
            "y": ens_stat_df["max"],
            "mode": "lines",
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P90 (low)",
            "x": x,
            "y": ens_stat_df["low_p90"],
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "P10 (high)",
            "x": x,
            "y": ens_stat_df["high_p10"],
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
        {
            "name": legend_group,
            "hovertext": "Mean",
            "x": x,
            "y": ens_stat_df["mean"],
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"color": line_color},
            "legendgroup": legend_group,
            "showlegend": True,
        },
        {
            "name": legend_group,
            "hovertext": "Minimum",
            "x": x,
            "y": ens_stat_df["min"],
            "mode": "lines",
            "fill": "tonexty",
            "fillcolor": fill_color,
            "line": {"width": 0, "color": line_color},
            "legendgroup": legend_group,
            "showlegend": False,
        },
    ]


def hex_to_rgb(hex_string, opacity=1):
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"

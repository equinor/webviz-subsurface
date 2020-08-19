########################################
#
#  Copyright (C) 2020-     Equinor ASA
#
########################################

from typing import Callable, Dict, List, Tuple, Union

import pandas as pd
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config import WebvizPluginABC

from .._datainput.pvt_data import load_pvt_dataframe
from .._datainput.fmu_input import load_csv


class PvtPlot(WebvizPluginABC):
    """Visualizes formation volume factor and viscosity data \
for oil, gas and water from both Eclipse **init** and **include** files.

---

* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`pvt_relative_file_path`:** Local path to a csv file in each \
    realization with dumped pvt data.
* **`read_from_init_file`:** A boolean flag stating if data shall be \
    read from an Eclipse INIT file instead of an INCLUDE file. \
    This is only used when **pvt_relative_file_path** is not given.

---
The minimum requirement is to define `ensembles`.

If no `pvt_relative_file_path` is given, the PVT data will be extracted automatically
from the simulation decks of individual realizations using `fmu_ensemble` and `ecl2data_frame`.
If the `read_from_init_file` flag is set to True, then the extraction procedure in
`ecl2data_frame` will be replaced by an individual extracting procedure that reads the
normalized Eclipse INIT file.
Note that the latter two extraction methods can be very slow for larger data and are therefore
not recommended unless you have a very simple model/data deck.

`pvt_relative_file_path` is a path to a file stored per realization (e.g. in \
`share/results/tables/pvt.csv`). `pvt_relative_file_path` columns:
* One column named `KEYWORD` or `TYPE`: with Flow/Eclipse style keywords
    (e.g. `PVTO` and `PVDG`).
* One column named `PVTNUM` with integer `PVTNUM` regions.
* One column named `GOR` or `RS` with the gas-oil-ratio as the primary variate.
* One column named `PRESSURE` with the fluids pressure as the secondary variate.
* One column named `VOLUMEFACTOR` as the first covariate.
* One column named `VISCOSITY` as the second covariate.

The file can e.g. be dumped to disc per realization by a forward model in ERT using
`ecl2data_frame` or `pyscal`.
"""

    PHASES = {"OIL": "PVTO", "GAS": "PVDG", "WATER": "PVTW"}

    def __init__(
        self,
        app,
        ensembles: List[str],
        pvt_relative_file_path: str = None,
        read_from_init_file: bool = False,
    ):

        super().__init__()

        self.ensemble_paths = {
            ensemble: app.webviz_settings["shared_settings"]["scratch_ensembles"][
                ensemble
            ]
            for ensemble in ensembles
        }

        self.plotly_theme = app.webviz_settings["theme"].plotly_theme

        self.pvt_relative_file_path = pvt_relative_file_path

        self.read_from_init_file = read_from_init_file

        if self.pvt_relative_file_path is None:
            self.pvt_data_frame = load_pvt_dataframe(
                self.ensemble_paths, use_init_file=read_from_init_file
            )
            self.pvt_data_frame = self.pvt_data_frame.rename(
                str.upper, axis="columns"
            ).rename(columns={"TYPE": "KEYWORD", "RS": "GOR"})
        else:
            # Load data from all ensembles into a pandas DataFrame
            self.pvt_data_frame = load_csv(
                ensemble_paths=self.ensemble_paths, csv_file=self.pvt_relative_file_path
            )

            # Rename "type" header column to "keyword" and make all headers having capital letters
            self.pvt_data_frame = self.pvt_data_frame.rename(
                str.upper, axis="columns"
            ).rename(columns={"TYPE": "KEYWORD", "RS": "GOR"})

            # Ensure that the identifier string "KEYWORD" is contained in the header columns
            if "KEYWORD" not in self.pvt_data_frame.columns:
                raise ValueError(
                    "There has to be a KEYWORD or TYPE column with corresponding Eclipse keyword."
                )

        columns = [
            "ENSEMBLE",
            "REAL",
            "PVTNUM",
            "KEYWORD",
            "GOR",
            "PRESSURE",
            "VOLUMEFACTOR",
            "VISCOSITY",
        ]
        self.pvt_data_frame = self.pvt_data_frame[columns]

        stored_data_frames = []
        cleaned_data_frame = self.pvt_data_frame.iloc[0:0]
        columns_subset = self.pvt_data_frame.columns.difference(["REAL", "ENSEMBLE"])

        for iter_data_frame in self.pvt_data_frame.groupby("ENSEMBLE").items():
            iter_merged_dataframe = self.pvt_data_frame.iloc[0:0]
            for realization_data_frame in iter_data_frame.groupby("REAL").items():
                if iter_merged_dataframe.empty:
                    iter_merged_dataframe = iter_merged_dataframe.append(
                        realization_data_frame
                    ).reset_index(drop=True)
                else:
                    iter_merged_dataframe = (
                        pd.concat([iter_merged_dataframe, realization_data_frame])
                        .drop_duplicates(subset=columns_subset, keep="first",)
                        .reset_index(drop=True)
                    )
            data_frame_stored = False
            for data_frame in stored_data_frames:
                if all(
                    data_frame[columns_subset] == iter_merged_dataframe[columns_subset]
                ):
                    data_frame_stored = True
                    break
            if data_frame_stored:
                continue
            stored_data_frames.append(iter_merged_dataframe)
            cleaned_data_frame = cleaned_data_frame.append(iter_merged_dataframe)

        self.pvt_data_frame = cleaned_data_frame

        self.set_callbacks(app)

    @property
    def phases(self) -> List[str]:
        return list(PvtPlot.PHASES.keys())

    @property
    def ensembles(self) -> List[str]:
        return list(self.pvt_data_frame["ENSEMBLE"].unique())

    @property
    def pvtnums(self) -> List[str]:
        return list(self.pvt_data_frame["PVTNUM"].unique())

    @property
    def ensemble_colors(self) -> Dict[str, List[str]]:
        return {
            ensemble: self.plotly_theme["layout"]["colorway"][
                self.ensembles.index(ensemble)
            ]
            for ensemble in self.ensembles
        }

    @property
    def pvtnum_colors(self) -> Dict[str, List[str]]:
        return {
            pvtnum: self.plotly_theme["layout"]["colorway"][self.pvtnums.index(pvtnum)]
            for pvtnum in self.pvtnums
        }

    @property
    def color_options(self) -> List[str]:
        """Options to color by"""
        return ["ENSEMBLE", "PVTNUM"]

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("layout"),
                "content": "Dashboard displaying formation volume factor and viscosity"
                " data of either Oil, Gas or Water",
            },
            {
                "id": self.uuid("graph"),
                "content": (
                    "Visualization of curves. "
                    "Different options can be set in the menu to the left."
                    "You can also toggle data on/off by clicking at the legend."
                ),
            },
            {
                "id": self.uuid("color_by_selector"),
                "content": ("Choose the basis for your colormap."),
            },
            {"id": self.uuid("ensemble_selector"), "content": ("Select ensembles."),},
            {
                "id": self.uuid("phase_selector"),
                "content": (
                    "Choose a phase. formation volume factor and viscosity data will be"
                    " shown for the selected phase in separate plots."
                ),
            },
            {
                "id": self.uuid("pvtnum_selector"),
                "content": ("Choose PVTNUM regions."),
            },
        ]

    @staticmethod
    def set_grid_layout(columns: int, padding: int = 0) -> Dict[str, str]:
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
            "padding": f"{padding}px",
        }

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(
                    id=self.uuid("filters"),
                    style={"flex": "1"},
                    children=[
                        html.Label(
                            id=self.uuid("color_by_selector"),
                            children=[
                                html.Span("Color by:", style={"font-weight": "bold"}),
                                dcc.Dropdown(
                                    id=self.uuid("color_by"),
                                    clearable=False,
                                    options=[
                                        {"label": i.lower().capitalize(), "value": i,}
                                        for i in self.color_options
                                    ],
                                    value=self.color_options[0],
                                ),
                            ],
                        ),
                        html.Label(
                            id=self.uuid("ensemble_selector"),
                            children=[
                                dcc.Store(id=self.uuid("stored_ensemble"), data={}),
                                html.Span("Ensembles:", style={"font-weight": "bold"}),
                                dcc.Dropdown(
                                    id=self.uuid("ensemble"),
                                    clearable=False,
                                    multi=True,
                                    options=[
                                        {"label": i, "value": i} for i in self.ensembles
                                    ],
                                    value=self.ensembles[0],
                                ),
                            ],
                        ),
                        html.Label(
                            id=self.uuid("phase_selector"),
                            children=[
                                html.Span("Phase:", style={"font-weight": "bold"},),
                                dcc.Dropdown(
                                    id=self.uuid("phase"),
                                    clearable=False,
                                    options=[
                                        {"label": i.lower().capitalize(), "value": i,}
                                        for i in self.phases
                                    ],
                                    value=list(self.phases)[0],
                                ),
                            ],
                        ),
                        dcc.Store(id=self.uuid("stored_pvtnum"), data={}),
                        html.Label(
                            id=self.uuid("pvtnum_selector"),
                            children=[
                                html.Span("Pvtnum:", style={"font-weight": "bold"}),
                                dcc.Dropdown(
                                    id=self.uuid("pvtnum"),
                                    clearable=False,
                                    multi=True,
                                    options=[
                                        {"label": i, "value": i} for i in self.pvtnums
                                    ],
                                    value=self.pvtnums[0],
                                ),
                            ],
                        ),
                    ],
                ),
                html.Div(
                    id=self.uuid("graphs"),
                    style={"flex": "4"},
                    children=wcc.Graph(id=self.uuid("graph")),
                ),
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("graph"), "figure"),
            [
                Input(self.uuid("color_by"), "value"),
                Input(self.uuid("phase"), "value"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("pvtnum"), "value"),
            ],
        )
        def _update_graph(
            color_by: str,
            phase: str,
            ensembles: Union[List[str], str],
            pvtnums: Union[List[str], str],
        ) -> Dict[str, Union[dict, List[dict]]]:
            if not phase:
                raise PreventUpdate
            if ensembles is None:
                ensembles = []
            if not isinstance(ensembles, list):
                ensembles = [ensembles]
            if not isinstance(pvtnums, list):
                pvtnums = [pvtnums]

            data_frame = filter_data_frame(self.pvt_data_frame, ensembles, pvtnums)

            if color_by == "ENSEMBLE":
                colors = self.ensemble_colors
            elif color_by == "PVTNUM":
                colors = self.pvtnum_colors

            layout = plot_layout(phase, color_by, self.plotly_theme["layout"])

            traces = add_realization_traces(data_frame, color_by, colors, phase)

            return {"data": traces, "layout": layout}

        @app.callback(
            [
                Output(self.uuid("ensemble"), "multi"),
                Output(self.uuid("ensemble"), "value"),
            ],
            [Input(self.uuid("color_by"), "value")],
            [State(self.uuid("stored_ensemble"), "data")],
        )
        def _set_ensemble_selector(
            color_by: str, stored_ensemble: pd.DataFrame
        ) -> Tuple[bool, str]:
            """If ensemble is selected as color by, set the ensemble
            selector to allow multiple selections, else use stored_ensemble
            """

            if color_by == "ENSEMBLE":
                return True, self.ensembles

            return (
                False,
                stored_ensemble.get("ENSEMBLE", self.ensembles[0]),
            )

        @app.callback(
            [
                Output(self.uuid("pvtnum"), "multi"),
                Output(self.uuid("pvtnum"), "value"),
            ],
            [Input(self.uuid("color_by"), "value")],
            [State(self.uuid("stored_pvtnum"), "data")],
        )
        def _set_pvtnum_selector(
            color_by: str, stored_pvtnum: pd.DataFrame
        ) -> Tuple[bool, str]:
            """If pvtnum is selected as color by, set the pvtnum
            selector to allow multiple selections, else use stored_satnum
            """

            if color_by == "PVTNUM":
                return True, self.pvtnums

            return (
                False,
                stored_pvtnum.get("PVTNUM", self.pvtnums[0]),
            )

    def add_webvizstore(self,) -> List[Tuple[Callable, List[Dict[str, any]]]]:
        return (
            [
                (
                    load_pvt_dataframe,
                    [
                        {
                            "ensemble_paths": self.ensemble_paths,
                            "use_init_file": self.read_from_init_file,
                        }
                    ],
                )
            ]
            if self.pvt_relative_file_path is None
            else [
                (
                    load_csv,
                    [
                        {
                            "ensemble_paths": self.ensemble_paths,
                            "csv_file": self.pvt_relative_file_path,
                        }
                    ],
                )
            ]
        )


# Caching should be safe here with DataFrame as it is always the same for an instance of the plugin.
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_data_frame(
    data_frame: pd.DataFrame, ensembles: List[str], pvtnums: List[str]
) -> pd.DataFrame:

    data_frame = data_frame.copy()
    data_frame = data_frame.loc[data_frame["ENSEMBLE"].isin(ensembles)]
    data_frame = data_frame.loc[data_frame["PVTNUM"].isin(pvtnums)]
    return data_frame.fillna(0)


def add_realization_traces(
    data_frame: pd.DataFrame, color_by: str, colors: List[str], phase: str
) -> List[dict]:
    """Renders line traces for individual realizations"""
    # pylint: disable-msg=too-many-locals

    traces = []

    data_frame = data_frame.loc[data_frame["KEYWORD"] == PvtPlot.PHASES[phase]]
    column_name = "GOR"

    border_value_pressure = {}
    border_value_viscosity = {}
    border_value_volumefactor = {}

    for ratio_no, oil_gas_ratio in enumerate(data_frame[column_name].unique()):
        constant_group = (
            data_frame["PVTNUM"].iloc[0]
            if color_by == "ENSEMBLE"
            else data_frame["ENSEMBLE"].iloc[0]
        )

        for (group, grouped_data_frame) in data_frame.groupby(color_by):
            for realization_no, (realization, realization_data_frame) in enumerate(
                grouped_data_frame.groupby("REAL")
            ):

                if group not in border_value_pressure:
                    border_value_pressure[group] = []
                    border_value_viscosity[group] = []
                    border_value_volumefactor[group] = []

                border_value_pressure[group].append(
                    realization_data_frame.loc[
                        realization_data_frame[column_name] == oil_gas_ratio
                    ]["PRESSURE"].iloc[0]
                )
                border_value_volumefactor[group].append(
                    realization_data_frame.loc[
                        realization_data_frame[column_name] == oil_gas_ratio
                    ]["VOLUMEFACTOR"].iloc[0]
                )
                border_value_viscosity[group].append(
                    realization_data_frame.loc[
                        realization_data_frame[column_name] == oil_gas_ratio
                    ]["VISCOSITY"].iloc[0]
                )

                traces.extend(
                    [
                        {
                            "type": "scatter",
                            "x": realization_data_frame.loc[
                                realization_data_frame[column_name] == oil_gas_ratio
                            ]["PRESSURE"],
                            "y": realization_data_frame.loc[
                                realization_data_frame[column_name] == oil_gas_ratio
                            ]["VOLUMEFACTOR"],
                            "xaxis": "x",
                            "yaxis": "y",
                            "hovertext": (
                                f"{'Rs' if phase == 'OIL' else 'Rv'} = {oil_gas_ratio}"
                                ", Pvtnum: "
                                f"{group if color_by == 'PVTNUM' else constant_group}<br>"
                                f"Realization: {realization}, Ensemble: "
                                f"{group if color_by == 'ENSEMBLE' else constant_group}"
                            ),
                            "name": group,
                            "legendgroup": group,
                            "marker": {
                                "color": colors.get(
                                    group, colors[list(colors.keys())[-1]]
                                )
                            },
                            "showlegend": realization_no == 0 and ratio_no == 0,
                        }
                    ]
                )
                traces.extend(
                    [
                        {
                            "type": "scatter",
                            "x": realization_data_frame.loc[
                                realization_data_frame[column_name] == oil_gas_ratio
                            ]["PRESSURE"],
                            "y": realization_data_frame.loc[
                                realization_data_frame[column_name] == oil_gas_ratio
                            ]["VISCOSITY"],
                            "xaxis": "x2",
                            "yaxis": "y2",
                            "hovertext": (
                                f"{'Rs' if phase == 'OIL' else 'Rv'} = {oil_gas_ratio}"
                                ", Pvtnum: "
                                f"{group if color_by == 'PVTNUM' else constant_group}<br>"
                                f"Realization: {realization}, Ensemble: "
                                f"{group if color_by == 'ENSEMBLE' else constant_group}"
                            ),
                            "name": group,
                            "legendgroup": group,
                            "marker": {
                                "color": colors.get(
                                    group, colors[list(colors.keys())[-1]]
                                )
                            },
                            "showlegend": False,
                        }
                    ]
                )

    for group in border_value_pressure:
        traces.extend(
            [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": border_value_pressure[group],
                    "y": border_value_volumefactor[group],
                    "xaxis": "x",
                    "yaxis": "y",
                    "line": {"width": 1, "color": "black",},
                    "showlegend": False,
                }
            ]
        )
        traces.extend(
            [
                {
                    "type": "scatter",
                    "mode": "lines",
                    "x": border_value_pressure[group],
                    "y": border_value_viscosity[group],
                    "xaxis": "x2",
                    "yaxis": "y2",
                    "line": {"width": 1, "color": "black",},
                    "showlegend": False,
                }
            ]
        )
    return traces


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_layout(phase: str, color_by: str, theme: dict) -> dict:
    """
    Constructing plot layout from scratch as it is more responsive than plotly subplots package.
    """
    titles = [
        "{} Formation Volume Factor".format(phase.lower().capitalize()),
        "{} Viscosity".format(phase.lower().capitalize()),
    ]
    layout = {}
    layout.update(theme)
    layout.update({"hovermode": "closest"})
    # create subplots
    layout.update(
        {
            "annotations": [
                {
                    "showarrow": False,
                    "text": titles[0],
                    "x": 0.5,
                    "xanchor": "center",
                    "xref": "paper",
                    "y": 1.0,
                    "yanchor": "bottom",
                    "yref": "paper",
                    "font": {"size": 16},
                },
                {
                    "showarrow": False,
                    "text": titles[1],
                    "x": 0.5,
                    "xanchor": "center",
                    "xref": "paper",
                    "y": 0.475,
                    "yanchor": "bottom",
                    "yref": "paper",
                    "font": {"size": 16},
                },
            ],
        }
    )

    layout["legend"] = {"title": {"text": color_by.lower().capitalize()}}
    # format axes
    layout.update(
        {
            "xaxis": {
                "automargin": True,
                "zeroline": False,
                "anchor": "y",
                "domain": [0.0, 1.0],
                "matches": "x2",
                "showticklabels": False,
                "showgrid": True,
            },
            "xaxis2": {
                "automargin": True,
                "ticks": "",
                "showticklabels": True,
                "zeroline": False,
                "anchor": "y2",
                "domain": [0.0, 1.0],
                "title": {"text": "Pressure [barsa]", "standoff": 15},
                "showgrid": True,
            },
            "yaxis": {
                "automargin": True,
                "ticks": "",
                "zeroline": False,
                "anchor": "x",
                "domain": [0.525, 1.0],
                "title": {
                    "text": "{} Formation Volume Factor [rm3/sm3]".format(
                        phase.lower().capitalize()
                    )
                },
                "type": "linear",
                "showgrid": True,
            },
            "yaxis2": {
                "automargin": True,
                "ticks": "",
                "zeroline": False,
                "anchor": "x2",
                "domain": [0.0, 0.475],
                "title": {
                    "text": "{} Viscosity [cP]".format(phase.lower().capitalize())
                },
                "type": "linear",
                "showgrid": True,
            },
            "height": 800,
            "margin": {"t": 20, "b": 0},
            "plot_bgcolor": "rgba(0,0,0,0)",
        }
    )
    return layout

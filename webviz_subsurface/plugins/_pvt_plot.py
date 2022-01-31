########################################
#
#  Copyright (C) 2020-     Equinor ASA
#
########################################

from typing import Any, Callable, Dict, List, Tuple, Union

import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, State, callback_context, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE

from .._datainput.pvt_data import load_pvt_csv, load_pvt_dataframe


class PvtPlot(WebvizPluginABC):
    """Visualizes formation volume factor and viscosity data \
    for oil, gas and water from both **csv**, Eclipse **init** and **include** files.

    !> The plugin supports variations in PVT between ensembles, but not between \
    realizations in the same ensemble.
    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`pvt_relative_file_path`:** Local path to a csv file in each \
        realization with dumped pvt data.
    * **`read_from_init_file`:** A boolean flag stating if data shall be \
        read from an Eclipse INIT file instead of an INCLUDE file. \
        This is only used when **pvt_relative_file_path** is not given.
    * **`drop_ensemble_duplicates`:** A boolean flag stating if ensembles \
        which are holding duplicate data of other ensembles shall be dropped. \
        Defaults to False.

    ---
    The minimum requirement is to define `ensembles`.

    If no `pvt_relative_file_path` is given, the PVT data will be extracted automatically
    from the simulation decks of individual realizations using `fmu_ensemble` and `ecl2df`.
    If the `read_from_init_file` flag is set to True, the extraction procedure in
    `ecl2df` will be replaced by an individual extracting procedure that reads the
    normalized Eclipse INIT file.
    Note that the latter two extraction methods can be very slow for larger data and are therefore
    not recommended unless you have a very simple model/data deck.
    If the `drop_ensemble_duplicates` flag is set to True, any ensembles which are holding
    duplicate data of other ensembles will be dropped.

    `pvt_relative_file_path` is a path to a file stored per realization (e.g. in \
    `share/results/tables/pvt.csv`). `pvt_relative_file_path` columns:
    * One column named `KEYWORD` or `TYPE`: with Flow/Eclipse style keywords
        (e.g. `PVTO` and `PVDG`).
    * One column named `PVTNUM` with integer `PVTNUM` regions.
    * One column named `RATIO` or `R` with the gas-oil-ratio as the primary variate.
    * One column named `PRESSURE` with the fluids pressure as the secondary variate.
    * One column named `VOLUMEFACTOR` as the first covariate.
    * One column named `VISCOSITY` as the second covariate.

    The file can e.g. be dumped to disc per realization by a forward model in ERT using
    `ecl2df`.
    """

    PHASES = ["OIL", "GAS", "WATER"]

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        pvt_relative_file_path: str = None,
        read_from_init_file: bool = False,
        drop_ensemble_duplicates: bool = False,
    ):

        super().__init__()

        self.ensemble_paths = {
            ensemble: webviz_settings.shared_settings["scratch_ensembles"][ensemble]
            for ensemble in ensembles
        }

        self.plotly_theme = webviz_settings.theme.plotly_theme

        self.pvt_relative_file_path = pvt_relative_file_path

        self.read_from_init_file = read_from_init_file

        self.drop_ensemble_duplicates = drop_ensemble_duplicates

        if self.pvt_relative_file_path is None:
            self.pvt_data_frame = load_pvt_dataframe(
                self.ensemble_paths,
                use_init_file=read_from_init_file,
                drop_ensemble_duplicates=drop_ensemble_duplicates,
            )
        else:
            # Load data from all ensembles into a pandas DataFrame
            self.pvt_data_frame = load_pvt_csv(
                ensemble_paths=self.ensemble_paths,
                csv_file=self.pvt_relative_file_path,
                drop_ensemble_duplicates=drop_ensemble_duplicates,
            )

            self.pvt_data_frame = self.pvt_data_frame.rename(
                str.upper, axis="columns"
            ).rename(
                columns={"TYPE": "KEYWORD", "RS": "RATIO", "R": "RATIO", "GOR": "RATIO"}
            )

        # Ensure that the identifier string "KEYWORD" is contained in the header columns
        if "KEYWORD" not in self.pvt_data_frame.columns:
            raise ValueError(
                (
                    "There has to be a KEYWORD or TYPE column with corresponding Eclipse keyword."
                    "When not providing a csv file, make sure ecl2df is installed."
                )
            )

        self.phases_additional_info: List[str] = []
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTO").any():
            self.phases_additional_info.append("PVTO")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVDO").any():
            self.phases_additional_info.append("PVDO")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVCDO").any():
            self.phases_additional_info.append("PVCDO")
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTG").any():
            self.phases_additional_info.append("PVTG")
        elif self.pvt_data_frame["KEYWORD"].str.contains("PVDG").any():
            self.phases_additional_info.append("PVDG")
        if self.pvt_data_frame["KEYWORD"].str.contains("PVTW").any():
            self.phases_additional_info.append("PVTW")

        self.set_callbacks(app)

    @staticmethod
    def plot_visibility_options(phase: str = "") -> Dict[str, str]:
        options = {
            "fvf": "Formation Volume Factor",
            "viscosity": "Viscosity",
            "density": "Density",
        }
        if phase == "PVTO":
            options["ratio"] = "Gas/Oil Ratio (Rs)"
        if phase == "PVTG":
            options["ratio"] = "Vaporized Oil Ratio (Rv)"
        return options

    @property
    def phases(self) -> Dict[str, str]:
        phase_descriptions: Dict[str, str] = {}
        for i, phase in enumerate(PvtPlot.PHASES):
            phase_descriptions[phase] = self.phases_additional_info[i]
        return phase_descriptions

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
                "id": self.uuid("color_by"),
                "content": ("Choose the basis for your colormap."),
            },
            {
                "id": self.uuid("ensemble"),
                "content": ("Select ensembles."),
            },
            {
                "id": self.uuid("phase"),
                "content": (
                    "Choose a phase. Formation volume factor and viscosity data will be"
                    " shown for the selected phase in separate plots."
                ),
            },
            {
                "id": self.uuid("pvtnum"),
                "content": ("Choose PVTNUM regions."),
            },
        ]

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                wcc.Frame(
                    style={"flex": "1", "height": "90vh"},
                    children=[
                        wcc.Selectors(
                            label="Selectors",
                            children=[
                                wcc.Dropdown(
                                    label="Color by",
                                    id=self.uuid("color_by"),
                                    clearable=False,
                                    options=[
                                        {
                                            "label": i.lower().capitalize(),
                                            "value": i,
                                        }
                                        for i in self.color_options
                                    ],
                                    value=self.color_options[0],
                                ),
                                wcc.Dropdown(
                                    label="Ensembles",
                                    id=self.uuid("ensemble"),
                                    clearable=False,
                                    multi=True,
                                    options=[
                                        {"label": i, "value": i} for i in self.ensembles
                                    ],
                                    value=self.ensembles,
                                ),
                                wcc.Dropdown(
                                    label="Phase",
                                    id=self.uuid("phase"),
                                    clearable=False,
                                    options=[
                                        {
                                            "label": f"{value.lower().capitalize()} ({info})",
                                            "value": value,
                                        }
                                        for value, info in self.phases.items()
                                    ],
                                    multi=False,
                                    value=list(self.phases.keys())[0],
                                ),
                                wcc.Dropdown(
                                    label="Pvtnum",
                                    id=self.uuid("pvtnum"),
                                    clearable=False,
                                    multi=False,
                                    options=[
                                        {"label": i, "value": i} for i in self.pvtnums
                                    ],
                                    value=self.pvtnums[0],
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Show plots",
                            children=[
                                wcc.Checklist(
                                    id=self.uuid("plots_visibility"),
                                    options=[
                                        {"label": l, "value": v}
                                        for v, l in self.plot_visibility_options().items()
                                    ],
                                    value=[
                                        "fvf",
                                        "viscosity",
                                        "density",
                                        "ratio",
                                    ],
                                    labelStyle={"display": "block"},
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.Frame(
                    color="white",
                    highlight=False,
                    id=self.uuid("graphs"),
                    style={"flex": "6", "height": "90vh"},
                    children=[],
                ),
                dcc.Store(
                    id=self.uuid("init_callback"), storage_type="session", data=True
                ),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.uuid("graphs"), "children"),
            [
                Input(self.uuid("phase"), "value"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("pvtnum"), "value"),
                Input(self.uuid("color_by"), "value"),
                Input(self.uuid("plots_visibility"), "value"),
            ],
        )
        def _update_graph(
            phase: str,
            ensembles: Union[List[str], str],
            pvtnums: Union[List[str], str],
            color_by: str,
            plots_visibility: Union[List[str], str],
        ) -> html.Div:
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

            return html.Div(
                style={
                    "display": "flex",
                    "flex-wrap": "wrap",
                },
                children=[
                    create_graph(
                        data_frame,
                        color_by,
                        colors,
                        phase,
                        plot,
                        self.plot_visibility_options(self.phases[phase])[plot],
                        self.plotly_theme,
                    )
                    for plot in plots_visibility
                ],
            )

        @app.callback(
            [
                Output(self.uuid("plots_visibility"), "options"),
                Output(self.uuid("plots_visibility"), "value"),
            ],
            Input(self.uuid("phase"), "value"),
            State(self.uuid("plots_visibility"), "value"),
        )
        def _set_available_plots(
            phase: str,
            values: List[str],
        ) -> Tuple[List[dict], List[str]]:
            visibility_options = self.plot_visibility_options(self.phases[phase])
            return (
                [{"label": l, "value": v} for v, l in visibility_options.items()],
                [value for value in values if value in visibility_options],
            )

        @app.callback(
            [
                Output(self.uuid("ensemble"), "multi"),
                Output(self.uuid("ensemble"), "value"),
            ],
            [Input(self.uuid("color_by"), "value")],
        )
        def _set_ensemble_selector(color_by: str) -> Tuple[bool, Union[str, List[str]]]:
            """If ensemble is selected as color by, set the ensemble
            selector to allow multiple selections
            """
            if (
                callback_context.triggered is None
                or not callback_context.triggered[0]["prop_id"].split(".")[0]
            ):
                raise PreventUpdate

            if color_by == "ENSEMBLE":
                return True, self.ensembles

            # Note: Reimplement using stored_ensemble as soon as it is working properly.
            return (
                False,
                self.ensembles[0],
            )

        @app.callback(
            [
                Output(self.uuid("pvtnum"), "multi"),
                Output(self.uuid("pvtnum"), "value"),
            ],
            [Input(self.uuid("color_by"), "value")],
        )
        # pylint:
        def _set_pvtnum_selector(color_by: str) -> Tuple[bool, Union[str, List[str]]]:
            """If pvtnum is selected as color by, set the pvtnum
            selector to allow multiple selections
            """
            if (
                callback_context.triggered is None
                or not callback_context.triggered[0]["prop_id"].split(".")[0]
            ):
                raise PreventUpdate

            if color_by == "PVTNUM":
                return True, self.pvtnums

            # Note: Reimplement using stored_pvtnum as soon as it is working properly.
            return (
                False,
                self.pvtnums[0],
            )

    def add_webvizstore(
        self,
    ) -> List[Tuple[Callable, List[Dict[str, Any]]]]:
        return (
            [
                (
                    load_pvt_dataframe,
                    [
                        {
                            "ensemble_paths": self.ensemble_paths,
                            "use_init_file": self.read_from_init_file,
                            "drop_ensemble_duplicates": self.drop_ensemble_duplicates,
                        }
                    ],
                )
            ]
            if self.pvt_relative_file_path is None
            else [
                (
                    load_pvt_csv,
                    [
                        {
                            "ensemble_paths": self.ensemble_paths,
                            "csv_file": self.pvt_relative_file_path,
                            "drop_ensemble_duplicates": self.drop_ensemble_duplicates,
                        }
                    ],
                )
            ]
        )


def filter_data_frame(
    data_frame: pd.DataFrame, ensembles: List[str], pvtnums: List[str]
) -> pd.DataFrame:

    data_frame = data_frame.copy()
    data_frame = data_frame.loc[data_frame["ENSEMBLE"].isin(ensembles)]
    data_frame = data_frame.loc[data_frame["PVTNUM"].isin(pvtnums)]
    return data_frame.fillna(0)


def create_graph(
    data_frame: pd.DataFrame,
    color_by: str,
    colors: Dict[str, List[str]],
    phase: str,
    plot: str,
    plot_title: str,
    theme: dict,
) -> html.Div:
    return html.Div(
        style={
            "min-width": "500px",
            "min-height": "400px",
            "text-align": "center",
            "padding": "2%",
            "flex": "1 1 46%",
        },
        children=(
            [
                html.Span(plot_title, style={"font-weight": "bold"}),
                wcc.Graph(
                    figure={
                        "layout": plot_layout(
                            color_by,
                            theme,
                            rf"Pressure [{data_frame['PRESSURE_UNIT'].iloc[0]}]",
                            rf"[{data_frame['VOLUMEFACTOR_UNIT'].iloc[0]}]",
                        ),
                        "data": create_traces(
                            data_frame,
                            color_by,
                            colors,
                            phase,
                            "VOLUMEFACTOR",
                            True,
                            True,
                        ),
                    }
                ),
            ]
            if plot == "fvf"
            else [
                html.Span(plot_title, style={"font-weight": "bold"}),
                wcc.Graph(
                    figure={
                        "layout": plot_layout(
                            color_by,
                            theme,
                            rf"Pressure [{data_frame['PRESSURE_UNIT'].iloc[0]}]",
                            rf"[{data_frame['VISCOSITY_UNIT'].iloc[0]}]",
                        ),
                        "data": create_traces(
                            data_frame,
                            color_by,
                            colors,
                            phase,
                            "VISCOSITY",
                            True,
                            True,
                        ),
                    }
                ),
            ]
            if plot == "viscosity"
            else [
                html.Span(plot_title, style={"font-weight": "bold"}),
                wcc.Graph(
                    figure={
                        "layout": plot_layout(
                            color_by,
                            theme,
                            rf"Pressure [{data_frame['PRESSURE_UNIT'].iloc[0]}]",
                            rf"[{data_frame['DENSITY_UNIT'].iloc[0]}]",
                        ),
                        "data": create_traces(
                            data_frame,
                            color_by,
                            colors,
                            phase,
                            "DENSITY",
                            True,
                            True,
                        ),
                    }
                ),
            ]
            if plot == "density"
            else [
                html.Span(plot_title, style={"font-weight": "bold"}),
                wcc.Graph(
                    figure={
                        "layout": plot_layout(
                            color_by,
                            theme,
                            rf"Pressure [{data_frame['PRESSURE_UNIT'].iloc[0]}]",
                            rf"[{data_frame['RATIO_UNIT'].iloc[0]}]",
                        ),
                        "data": create_traces(
                            data_frame,
                            color_by,
                            colors,
                            phase,
                            "RATIO",
                            False,
                            True,
                            True,
                        ),
                    }
                ),
            ]
            if plot == "ratio"
            else []
        ),
    )


def create_traces(
    data_frame: pd.DataFrame,
    color_by: str,
    colors: Dict[str, List[str]],
    phase: str,
    column_name: str,
    show_scatter_values: bool,
    show_border_values: bool,
    show_border_markers: bool = False,
) -> List[dict]:
    """Renders line traces for individual realizations"""
    # pylint: disable-msg=too-many-locals
    # pylint: disable=too-many-nested-blocks
    # pylint: disable=too-many-branches

    traces = []
    hovertext: Union[List[str], str]
    border_value_pressure: Dict[str, list] = {}
    border_value_dependent: Dict[str, list] = {}

    dim_column_name = "RATIO"

    if phase == "OIL":
        data_frame = data_frame.loc[
            (data_frame["KEYWORD"] == "PVTO") | (data_frame["KEYWORD"] == "PVDO")
        ]
    elif phase == "GAS":
        data_frame = data_frame.loc[
            (data_frame["KEYWORD"] == "PVTG") | (data_frame["KEYWORD"] == "PVDG")
        ]
        dim_column_name = "PRESSURE"
    else:
        data_frame = data_frame.loc[data_frame["KEYWORD"] == "PVTW"]
        dim_column_name = "PRESSURE"

    data_frame = data_frame.sort_values(
        ["PRESSURE", "VOLUMEFACTOR", "VISCOSITY"],
        ascending=[True, True, True],
    )

    constant_group = (
        data_frame["PVTNUM"].iloc[0]
        if color_by == "ENSEMBLE"
        else data_frame["ENSEMBLE"].iloc[0]
    )

    for (group, grouped_data_frame) in data_frame.groupby(color_by):
        for set_no, set_value in enumerate(
            grouped_data_frame[dim_column_name].unique()
        ):
            for realization_no, (realization, realization_data_frame) in enumerate(
                grouped_data_frame.groupby("REAL")
            ):
                if group not in border_value_pressure:
                    border_value_pressure[group] = []
                    border_value_dependent[group] = []
                try:
                    border_value_pressure[group].append(
                        realization_data_frame.loc[
                            realization_data_frame[dim_column_name] == set_value
                        ]["PRESSURE"].iloc[0]
                    )
                    if column_name == "VISCOSITY":
                        if phase == "OIL":
                            border_value_dependent[group].append(
                                realization_data_frame[
                                    (
                                        realization_data_frame[dim_column_name]
                                        == set_value
                                    )
                                ]["VISCOSITY"].iloc[0]
                            )
                        else:
                            border_value_dependent[group].append(
                                realization_data_frame[
                                    (
                                        realization_data_frame[dim_column_name]
                                        == set_value
                                    )
                                ]["VISCOSITY"].max()
                            )
                    else:
                        border_value_dependent[group].append(
                            realization_data_frame.loc[
                                realization_data_frame[dim_column_name] == set_value
                            ][column_name].iloc[0]
                        )
                except IndexError as exc:
                    raise IndexError(
                        "This error is most likely due to PVT differences between "
                        "realizations within the same ensemble. This is currently not "
                        "supported."
                    ) from exc

                if show_scatter_values:
                    if phase == "GAS":
                        hovertext = [
                            create_hovertext(
                                phase,
                                realization_data_frame["KEYWORD"].iloc[0],
                                constant_group,
                                group,
                                color_by,
                                realization,
                                realization_data_frame.loc[
                                    (realization_data_frame["PRESSURE"] == y)
                                    & (realization_data_frame[column_name] == x)
                                ]["RATIO"].iloc[0],
                            )
                            for x, y in zip(
                                realization_data_frame.loc[
                                    realization_data_frame["PRESSURE"] == set_value
                                ][column_name],
                                realization_data_frame.loc[
                                    realization_data_frame["PRESSURE"] == set_value
                                ].PRESSURE,
                            )
                        ]
                    else:
                        hovertext = create_hovertext(
                            phase,
                            realization_data_frame["KEYWORD"].iloc[0],
                            constant_group,
                            group,
                            color_by,
                            realization,
                            set_value,
                        )

                    traces.extend(
                        [
                            {
                                "type": "scatter",
                                "x": realization_data_frame.loc[
                                    realization_data_frame[dim_column_name] == set_value
                                ]["PRESSURE"],
                                "y": realization_data_frame.loc[
                                    realization_data_frame[dim_column_name] == set_value
                                ][column_name],
                                "xaxis": "x",
                                "yaxis": "y",
                                "hovertext": hovertext,
                                "name": group,
                                "legendgroup": group,
                                "marker": {
                                    "color": colors.get(
                                        group, colors[list(colors.keys())[-1]]
                                    )
                                },
                                "showlegend": realization_no == 0 and set_no == 0,
                            }
                        ]
                    )
    if show_border_values:
        for group, group_border_value_pressure in border_value_pressure.items():
            traces.extend(
                [
                    {
                        "type": "scatter",
                        "mode": ("lines+markers" if show_border_markers else "lines"),
                        "x": group_border_value_pressure,
                        "y": border_value_dependent[group],
                        "xaxis": "x",
                        "yaxis": "y",
                        "legendgroup": group,
                        "line": {
                            "width": 1,
                            "color": colors.get(group, colors[list(colors.keys())[-1]]),
                        },
                        "showlegend": not show_scatter_values,
                    }
                ]
            )
    return traces


def create_hovertext(
    phase: str,
    keyword: str,
    constant_group: str,
    group: str,
    color_by: str,
    realization: str,
    ratio_value: float,
) -> str:
    hovertext: Union[str, list] = ""
    if phase == "OIL":
        # pylint: disable=consider-using-f-string
        hovertext = "{} Pvtnum: {}<br />Realization: {}, Ensemble: {}".format(
            f"Rs = {ratio_value}" if keyword == "PVTO" else "",
            group if color_by == "PVTNUM" else constant_group,
            realization,
            group if color_by == "ENSEMBLE" else constant_group,
        )
    elif phase == "GAS":
        # pylint: disable=consider-using-f-string
        hovertext = (
            "{}"
            "Pvtnum: "
            "{}<br />"
            "Realization: {}, Ensemble: "
            "{}".format(
                f"Rv = {ratio_value}, " if keyword == "PVTG" else "",
                group if color_by == "PVTNUM" else constant_group,
                realization,
                group if color_by == "ENSEMBLE" else constant_group,
            )
        )
    else:
        hovertext = (
            f"Pvtnum: {group if color_by == 'PVTNUM' else constant_group}<br />"
            f"Realization: {realization}, "
            f"Ensemble: {group if color_by == 'ENSEMBLE' else constant_group}"
        )

    return hovertext


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_layout(
    color_by: str,
    theme: dict,
    x_unit: str,
    y_unit: str,
) -> dict:
    layout = {}
    layout.update(theme)
    layout["legend"] = {"title": {"text": color_by.lower().capitalize()}}
    layout.update(
        {
            "xaxis": {
                "automargin": True,
                "zeroline": False,
                "anchor": "y",
                "domain": [0.0, 1.0],
                "title": {
                    "text": x_unit,
                    "standoff": 15,
                },
                "showticklabels": True,
                "showgrid": True,
            },
            "yaxis": {
                "automargin": True,
                "ticks": "",
                "zeroline": False,
                "anchor": "x",
                "domain": [0.0, 1.0],
                "title": {
                    "text": y_unit,
                },
                "type": "linear",
                "showgrid": True,
            },
            "margin": {"t": 20, "b": 0},
            "plot_bgcolor": "rgba(0,0,0,0)",
            "hovermode": "closest",
        }
    )
    return layout

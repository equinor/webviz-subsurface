from uuid import uuid4
from pathlib import Path
import copy

import numpy as np
import pandas as pd
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore
from webviz_config import WebvizPluginABC

from .._datainput.inplace_volumes import extract_volumes

from .._abbreviations.volume_terminology import (
    volume_description,
    volume_unit,
    volume_recoverable,
)
from .._abbreviations.number_formatting import TABLE_STATISTICS_BASE


class InplaceVolumes(WebvizPluginABC):
    """### InplaceVolumes

This plugin visualizes inplace volumetrics results from
FMU ensembles.

Input can be given either as aggregated csv files for volumes or or as an ensemble name
defined in *plugin_settings* and volumetric csv files stored per realizations.

#### Volumetric input

The volumetric csv files must follow FMU standards.
[Example csv file](
https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv)

The columns: *ZONE*, *REGION*, *FACIES*, *LICENSE* and *SOURCE* will be used as available
filters if present. (*SOURCE* is relevant if calculations are done for multiple grids).

Remaining columns are seen as volumetric responses. Any names are allowed,
but the following responses are given more descriptive names automatically:

- **BULK_OIL**: Bulk Volume (Oil)
- **NET_OIL**: Net Volume (Oil)
- **PORE_OIL**: Pore Volume (Oil)
- **HCPV_OIL**: Hydro Carbon Pore Volume (Oil)
- **STOIIP_OIL**: Stock Tank Oil In Place
- **BULK_GAS**: Bulk Volume (Gas)
- **NET_GAS**: Net Volume (Gas)
- **PORV_GAS**: Pore Volume (Gas)
- **HCPV_GAS**: Hydro Carbon Pore Volume (Gas)
- **GIIP_GAS**: Gas In Place
- **RECOVERABLE_OIL**: Recoverable Volume (Oil)
- **RECOVERABLE_GAS**: Recoverable Volume (Gas)

* `csvfile`: Aggregated csvfile with 'REAL', 'ENSEMBLE' and 'SOURCE' columns
* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `volfiles`:  Key/value pair of csv files E.g. (geogrid: geogrid--oil.csv)
* `volfolder`: Optional local folder for csv files
* `response`: Optional initial visualized volume response

"""

    TABLE_STATISTICS = [("Response", {}), ("Group", {})] + TABLE_STATISTICS_BASE
    COLUMN_WIDTHS = [
        {"if": {"column_id": i}, "width": "10%"} for i, _ in TABLE_STATISTICS_BASE
    ]
    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        csvfile: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        response: str = "STOIIP_OIL",
        fipfile: Path = None,
        fip_column_keys: list = None,
        time_index: str = "monthly",
    ):

        super().__init__()

        self.csvfile = csvfile if csvfile else None
        if csvfile and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )
        if csvfile:
            self.volumes = read_csv(csvfile)

        elif ensembles and (volfiles or fipfile):
            volumes = []
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }

            self.volfolder = volfolder
            self.volfiles = volfiles
            self.fipfile = fipfile
            self.fip_column_keys = fip_column_keys
            self.time_index = time_index
            self.volumes = extract_volumes(
                self.ens_paths,
                self.volfolder,
                self.volfiles,
                self.fipfile,
                self.fip_column_keys,
                self.time_index,
            )

        else:
            raise ValueError(
                "Incorrent arguments. Either provide a 'csvfile' or 'ensembles' and 'volfiles'"
                " and/or 'fipfile'"
            )
        if not "DATE" in self.volumes.columns:
            self.volumes["DATE"] = "N/A"
        self.initial_response = response
        self.uid = uuid4()
        self.selectors_id = {x: str(uuid4()) for x in self.selectors}
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": ("Dashboard displaying in place volumetric results. "),
            },
            {
                "id": self.ids("graph"),
                "content": (
                    "Chart showing results for the current selection. "
                    "Different charts and options can be selected from the menu above."
                ),
            },
            {
                "id": self.ids("table"),
                "content": (
                    "The table shows statistics for the current active selection. "
                    "Rows can be filtered by searching, and sorted by "
                    "clicking on a column header."
                ),
            },
            {
                "id": self.ids("response"),
                "content": "Select the volumetric calculation to display.",
            },
            {
                "id": self.ids("plot-type"),
                "content": (
                    "Controls the type of the visualized chart. "
                    "Per realization shows bars per realization, "
                    "while the boxplot shows the range per sensitivity."
                ),
            },
            {
                "id": self.ids("group"),
                "content": ("Allows grouping of results on a given category."),
            },
            {
                "id": self.ids("date"),
                "content": (
                    "Select date, `Initial` can be used to compare initial inplace between grids"
                    " and simulation."
                ),
            },
            {
                "id": self.ids("mode"),
                "content": ("Select mode, `Volume` or `Recovery factor`."),
            },
            {
                "id": self.ids("filters"),
                "content": (
                    "Filter on different combinations of e.g. zones, facies and regions "
                    "(The options will vary dependent on what was included "
                    "in the calculation.)"
                ),
            },
        ]

    def add_webvizstore(self):
        return (
            [((read_csv, [{"csv_file": self.csvfile}]))]
            if self.csvfile
            else [
                (
                    extract_volumes,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "volfolder": self.volfolder,
                            "volfiles": self.volfiles,
                            "fipfile": self.fipfile,
                            "column_keys": self.fip_column_keys,
                            "time_index": self.time_index,
                        }
                    ],
                )
            ]
        )

    @property
    def vol_columns(self):
        """List of all columns in dataframe"""
        return list(self.volumes.columns)

    @property
    def all_selectors(self):
        """List of all possible selectors"""
        return ["SOURCE", "ENSEMBLE", "ZONE", "REGION", "FACIES", "LICENSE"]

    @property
    def plot_types(self):
        """List of available plots"""
        return ["Histogram", "Per realization", "Box plot"]

    @property
    def selectors(self):
        """List of available selector columns in dframe"""
        return [x for x in self.all_selectors if x in self.vol_columns]

    @property
    def responses(self):
        """List of available volume responses in dframe"""
        return [
            x
            for x in self.vol_columns
            if x not in self.selectors and x not in ["REAL", "DATE"]
        ]

    @property
    def dates(self):
        return list(self.volumes["DATE"].unique())

    @property
    def modes(self):
        """List of available modes"""
        return ["Volume", "Recovery factor"]

    @property
    def vol_callback_inputs(self):
        """Returns all Dash inputs for selecting and filtering volumes
        The number of inputs will vary depending on the available
        selector columns in the volumes dataframe
        """
        inputs = []
        inputs.append(Input(self.ids("response"), "value"))
        inputs.append(Input(self.ids("plot-type"), "value"))
        inputs.append(Input(self.ids("group"), "value"))
        inputs.append(Input(self.ids("date"), "value"))
        inputs.append(Input(self.ids("mode"), "value"))
        for selector in self.selectors:
            inputs.append(Input(self.selectors_id[selector], "value"))
        return inputs

    @property
    def selector_dropdowns(self):
        """Makes dropdowns for each selector.
        Args:
            dframe - Volumetrics Dataframe
            selectors - List of selector columns
        Return:
            dcc.Dropdown objects
        """
        dropdowns = []
        for selector in self.selectors:
            elements = list(self.volumes[selector].unique())
            multi = True

            if selector in ["ENSEMBLE", "SOURCE"]:
                value = elements[0]
            else:
                value = elements

            dropdowns.append(
                html.Div(
                    children=[
                        html.Details(
                            open=True,
                            children=[
                                html.Summary(selector.lower().capitalize()),
                                dcc.Dropdown(
                                    id=self.selectors_id[selector],
                                    options=[
                                        {"label": i, "value": i} for i in elements
                                    ],
                                    value=value,
                                    multi=multi,
                                    clearable=False,
                                ),
                            ],
                        )
                    ]
                )
            )
        return dropdowns

    @property
    def style_plot_options(self):
        """Simple grid layout for the selector row"""
        return {
            "display": "grid",
            "align-content": "space-around",
            "justify-content": "space-between",
            "grid-template-columns": "4fr 2fr 2fr 2fr 2fr 1fr",
        }

    @property
    def style_layout(self):
        """Simple grid layout for the main elements"""
        return {
            "display": "grid",
            "align-content": "space-around",
            "justify-content": "space-between",
            "grid-template-columns": "5fr 1fr",
        }

    @property
    def plot_options_layout(self):
        """Row layout of dropdowns for plot options"""
        return html.Div(
            style=self.style_plot_options,
            children=[
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Response:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("response"),
                                options=[
                                    {"label": volume_description(i), "value": i,}
                                    for i in self.responses
                                ],
                                value=self.initial_response
                                if self.initial_response in self.responses
                                else self.responses[0],
                                clearable=False,
                            ),
                        ]
                    )
                ),
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Plot type:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("plot-type"),
                                options=[
                                    {"label": i, "value": i} for i in self.plot_types
                                ],
                                value="Per realization",
                                clearable=False,
                            ),
                        ]
                    )
                ),
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Group by:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("group"),
                                options=[
                                    {"label": i.lower().capitalize(), "value": i}
                                    for i in self.selectors
                                ],
                                value=None,
                                placeholder="Not grouped",
                            ),
                        ]
                    )
                ),
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Date:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("date"),
                                options=[{"label": i, "value": i} for i in self.dates],
                                value=self.dates[0],
                                clearable=False,
                            ),
                        ]
                    )
                ),
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Mode:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("mode"),
                                options=[
                                    {"label": i, "value": i, "disabled": False}
                                    for i in self.modes
                                ],
                                value=self.modes[0],
                                clearable=False,
                            ),
                        ]
                    )
                ),
            ],
        )

    @property
    def layout(self):
        """Main layout"""
        return html.Div(
            id=self.ids("layout"),
            children=[
                html.Div(
                    style=self.style_layout,
                    children=[
                        html.Div(
                            children=[
                                self.plot_options_layout,
                                html.Div(
                                    style={"height": 400},
                                    children=wcc.Graph(id=self.ids("graph")),
                                ),
                                html.Div(
                                    dash_table.DataTable(
                                        id=self.ids("table"),
                                        style_cell_conditional=InplaceVolumes.COLUMN_WIDTHS,
                                    )
                                ),
                            ]
                        ),
                        html.Div(
                            children=[
                                dcc.Store(id=self.ids("stored_ensemble"), data={}),
                                dcc.Store(id=self.ids("stored_source"), data={}),
                                html.P("Filters:", style={"font-weight": "bold"}),
                                html.Div(
                                    id=self.ids("filters"),
                                    children=self.selector_dropdowns,
                                ),
                            ]
                        ),
                    ],
                )
            ],
        )

    # pylint: disable=too-many-locals
    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.ids("graph"), "figure"),
                Output(self.ids("table"), "data"),
                Output(self.ids("table"), "columns"),
            ],
            self.vol_callback_inputs,
        )
        def _render_vol_chart(*args):
            """Renders a volume visualization either as a Plotly Graph or
            as a Dash table object.
            The arguments are given by the vol_callback_inputs property
            Args:
                response: The volumetrics response to plot
                plot_type: The type of graph/table to plot
                group: The selector to group the data by
                date: The date to plot data from
                selections: Active values from the selector columns
            Return:
                Plotly Graph/dash_table.DataTable
            """
            response = args[0]
            plot_type = args[1]
            group = args[2]
            date = args[3]
            mode = args[4]
            selections = args[5:]
            data = filter_dataframe(self.volumes, self.selectors, selections, date)
            if mode == "Recovery factor":
                data_init = filter_dataframe(
                    self.volumes, self.selectors, selections, "Initial"
                )
                if group:
                    data_init_grouped = data_init.groupby(group)

            # If not grouped make one trace
            if not group:
                dframe = (
                    data.groupby("REAL").sum(min_count=1).reset_index().to_dict("list")
                )
                if mode == "Recovery factor":
                    dframe[response] = calc_recovery(
                        data_init.groupby("REAL")
                        .sum(min_count=1)
                        .reset_index()
                        .to_dict("list")[response],
                        dframe[response],
                    )
                plot_traces = [plot_data(plot_type, dframe, response, "Total")]
                table = [plot_table(dframe, response, "Total")]
            # Else make one trace for each group member
            else:
                plot_traces = []
                table = []
                for name, vol_group_df in data.groupby(group):
                    dframe = (
                        vol_group_df.groupby("REAL")
                        .sum(min_count=1)
                        .reset_index()
                        .to_dict("list")
                    )
                    if mode == "Recovery factor":
                        try:
                            dframe[response] = calc_recovery(
                                data_init_grouped.get_group(name)
                                .groupby("REAL")
                                .sum(min_count=1)
                                .reset_index()
                                .to_dict("list")[response],
                                dframe[response],
                            )
                        except KeyError:
                            dframe[response] = []
                    trace = plot_data(plot_type, dframe, response, name)
                    if trace is not None:
                        plot_traces.append(trace)
                        table.append(plot_table(dframe, response, name))
            # Column specification
            columns = table_columns(response, mode)
            # Else make a graph object
            return (
                {
                    "data": plot_traces,
                    "layout": plot_layout(
                        plot_type, response, mode, theme=self.plotly_theme
                    ),
                },
                table,
                columns,
            )

        @app.callback(
            [
                Output(self.selectors_id["ENSEMBLE"], "multi"),
                Output(self.selectors_id["ENSEMBLE"], "value"),
            ],
            [Input(self.ids("group"), "value")],
            [State(self.ids("stored_ensemble"), "data")],
        )
        def _set_iteration_selector(group_by, stored_ensemble):
            """If iteration is selected as group by set the iteration
            selector to allow multiple selections, else use stored_ensemble
            """

            if group_by == "ENSEMBLE":
                return True, list(self.volumes["ENSEMBLE"].unique())

            return (
                False,
                stored_ensemble.get(
                    "ENSEMBLE", list(self.volumes["ENSEMBLE"].unique())[0]
                ),
            )

        @app.callback(
            Output(self.ids("stored_ensemble"), "data"),
            [Input(self.selectors_id["ENSEMBLE"], "value"),],
            [
                State(self.selectors_id["ENSEMBLE"], "multi"),
                State(self.ids("stored_ensemble"), "data"),
            ],
        )
        def _set_stored_ensemble(ens_value, ens_multi, stored_ensemble):
            if not ens_multi:
                stored_ensemble.update({"ENSEMBLE": ens_value})
            return stored_ensemble

        if "SOURCE" in self.selectors:

            @app.callback(
                [
                    Output(self.selectors_id["SOURCE"], "multi"),
                    Output(self.selectors_id["SOURCE"], "value"),
                ],
                [Input(self.ids("group"), "value")],
                [State(self.ids("stored_source"), "data")],
            )
            def _set_source_selector(group_by, stored_source):
                """If iteration is selected as group by set the iteration
                selector to allow multiple selections, else use single selection
                """
                if group_by == "SOURCE":
                    return True, list(self.volumes["SOURCE"].unique())

                return (
                    False,
                    stored_source.get(
                        "SOURCE", list(self.volumes["SOURCE"].unique())[0]
                    ),
                )

            @app.callback(
                Output(self.ids("stored_source"), "data"),
                [Input(self.selectors_id["SOURCE"], "value")],
                [
                    State(self.selectors_id["SOURCE"], "multi"),
                    State(self.ids("stored_source"), "data"),
                ],
            )
            def _set_stored_source(source_value, source_multi, stored_source):
                if not source_multi:
                    stored_source.update({"SOURCE": source_value})
                return stored_source

        @app.callback(
            [Output(self.ids("mode"), "options"), Output(self.ids("mode"), "value")],
            [Input(self.ids("response"), "value")],
            [State(self.ids("mode"), "value")],
        )
        def _set_mode(response, mode):
            """If the response is not listed as recoverable, reset mode to volume and disable
            recovery option. Note that this is only done for responses, not if the source is lacking
            data."""
            if volume_recoverable(response):
                return (
                    [{"label": i, "value": i, "disabled": False} for i in self.modes],
                    mode,
                )
            return (
                [
                    {"label": i, "value": i, "disabled": i == "Recovery factor"}
                    for i in self.modes
                ],
                mode if mode != "Recovery factor" else "Volume",
            )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_data(plot_type, ddict, response, name):
    values = ddict[response]

    if plot_type == "Histogram":
        if len(set(values)) == 1:
            values = values[0]
        output = {"x": values, "type": "histogram", "name": name}
    elif plot_type == "Box plot":
        output = {"y": values, "name": name, "type": "box"}
    elif plot_type == "Per realization":
        output = {"y": values, "x": ddict["REAL"], "name": name, "type": "bar"}
    else:
        output = None

    return output


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calc_recovery(initial_values: list, current_values: list):
    try:
        with np.errstate(
            divide="ignore", invalid="ignore"
        ):  # To avoid warnings when inplace = 0
            return np.divide(
                np.array(initial_values) - np.array(current_values),
                np.array(initial_values),
            )
    except ValueError:
        return []  # If a list is empty (missing data)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_table(ddict, response, name):
    values = ddict[response]
    try:
        output = {
            "Response": volume_description(response),
            "Group": str(name),
            "Minimum": min(values),
            "Maximum": max(values),
            "Mean": np.mean(values),
            "Stddev": np.std(values),
            "P10": np.percentile(values, 90),
            "P90": np.percentile(values, 10),
        }
    except ValueError:
        output = {
            "Response": volume_description(response),
            "Group": str(name),
            "Minimum": None,
            "Maximum": None,
            "Mean": None,
            "Stddev": None,
            "P10": None,
            "P90": None,
        }

    return output


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def table_columns(response, mode):
    columns = [
        {**{"name": i[0], "id": i[0]}, **i[1]}
        for i in copy.deepcopy(InplaceVolumes.TABLE_STATISTICS)
    ]
    if mode == "Recovery factor":
        for col in columns:
            try:
                col["format"]["specifier"] = ".2%"
            except KeyError:
                pass
    else:
        for col in columns:
            try:
                col["format"]["locale"]["symbol"] = [
                    "",
                    f"{volume_unit(response)}",
                ]
            except KeyError:
                pass
    return columns


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_layout(plot_type, response, mode, theme):
    layout = {}
    layout.update(theme["layout"])
    layout.update({"showlegend": True})
    layout["height"] = 400
    if plot_type == "Histogram":
        layout.update(
            {
                "barmode": "overlay",
                "bargap": 0.01,
                "bargroupgap": 0.2,
                "xaxis": {"title": volume_description(response)},
                "yaxis": {"title": "Count"},
            }
        )
        if mode == "Recovery factor":
            layout["xaxis"]["tickformat"] = "%"
    elif plot_type == "Box plot":
        layout.update({"yaxis": {"title": volume_description(response)}})
        if mode == "Recovery factor":
            layout["yaxis"]["tickformat"] = "%"
    else:
        layout.update(
            {
                "margin": {"l": 60, "r": 40, "b": 30, "t": 10},
                "yaxis": {"title": volume_description(response)},
                "xaxis": {"title": "Realization"},
            }
        )
        if mode == "Recovery factor":
            layout["yaxis"]["tickformat"] = "%"

    # output["colorway"] = colors
    return layout


# @CACHE.memoize(timeout=CACHE.TIMEOUT) Temporarily disabled cache due to:
# https://github.com/equinor/webviz-config/issues/211
def filter_dataframe(dframe, columns, column_values, date):
    df = dframe[dframe["DATE"] == date].copy()
    if not isinstance(columns, list):
        columns = [columns]
    for filt, col in zip(column_values, columns):
        if isinstance(filt, list):
            df = df.loc[df[col].isin(filt)]
        else:
            df = df.loc[df[col] == filt]
    return df


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)

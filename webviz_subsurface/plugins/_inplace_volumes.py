from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
import dash_table
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore
from webviz_config import WebvizPluginABC

from .._datainput.inplace_volumes import extract_volumes
from .._abbreviations import VOLUME_TERMINOLOGY


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
- **STOIIP_OIL**: Stock Tank Oil Initially In Place
- **BULK_GAS**: Bulk Volume (Gas)
- **NET_GAS**: Net Volume (Gas)
- **PORV_GAS**: Pore Volume (Gas)
- **HCPV_GAS**: Hydro Carbon Pore Volume (Gas)
- **GIIP_GAS**: Gas Initially In Place
- **RECOVERABLE_OIL**: Recoverable Volume (Oil)
- **RECOVERABLE_GAS**: Recoverable Volume (Gas)

* `csvfile`: Aggregated csvfile with 'REAL', 'ENSEMBLE' and 'SOURCE' columns
* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `volfiles`:  Key/value pair of csv files E.g. (geogrid: geogrid--oil.csv)
* `volfolder`: Optional local folder for csv files
* `response`: Optional initial visualized volume response

"""

    TABLE_STATISTICS = [
        "response",
        "group",
        "mean",
        "stddev",
        "minimum",
        "p90",
        "p10",
        "maximum",
    ]

    def __init__(
        self,
        app,
        csvfile: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        response: str = "STOIIP_OIL",
    ):

        super().__init__()

        self.csvfile = csvfile if csvfile else None
        if csvfile and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )
        if csvfile:
            self.volumes = read_csv(csvfile)

        elif ensembles and volfiles:
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.volfiles = volfiles
            self.volfolder = volfolder
            self.volumes = extract_volumes(
                self.ens_paths, self.volfolder, self.volfiles
            )

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )

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
            [(read_csv, [{"csv_file": self.csvfile}])]
            if self.csvfile
            else [
                (
                    extract_volumes,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "volfolder": self.volfolder,
                            "volfiles": self.volfiles,
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
        return [x for x in self.vol_columns if x not in self.selectors and x != "REAL"]

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
            "grid-template-columns": "2fr 1fr 1fr 1fr",
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
                                    {"label": VOLUME_TERMINOLOGY.get(i, i), "value": i,}
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
                                        columns=[
                                            {"name": i, "id": i}
                                            for i in InplaceVolumes.TABLE_STATISTICS
                                        ],
                                    )
                                ),
                            ]
                        ),
                        html.Div(
                            children=[
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

    def set_callbacks(self, app):
        @app.callback(
            [Output(self.ids("graph"), "figure"), Output(self.ids("table"), "data")],
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
                selections: Active values from the selector columns
            Return:
                Plotly Graph/dash_table.DataTable
            """
            response = args[0]
            plot_type = args[1]
            group = args[2]
            selections = args[3:]
            data = self.volumes
            data = filter_dataframe(data, self.selectors, selections)

            # If not grouped make one trace
            if not group:
                dframe = data.groupby("REAL").sum().reset_index()
                plot_traces = [plot_data(plot_type, dframe, response, "Total")]
                table = [plot_table(dframe, response, "Total")]
            # Else make one trace for each group member
            else:
                plot_traces = []
                table = []
                for name, vol_group_df in data.groupby(group):
                    dframe = vol_group_df.groupby("REAL").sum().reset_index()
                    trace = plot_data(plot_type, dframe, response, name)
                    if trace is not None:
                        plot_traces.append(trace)
                        table.append(plot_table(dframe, response, name))

            # Else make a graph object
            return (
                {
                    "data": plot_traces,
                    "layout": plot_layout(plot_type, response, theme=self.plotly_theme),
                },
                table,
            )

        @app.callback(
            [
                Output(self.selectors_id["ENSEMBLE"], "multi"),
                Output(self.selectors_id["ENSEMBLE"], "value"),
            ],
            [Input(self.ids("group"), "value")],
        )
        def _set_iteration_selector(group_by):
            """If iteration is selected as group by set the iteration
            selector to allow multiple selections, else use single selection
            """
            if group_by == "ENSEMBLE":
                return True, list(self.volumes["ENSEMBLE"].unique())

            return False, list(self.volumes["ENSEMBLE"].unique())[0]

        if "SOURCE" in self.selectors:

            @app.callback(
                [
                    Output(self.selectors_id["SOURCE"], "multi"),
                    Output(self.selectors_id["SOURCE"], "value"),
                ],
                [Input(self.ids("group"), "value")],
            )
            def _set_source_selector(group_by):
                """If iteration is selected as group by set the iteration
                selector to allow multiple selections, else use single selection
                """

                if group_by == "SOURCE" and "SOURCE" in self.selectors:
                    return True, list(self.volumes["SOURCE"].unique())

                return False, list(self.volumes["SOURCE"].unique())[0]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_data(plot_type, dframe, response, name):
    values = dframe[response]

    if plot_type == "Histogram":
        if values.nunique() == 1:
            values = values[0]
        output = {"x": values, "type": "histogram", "name": name}
    elif plot_type == "Box plot":
        output = {"y": values, "name": name, "type": "box"}
    elif plot_type == "Per realization":
        output = {"y": values, "x": dframe["REAL"], "name": name, "type": "bar"}
    else:
        output = None

    return output


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_table(dframe, response, name):
    values = dframe[response]
    try:
        output = {
            "response": VOLUME_TERMINOLOGY.get(response, response),
            "group": str(name),
            "minimum": f"{values.min():.2e}",
            "maximum": f"{values.max():.2e}",
            "mean": f"{values.mean():.2e}",
            "stddev": f"{values.std():.2e}",
            "p10": f"{np.percentile(values, 90):.2e}",
            "p90": f"{np.percentile(values, 10):.2e}",
        }
    except KeyError:
        output = None

    return output


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_layout(plot_type, response, theme):
    layout = {}
    layout.update(theme["layout"])
    layout["height"] = 400
    if plot_type == "Histogram":
        layout.update(
            {
                "barmode": "overlay",
                "bargap": 0.01,
                "bargroupgap": 0.2,
                "xaxis": {"title": VOLUME_TERMINOLOGY.get(response, response)},
                "yaxis": {"title": "Count"},
            }
        )
    elif plot_type == "Box plot":
        layout.update({"yaxis": {"title": VOLUME_TERMINOLOGY.get(response, response)}})
    else:
        layout.update(
            {
                "margin": {"l": 40, "r": 40, "b": 30, "t": 10},
                "yaxis": {"title": VOLUME_TERMINOLOGY.get(response, response)},
                "xaxis": {"title": "Realization"},
            }
        )

    # output["colorway"] = colors
    return layout


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_dataframe(dframe, columns, column_values):
    df = dframe.copy()
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

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
from webviz_config import WebvizContainerABC

from ..datainput import extract_volumes


class InplaceVolumes(WebvizContainerABC):
    """### Volumetrics

This container visualizes inplace volumetrics results from
FMU ensembles. Input can be given either as aggregated csv files
or as an ensemble name defined in 'container_settings' and csvfiles stored
per realizations.
In either case the csv files must follow FMU standards, that is it must have
one or more of the following columns:
'ZONE', 'REGION', 'FACIES', 'LICENSE' - these columns are used to filter the data.

Remaining columns are seen as volumetric responses. Any names are allowed,
but the following responses are given more descriptive names automatically:
"BULK_OIL": "Bulk Volume (Oil)"
"NET_OIL": "Net Volume (Oil)"
"PORE_OIL": "Pore Volume (Oil)"
"HCPV_OIL": "Hydro Carbon Pore Volume (Oil)"
"STOIIP_OIL": "Stock Tank Oil Initially Inplace"
"BULK_GAS": "Bulk Volume (Gas)"
"NET_GAS": "Net Volume (Gas)"
"PORV_GAS": "Pore Volume (Gas)"
"HCPV_GAS": "Hydro Carbon Pore Volume (Gas)"
"GIIP_GAS": "Gas Initially in-place"
"RECOVERABLE_OIL": "Recoverable Volume (Oil)"
"RECOVERABLE_GAS": "Recoverable Volume (Gas)"

* `csvfile`: Aggregated csvfile with 'REAL', 'ENSEMBLE' and 'SOURCE' columns
* `ensembles`: Which ensembles in `container_settings` to visualize.
* `volfiles`:  Key/value pair of csv files E.g. (geogrid: geogrid--oil.csv)
* `volfolder`: Optional local folder for csv files
* `response`: Optional initial visualized volume response

"""

    RESPONSES = {
        "BULK_OIL": "Bulk Volume (Oil)",
        "NET_OIL": "Net Volume (Oil)",
        "PORV_OIL": "Pore Volume (Oil)",
        "HCPV_OIL": "Hydro Carbon Pore Volume (Oil)",
        "STOIIP_OIL": "Stock Tank Oil Initially Inplace",
        "BULK_GAS": "Bulk Volume (Gas)",
        "NET_GAS": "Net Volume (Gas)",
        "PORV_GAS": "Pore Volume (Gas)",
        "HCPV_GAS": "Hydro Carbon Pore Volume (Gas)",
        "GIIP_GAS": "Gas Initially in-place",
        "RECOVERABLE_OIL": "Recoverable Volume (Oil)",
        "RECOVERABLE_GAS": "Recoverable Volume (Gas)",
    }

    def __init__(
        self,
        app,
        container_settings,
        csvfile: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        response: str = "STOIIP_OIL",
    ):
        self.csvfile = csvfile if csvfile else None
        self.colorway = app.webviz_settings.get("plotly_layout", {}).get("colorway", [])
        if csvfile and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )
        if csvfile:
            self.volumes = read_csv(csvfile)

        elif ensembles and volfiles:
            self.ens_paths = tuple(
                (ens, container_settings["scratch_ensembles"][ens]) for ens in ensembles
            )
            self.volfiles = tuple(volfiles.items())
            self.volfolder = volfolder
            self.volumes = extract_volumes(
                self.ens_paths, self.volfolder, self.volfiles
            )

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )

        self.initial_response = response
        self.radio_plot_type_id = "radio-plot-type-{}".format(uuid4())
        self.response_id = "response-{}".format(uuid4())
        self.chart_id = "chart-{}".format(uuid4())
        self.table_id = "table-{}".format(uuid4())
        self.radio_selectors_id = "radio-selectors-{}".format(uuid4())
        self.selectors_id = {x: str(uuid4()) for x in self.selectors}
        self.table_cols = [
            "response",
            "group",
            "mean",
            "stddev",
            "minimum",
            "p90",
            "p10",
            "maximum",
        ]

        self.set_callbacks(app)

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
        return ["Histogram", "Per realization", "Box Plot"]

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
        inputs.append(Input(self.response_id, "value"))
        inputs.append(Input(self.radio_plot_type_id, "value"))
        inputs.append(Input(self.radio_selectors_id, "value"))
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
                    children=[
                        html.P("Response:", style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id=self.response_id,
                            options=[
                                {
                                    "label": InplaceVolumes.RESPONSES.get(i, i),
                                    "value": i,
                                }
                                for i in self.responses
                            ],
                            value=self.initial_response
                            if self.initial_response in self.responses
                            else self.responses[0],
                            clearable=False,
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.P("Plot type:", style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id=self.radio_plot_type_id,
                            options=[{"label": i, "value": i} for i in self.plot_types],
                            value="Per realization",
                            clearable=False,
                        ),
                    ]
                ),
                html.Div(
                    children=[
                        html.P("Group by:", style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id=self.radio_selectors_id,
                            options=[
                                {"label": i.lower().capitalize(), "value": i}
                                for i in self.selectors
                            ],
                            value=None,
                            placeholder="Not grouped",
                        ),
                    ]
                ),
            ],
        )

    @property
    def layout(self):
        """Main layout"""
        return html.Div(
            [
                html.Div(
                    style=self.style_layout,
                    children=[
                        html.Div(
                            children=[
                                self.plot_options_layout,
                                html.Div(
                                    style={"height": 400},
                                    children=wcc.Graph(id=self.chart_id),
                                ),
                                html.Div(
                                    dash_table.DataTable(
                                        id=self.table_id,
                                        columns=[
                                            {"name": i, "id": i}
                                            for i in self.table_cols
                                        ],
                                    )
                                ),
                            ]
                        ),
                        html.Div(
                            children=[
                                html.P("Filters:", style={"font-weight": "bold"}),
                                html.Div(children=self.selector_dropdowns),
                            ]
                        ),
                    ],
                )
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [Output(self.chart_id, "figure"), Output(self.table_id, "data")],
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
                    "layout": plot_layout(plot_type, response, colors=self.colorway),
                },
                table,
            )

        @app.callback(
            [
                Output(self.selectors_id["ENSEMBLE"], "multi"),
                Output(self.selectors_id["ENSEMBLE"], "value"),
            ],
            [Input(self.radio_selectors_id, "value")],
        )
        def _set_iteration_selector(group_by):
            """If iteration is selected as group by set the iteration
            selector to allow multiple selections, else use single selection
            """
            if group_by == "ENSEMBLE":
                return True, list(self.volumes["ENSEMBLE"].unique())

            return False, list(self.volumes["ENSEMBLE"].unique())[0]

        @app.callback(
            [
                Output(self.selectors_id["SOURCE"], "multi"),
                Output(self.selectors_id["SOURCE"], "value"),
            ],
            [Input(self.radio_selectors_id, "value")],
        )
        def _set_source_selector(group_by):
            """If iteration is selected as group by set the iteration
            selector to allow multiple selections, else use single selection
            """

            if group_by == "SOURCE":
                return True, list(self.volumes["SOURCE"].unique())

            return False, list(self.volumes["SOURCE"].unique())[0]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_data(plot_type, dframe, response, name):
    values = dframe[response]

    if plot_type == "Histogram":
        if values.nunique() == 1:
            values = values[0]
        output = {"x": values, "type": "histogram", "name": name}
    elif plot_type == "Box Plot":
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
            "response": InplaceVolumes.RESPONSES.get(response, response),
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
def plot_layout(plot_type, response, colors):
    if plot_type == "Histogram":
        output = {
            "barmode": "overlay",
            "bargap": 0.01,
            "bargroupgap": 0.2,
            "xaxis": {"title": InplaceVolumes.RESPONSES.get(response, response)},
            "yaxis": {"title": "Count"},
        }
    elif plot_type == "Box Plot":
        output = {"yaxis": {"title": InplaceVolumes.RESPONSES.get(response, response)}}
    else:
        output = {
            "margin": {"l": 40, "r": 40, "b": 30, "t": 10},
            "yaxis": {"title": InplaceVolumes.RESPONSES.get(response, response)},
            "xaxis": {"title": "Realization"},
        }
    output["height"] = 400
    output["colorway"] = colors
    return output


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

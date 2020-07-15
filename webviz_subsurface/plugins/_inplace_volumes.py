from pathlib import Path
import json

import numpy as np
import pandas as pd
from dash_table import DataTable
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import webviz_core_components as wcc
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore
from webviz_config import WebvizPluginABC

from .._datainput.inplace_volumes import extract_volumes, get_metadata
from .._abbreviations.volume_terminology import (
    volume_description,
    column_title,
)
from .._abbreviations.number_formatting import table_statistics_base


class InplaceVolumes(WebvizPluginABC):
    """Visualizes inplace volumetric results from
FMU ensembles.

Input can be given either as aggregated `csv` files or as ensemble name(s)
defined in `shared_settings` (with volumetric `csv` files stored per realization).

---

**Using aggregated data**
* **`csvfile`:** Aggregated csvfile with `REAL`, `ENSEMBLE` and `SOURCE` columns \
(absolute path or relative to config file).

**Using data stored per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`volfiles`:**  Key/value pair of csv files E.g. `{geogrid: geogrid--oil.csv}`.
Only relevant if `ensembles` is defined. The key (e.g. `geogrid`) will be used as `SOURCE`.
* **`volfolder`:** Local folder for the `volfiles`.

**Common settings for both input options**
* **`response`:** Optional volume response to visualize initially.
* **`metadata`:** Optional path to volume response metadata stored in a json-file.
Supports descriptions and units.
---

?> The input files must follow FMU standards.

* [Example of an aggregated file for `csvfiles`](https://github.com/equinor/\
webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/\
realization-0/iter-0/share/results/volumes/geogrid--oil.csv).

* ADD PATH TO METADATAFILE

**The following columns will be used as available filters, if present:**

* `ZONE`
* `REGION`
* `FACIES`
* `LICENSE`
* `SOURCE` (relevant if calculations are done for multiple grids)


**Remaining columns are seen as volumetric responses.**

All names are allowed (except those mentioned above, in addition to `REAL` and `ENSEMBLE`), \
but the following responses are given more descriptive names automatically, unless another \
description is given in `metadata`:

* `BULK_OIL`: Bulk Volume (Oil)
* `NET_OIL`: Net Volume (Oil)
* `PORE_OIL`: Pore Volume (Oil)
* `HCPV_OIL`: Hydro Carbon Pore Volume (Oil)
* `STOIIP_OIL`: Stock Tank Oil Initially In Place
* `BULK_GAS`: Bulk Volume (Gas)
* `NET_GAS`: Net Volume (Gas)
* `PORV_GAS`: Pore Volume (Gas)
* `HCPV_GAS`: Hydro Carbon Pore Volume (Gas)
* `GIIP_GAS`: Gas Initially In Place
* `RECOVERABLE_OIL`: Recoverable Volume (Oil)
* `RECOVERABLE_GAS`: Recoverable Volume (Gas)

"""

    TABLE_STATISTICS = [("Group", {})] + table_statistics_base()

    def __init__(
        self,
        app,
        csvfile: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        response: str = "STOIIP_OIL",
        metadata: Path = None,
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
        self.metadata_path = metadata
        self.metadata = (
            self.metadata_path
            if self.metadata_path is None
            else json.load(get_metadata(self.metadata_path))
        )
        self.selectors_id = {x: self.uuid(x) for x in self.selectors}
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        if len(self.volumes["ENSEMBLE"].unique()) > 1:
            self.initial_plot = "Box plot"
            self.initial_group = "ENSEMBLE"
        else:
            self.initial_plot = "Per realization"
            self.initial_group = None
        self.set_callbacks(app)

    @property
    def tour_steps(self):
        return [
            {
                "id": self.uuid("layout"),
                "content": ("Dashboard displaying in place volumetric results. "),
            },
            {
                "id": self.uuid("graph"),
                "content": (
                    "Chart showing results for the current selection. "
                    "Different charts and options can be selected from the menu above."
                ),
            },
            {
                "id": self.uuid("table"),
                "content": (
                    "The table shows statistics for the current active selection. "
                    "Rows can be filtered by searching, and sorted by "
                    "clicking on a column header."
                ),
            },
            {
                "id": self.uuid("response"),
                "content": "Select the volumetric calculation to display.",
            },
            {
                "id": self.uuid("plot-type"),
                "content": (
                    "Controls the type of the visualized chart. "
                    "Per realization shows bars per realization, "
                    "while the boxplot shows the range per sensitivity."
                ),
            },
            {
                "id": self.uuid("group"),
                "content": ("Allows grouping of results on a given category."),
            },
            {
                "id": self.uuid("filters"),
                "content": (
                    "Filter on different combinations of e.g. zones, facies and regions "
                    "(The options will vary dependent on what was included "
                    "in the calculation.)"
                ),
            },
        ]

    def add_webvizstore(self):
        functions = []
        if self.csvfile:
            functions.append((read_csv, [{"csv_file": self.csvfile}]))
        else:
            functions.append(
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
            )
        if self.metadata is not None:
            functions.append((get_metadata, [{"metadata": self.metadata_path}]))
        return functions

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
        inputs.append(Input(self.uuid("response"), "value"))
        inputs.append(Input(self.uuid("plot-type"), "value"))
        inputs.append(Input(self.uuid("group"), "value"))
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
                                wcc.Select(
                                    id=self.selectors_id[selector],
                                    options=[
                                        {"label": i, "value": i} for i in elements
                                    ],
                                    value=value,
                                    multi=True,
                                    size=min(20, len(elements)),
                                ),
                            ],
                        )
                    ]
                )
            )
        return dropdowns

    @property
    def plot_options_layout(self):
        """Row layout of dropdowns for plot options"""
        return wcc.FlexBox(
            children=[
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Response:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.uuid("response"),
                                options=[
                                    {
                                        "label": volume_description(i, self.metadata),
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
                    )
                ),
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Plot type:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.uuid("plot-type"),
                                options=[
                                    {"label": i, "value": i} for i in self.plot_types
                                ],
                                value=self.initial_plot,
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
                                id=self.uuid("group"),
                                options=[
                                    {"label": i.lower().capitalize(), "value": i}
                                    for i in self.selectors
                                ],
                                value=self.initial_group,
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
            children=[
                wcc.FlexBox(
                    id=self.uuid("layout"),
                    children=[
                        html.Div(
                            style={"flex": 1},
                            children=[
                                html.Span("Filters:", style={"font-weight": "bold"}),
                                html.Div(
                                    id=self.uuid("filters"),
                                    children=self.selector_dropdowns,
                                ),
                            ],
                        ),
                        html.Div(
                            style={"flex": 5},
                            children=[
                                self.plot_options_layout,
                                html.Div(
                                    style={"height": 400},
                                    children=wcc.Graph(id=self.uuid("graph")),
                                ),
                                html.Div(
                                    children=[
                                        html.Div(
                                            id=self.uuid("table_title"),
                                            style={"textAlign": "center"},
                                            children="",
                                        ),
                                        DataTable(
                                            id=self.uuid("table"),
                                            sort_action="native",
                                            filter_action="native",
                                            page_action="native",
                                            page_size=10,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.uuid("graph"), "figure"),
                Output(self.uuid("table"), "data"),
                Output(self.uuid("table"), "columns"),
                Output(self.uuid("table_title"), "children"),
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
            # Column specification
            columns = [
                {**{"name": i[0], "id": i[0]}, **i[1]}
                for i in InplaceVolumes.TABLE_STATISTICS
            ]
            # Make a graph object and return
            return (
                {
                    "data": plot_traces,
                    "layout": plot_layout(
                        plot_type,
                        response,
                        theme=self.plotly_theme,
                        metadata=self.metadata,
                    ),
                },
                table,
                columns,
                column_title(response, self.metadata),
            )

        @app.callback(
            [
                Output(self.selectors_id["ENSEMBLE"], "multi"),
                Output(self.selectors_id["ENSEMBLE"], "value"),
                Output(self.selectors_id["ENSEMBLE"], "size"),
            ],
            [Input(self.uuid("group"), "value")],
        )
        def _set_iteration_selector(group_by):
            """If iteration is selected as group by set the iteration
            selector to allow multiple selections, else use single selection
            """
            selectors = list(self.volumes["ENSEMBLE"].unique())
            if group_by == "ENSEMBLE":
                return True, selectors, len(selectors)

            return False, selectors[0], 1

        if "SOURCE" in self.selectors:

            @app.callback(
                [
                    Output(self.selectors_id["SOURCE"], "multi"),
                    Output(self.selectors_id["SOURCE"], "value"),
                    Output(self.selectors_id["SOURCE"], "size"),
                ],
                [Input(self.uuid("group"), "value")],
            )
            def _set_source_selector(group_by):
                """If iteration is selected as group by set the iteration
                selector to allow multiple selections, else use single selection
                """
                selectors = list(self.volumes["SOURCE"].unique())
                if group_by == "SOURCE" and "SOURCE" in self.selectors:
                    return True, selectors, len(selectors)

                return False, selectors[0], 1


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
            "Group": str(name),
            "Minimum": values.min(),
            "Maximum": values.max(),
            "Mean": values.mean(),
            "Stddev": values.std(),
            "P10": np.percentile(values, 90),
            "P90": np.percentile(values, 10),
        }
    except KeyError:
        output = None

    return output


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_layout(plot_type, response, theme, metadata):
    layout = {}
    layout.update(theme["layout"])
    layout["height"] = 400
    if plot_type == "Histogram":
        layout.update(
            {
                "barmode": "overlay",
                "bargap": 0.01,
                "bargroupgap": 0.2,
                "xaxis": {"title": column_title(response, metadata)},
                "yaxis": {"title": "Count"},
            }
        )
    elif plot_type == "Box plot":
        layout.update({"yaxis": {"title": column_title(response, metadata)}})
    else:
        layout.update(
            {
                "margin": {"l": 60, "r": 40, "b": 30, "t": 10},
                "yaxis": {"title": column_title(response, metadata)},
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

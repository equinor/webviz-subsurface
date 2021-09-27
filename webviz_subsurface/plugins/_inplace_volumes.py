from pathlib import Path
from typing import Callable, Iterable, List, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, dash_table, dcc, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.deprecation_decorators import deprecated_plugin
from webviz_config.webviz_store import webvizstore

from .._abbreviations.number_formatting import table_statistics_base
from .._abbreviations.volume_terminology import volume_description, volume_unit
from .._datainput.inplace_volumes import extract_volumes


@deprecated_plugin(
    "Relevant functionality is implemented in the VolumetricAnalysis plugin."
)
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

---

?> The input files must follow FMU standards.

* [Example of an aggregated file for `csvfiles`](https://github.com/equinor/\
webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/\
realization-0/iter-0/share/results/volumes/geogrid--oil.csv).

**The following columns will be used as available filters, if present:**

* `ZONE`
* `REGION`
* `FACIES`
* `LICENSE`
* `SOURCE` (relevant if calculations are done for multiple grids)


**Remaining columns are seen as volumetric responses.**

All names are allowed (except those mentioned above, in addition to `REAL` and `ENSEMBLE`), \
but the following responses are given more descriptive names automatically:

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

    TABLE_STATISTICS: List[Tuple[str, dict]] = [("Group", {})] + table_statistics_base()

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
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
            self.volumes: pd.DataFrame = read_csv(csvfile)

        elif ensembles and volfiles:
            self.ens_paths = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
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
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.initial_group: Union[str, None] = None
        if len(self.volumes["ENSEMBLE"].unique()) > 1:
            self.initial_plot = "Box plot"
            self.initial_group = "ENSEMBLE"
        else:
            self.initial_plot = "Per realization"
            self.initial_group = None
        self.set_callbacks(app)

    def ids(self, element: str) -> str:
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self) -> List[dict]:
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

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
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
    def vol_columns(self) -> List[str]:
        """List of all columns in dataframe"""
        return list(self.volumes.columns)

    @property
    def all_selectors(self) -> List[str]:
        """List of all possible selectors"""
        return ["SOURCE", "ENSEMBLE", "ZONE", "REGION", "FACIES", "LICENSE"]

    @property
    def plot_types(self) -> List[str]:
        """List of available plots"""
        return ["Histogram", "Per realization", "Box plot"]

    @property
    def selectors(self) -> List[str]:
        """List of available selector columns in dframe"""
        return [x for x in self.all_selectors if x in self.vol_columns]

    @property
    def responses(self) -> List[str]:
        """List of available volume responses in dframe"""
        return [x for x in self.vol_columns if x not in self.selectors and x != "REAL"]

    @property
    def vol_callback_inputs(self) -> List[Input]:
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
    def selector_dropdowns(self) -> List[html.Div]:
        """Makes dropdowns for each selector.
        Args:
            dframe - Volumetrics Dataframe
            selectors - List of selector columns
        Return:
            dcc.Dropdown objects
        """
        dropdowns: List[html.Div] = []
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
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
                        )
                    ]
                )
            )
        return dropdowns

    @property
    def plot_options_layout(self) -> wcc.FlexBox:
        """Row layout of dropdowns for plot options"""
        return wcc.FlexBox(
            children=[
                html.Div(
                    children=html.Label(
                        children=[
                            html.Span("Response:", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id=self.ids("response"),
                                options=[
                                    {"label": volume_description(i), "value": i}
                                    for i in self.responses
                                ],
                                value=self.initial_response
                                if self.initial_response in self.responses
                                else self.responses[0],
                                clearable=False,
                                persistence=True,
                                persistence_type="session",
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
                                value=self.initial_plot,
                                clearable=False,
                                persistence=True,
                                persistence_type="session",
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
                                value=self.initial_group,
                                placeholder="Not grouped",
                                persistence=True,
                                persistence_type="session",
                            ),
                        ]
                    )
                ),
            ],
        )

    @property
    def layout(self) -> html.Div:
        """Main layout"""
        return html.Div(
            children=[
                wcc.FlexBox(
                    id=self.ids("layout"),
                    children=[
                        html.Div(
                            style={"flex": 1},
                            children=[
                                html.Span("Filters:", style={"font-weight": "bold"}),
                                html.Div(
                                    id=self.ids("filters"),
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
                                    children=wcc.Graph(id=self.ids("graph")),
                                ),
                                html.Div(
                                    children=[
                                        html.Div(
                                            id=self.ids("table_title"),
                                            style={"textAlign": "center"},
                                            children="",
                                        ),
                                        dash_table.DataTable(
                                            id=self.ids("table"),
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

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            [  # type: ignore
                Output(self.ids("graph"), "figure"),
                Output(self.ids("table"), "data"),
                Output(self.ids("table"), "columns"),
                Output(self.ids("table_title"), "children"),
            ],
            self.vol_callback_inputs,
        )
        # TODO(Sigurd) Doesn't seem to make sense with type hints
        # here unless all args are of same type
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
            # pylint: disable=line-too-long
            # TODO(Sigurd) Tricky to figure out the type hints without a bit of guesswork here due to the use of *args
            # The reasoning below is:
            #   response:   ids("response")  dcc.Dropdown(multi=False, clearable=False) => str
            #   plot_type:  ids("plot_type") dcc.Dropdown(multi=False, clearable=False) => str
            #   group:      ids("group")     dcc.Dropdown(multi=False, clearable=True)  => Union[str, None]
            #   selection:  multiple ids     n*wcc.Select(multi=?, clearable=?)         => Tuple[Union[str, List[str], None], ...]
            response: str = args[0]
            plot_type: str = args[1]
            group: Union[str, None] = args[2]
            selections: Tuple[Union[str, List[str], None], ...] = args[3:]
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
                    "layout": plot_layout(plot_type, response, theme=self.plotly_theme),
                },
                table,
                columns,
                f"{volume_description(response)} [{volume_unit(response)}]",
            )

        @app.callback(
            [
                Output(self.selectors_id["ENSEMBLE"], "multi"),
                Output(self.selectors_id["ENSEMBLE"], "value"),
                Output(self.selectors_id["ENSEMBLE"], "size"),
            ],
            [Input(self.ids("group"), "value")],
        )
        def _set_iteration_selector(
            group_by: Union[str, None]
        ) -> Tuple[bool, Union[str, list], int]:
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
                [Input(self.ids("group"), "value")],
            )
            def _set_source_selector(
                group_by: Union[str, None]
            ) -> Tuple[bool, Union[str, list], int]:
                """If iteration is selected as group by set the iteration
                selector to allow multiple selections, else use single selection
                """
                selectors = list(self.volumes["SOURCE"].unique())
                if group_by == "SOURCE" and "SOURCE" in self.selectors:
                    return True, selectors, len(selectors)

                return False, selectors[0], 1


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def plot_data(
    plot_type: str, dframe: pd.DataFrame, response: str, name: str
) -> Union[dict, None]:
    values = dframe[response]

    output: Union[dict, None] = None
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
def plot_table(dframe: pd.DataFrame, response: str, name: str) -> Union[dict, None]:
    values = dframe[response]

    output: Union[dict, None] = None
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
def plot_layout(plot_type: str, response: str, theme: dict) -> dict:
    layout = {}
    layout.update(theme["layout"])
    layout["height"] = 400
    if plot_type == "Histogram":
        layout.update(
            {
                "barmode": "overlay",
                "bargap": 0.01,
                "bargroupgap": 0.2,
                "xaxis": {
                    "title": f"{volume_description(response)} [{volume_unit(response)}]"
                },
                "yaxis": {"title": "Count"},
            }
        )
    elif plot_type == "Box plot":
        layout.update(
            {
                "yaxis": {
                    "title": f"{volume_description(response)} [{volume_unit(response)}]"
                }
            }
        )
    else:
        layout.update(
            {
                "margin": {"l": 60, "r": 40, "b": 30, "t": 10},
                "yaxis": {
                    "title": f"{volume_description(response)} [{volume_unit(response)}]"
                },
                "xaxis": {"title": "Realization"},
            }
        )

    # output["colorway"] = colors
    return layout


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_dataframe(
    dframe: pd.DataFrame,
    columns: Union[str, List[str]],
    column_values: Iterable[Union[str, List[str]]],
) -> pd.DataFrame:
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
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)

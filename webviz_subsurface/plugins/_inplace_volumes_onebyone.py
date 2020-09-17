import json
from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
from dash_table import DataTable
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .._private_plugins.tornado_plot import TornadoPlot
from .._datainput.inplace_volumes import extract_volumes
from .._datainput.fmu_input import get_realizations, find_sens_type
from .._abbreviations.volume_terminology import volume_description, volume_unit
from .._abbreviations.number_formatting import table_statistics_base


class InplaceVolumesOneByOne(WebvizPluginABC):
    # pylint: disable=too-many-instance-attributes
    """Visualizes inplace volumetrics related to a FMU ensemble with a design matrix.

Input can be given either as an aggregated `csv` file for volumes and sensitivity information,
or as ensemble name(s) defined in `shared_settings` and volumetric `csv` files
stored per realization.

---

* **`csvfile_vol`:** Aggregated csvfile for volumes with `REAL`, `ENSEMBLE` and `SOURCE` columns.
* **`csvfile_parameters`:** Aggregated csvfile of parameters for sensitivity information with \
  `REAL`, `ENSEMBLE`, `SENSNAME` and `SENSCASE` columns.
* **`ensembles`:** Which ensembles in `shared_settings` to visualize (not to be used with \
  `csvfile_vol` and `csvfile_parameters`).
* **`volfiles`:**  Key/value pair of csv files when using `ensembles`. \
  E.g. `{geogrid: geogrid--oil.csv}`.
* **`volfolder`:** Optional local folder for the `volfiles`.
* **`response`:** Optional volume response to visualize initially.

---
?> The input files must follow FMU standards.


**Volumetric input**

* [Example of an aggregated file for `csvfile_vol`](https://github.com/equinor/\
webviz-subsurface-testdata/blob/master/aggregated_data/volumes.csv).

* [Example of a file per realization that can be used with `ensembles` and `volfiles`]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/reek_history_match/\
realization-0/iter-0/share/results/volumes/geogrid--oil.csv).

The following columns will be used as available filters, if present:

* `ZONE`
* `REGION`
* `FACIES`
* `LICENSE`
* `SOURCE` (relevant if calculations are done for multiple grids)


Remaining columns are seen as volumetric responses.

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

**Sensitivity input**

The sensitivity information is extracted automatically if `ensembles` is given as input,
as long as `SENSCASE` and `SENSNAME` is found in `parameters.txt`.

An example of an aggregated file to use with `csvfile_parameters`
[can be found here](https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
aggregated_data/parameters.csv)
"""

    FILTERS = ["ZONE", "REGION", "FACIES", "LICENSE"]

    TABLE_STATISTICS = [("Sens Name", {}), ("Sens Case", {})] + table_statistics_base()

    ENSEMBLE_COLUMNS = [
        "REAL",
        "ENSEMBLE",
        "SOURCE",
        "SENSCASE",
        "SENSNAME",
        "SENSTYPE",
        "RUNPATH",
    ]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        csvfile_vol: Path = None,
        csvfile_parameters: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        response: str = "STOIIP_OIL",
    ):

        super().__init__()

        self.csvfile_vol = csvfile_vol if csvfile_vol else None
        self.csvfile_parameters = csvfile_parameters if csvfile_parameters else None

        if csvfile_vol and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_vol" and "csvfile_parameters" or '
                '"ensembles" and "volfiles"'
            )
        if csvfile_vol and csvfile_parameters:
            volumes = read_csv(csvfile_vol)
            parameters = read_csv(csvfile_parameters)
            parameters["SENSTYPE"] = parameters.apply(
                lambda row: find_sens_type(row.SENSCASE), axis=1
            )

        elif ensembles and volfiles:
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.volfiles = volfiles
            self.volfolder = volfolder
            # Extract volumetric dataframe
            volumes = extract_volumes(self.ens_paths, self.volfolder, self.volfiles)
            # Extract realizations and sensitivity information
            parameters = get_realizations(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            )

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_vol" and "csvfile_parameters" or '
                '"ensembles" and "volfiles"'
            )
        self.initial_response = response

        # Merge into one dataframe
        # (TODO: Should raise error if not all ensembles have sensitivity data)
        self.volumes = pd.merge(volumes, parameters, on=["ENSEMBLE", "REAL"])

        # Initialize a tornado plot. Data is added in callback
        self.tornadoplot = TornadoPlot(app, parameters, allow_click=True)
        self.uid = uuid4()
        self.selectors_id = {x: self.uuid(x) for x in self.selectors}
        self.theme = app.webviz_settings["theme"]
        self.set_callbacks(app)

    def add_webvizstore(self):
        return (
            [
                (
                    read_csv,
                    [
                        {"csv_file": self.csvfile_vol},
                        {"csv_file": self.csvfile_parameters},
                    ],
                )
            ]
            if self.csvfile_vol and self.csvfile_parameters
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
                ),
                (
                    get_realizations,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                        }
                    ],
                ),
            ]
        )

    def selector(self, label, id_name, column):
        return html.Div(
            children=html.Label(
                children=[
                    html.Span(f"{label}:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.uuid(id_name),
                        options=[
                            {"label": i, "value": i}
                            for i in list(self.volumes[column].unique())
                        ],
                        clearable=False,
                        value=list(self.volumes[column])[0],
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
        )

    @property
    def tour_steps(self):
        return [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard displaying in place volumetric results "
                    "from a sensitivity study."
                ),
            },
            {
                "id": self.uuid("graph-wrapper"),
                "content": (
                    "Chart showing results for the current selection. "
                    "Different charts and options can be selected from the menu above. "
                    "Different sensitivities can be highlighted by clicking in the tornado plot."
                ),
            },
            {
                "id": self.uuid("table"),
                "content": (
                    "The table shows statistics per sensitivity parameter. "
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
            *self.tornadoplot.tour_steps,
            {
                "id": self.uuid("ensemble"),
                "content": (
                    "If several ensembles are available, the active ensemble "
                    "can be selected here."
                ),
            },
            {
                "id": self.uuid("source"),
                "content": (
                    "If volumes have been calculated for different grids. "
                    "E.g. geogrid and eclipsegrid, the active grid can be selected here."
                ),
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

    @property
    def vol_columns(self):
        """List of all columns in dataframe"""
        return list(self.volumes.columns)

    @property
    def selectors(self):
        """List of available selector columns in dframe"""
        return [x for x in InplaceVolumesOneByOne.FILTERS if x in self.vol_columns]

    @property
    def responses(self):
        """List of available volume responses in dframe"""
        return [
            x
            for x in self.vol_columns
            if x not in self.selectors
            and x not in InplaceVolumesOneByOne.ENSEMBLE_COLUMNS
        ]

    @property
    def plot_selector(self):
        """Radiobuttons to select plot type"""
        return html.Div(
            children=[
                html.Span("Plot type:", style={"font-weight": "bold"}),
                dcc.Dropdown(
                    id=self.uuid("plot-type"),
                    options=[
                        {"label": i, "value": i}
                        for i in [
                            "Per realization",
                            "Per sensitivity name",
                            "Per sensitivity case",
                        ]
                    ],
                    value="Per realization",
                    clearable=False,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        )

    @property
    def response_selector(self):
        """Dropdown to select volumetric response"""
        return html.Div(
            children=html.Label(
                children=[
                    html.Span("Volumetric calculation:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.uuid("response"),
                        options=[
                            {"label": volume_description(i), "value": i}
                            for i in self.responses
                        ],
                        clearable=False,
                        value=self.initial_response
                        if self.initial_response in self.responses
                        else self.responses[0],
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
        )

    @property
    def filter_selectors(self):
        """Dropdowns for dataframe columns that can be filtered on (Zone, Region, etc)"""
        return [
            html.Div(
                children=[
                    html.Details(
                        open=True,
                        children=[
                            html.Summary(selector.lower().capitalize()),
                            wcc.Select(
                                id=self.selectors_id[selector],
                                options=[
                                    {"label": i, "value": i}
                                    for i in list(self.volumes[selector].unique())
                                ],
                                value=list(self.volumes[selector].unique()),
                                multi=True,
                                size=min(20, len(self.volumes[selector].unique())),
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    )
                ]
            )
            for selector in self.selectors
        ]

    @property
    def layout(self):
        """Main layout"""
        return html.Div(
            children=[
                wcc.FlexBox(
                    id=self.uuid("layout"),
                    children=[
                        html.Div(
                            children=[
                                wcc.FlexBox(
                                    children=[
                                        html.Div(
                                            style={"flex": 1},
                                            children=[
                                                self.selector(
                                                    "Ensemble", "ensemble", "ENSEMBLE"
                                                ),
                                                self.selector(
                                                    "Grid source", "source", "SOURCE"
                                                ),
                                                self.response_selector,
                                                self.plot_selector,
                                                html.Span(
                                                    "Filters:",
                                                    style={"font-weight": "bold"},
                                                ),
                                                html.Div(
                                                    id=self.uuid("filters"),
                                                    children=self.filter_selectors,
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            style={"flex": 3},
                                            children=[
                                                html.Div(
                                                    style={"height": "600px"},
                                                    id=self.uuid("graph-wrapper"),
                                                ),
                                                html.Div(
                                                    children=[
                                                        html.Div(
                                                            id=self.uuid(
                                                                "volume_title"
                                                            ),
                                                            style={
                                                                "textAlign": "center"
                                                            },
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
                                )
                            ]
                        ),
                        html.Div(
                            id=self.uuid("tornado-wrapper"),
                            style={"visibility": "visible", "flex": 2},
                            children=[self.tornadoplot.layout],
                        ),
                    ],
                ),
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.tornadoplot.storage_id, "data"),
                Output(self.uuid("table"), "data"),
                Output(self.uuid("table"), "columns"),
            ],
            [
                Input(i, "value")
                for sublist in [
                    [
                        self.uuid("ensemble"),
                        self.uuid("response"),
                        self.uuid("source"),
                    ],
                    list(self.selectors_id.values()),
                ]
                for i in sublist
            ],
        )
        def _render_table_and_tornado(ensemble, response, source, *filters):
            # Filter data
            data = filter_dataframe(
                self.volumes, self.selectors, ensemble, source, filters
            )

            # Table data
            table, columns = calculate_table(data, response)

            # TornadoPlot input
            tornado = json.dumps(
                {
                    "ENSEMBLE": ensemble,
                    "data": data.groupby("REAL")
                    .sum()
                    .reset_index()[["REAL", response]]
                    .values.tolist(),
                    "number_format": "#.4g",
                    "unit": volume_unit(response),
                }
            )
            return tornado, table, columns

        @app.callback(
            [
                Output(self.uuid("graph-wrapper"), "children"),
                Output(self.uuid("volume_title"), "children"),
            ],
            [
                Input(self.tornadoplot.click_id, "data"),
                Input(self.tornadoplot.high_low_storage_id, "data"),
                Input(self.uuid("plot-type"), "value"),
            ],
            [
                State(i, "value")
                for sublist in [
                    [
                        self.uuid("ensemble"),
                        self.uuid("response"),
                        self.uuid("source"),
                    ],
                    list(self.selectors_id.values()),
                ]
                for i in sublist
            ],
        )
        def _render_chart(
            tornado_click,
            high_low_storage,
            plot_type,
            ensemble,
            response,
            source,
            *filters,
        ):
            if dash.callback_context.triggered is None:
                raise PreventUpdate
            ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
            if tornado_click:
                tornado_click = json.loads(tornado_click)
                if (
                    high_low_storage is not None
                    and ctx == self.tornadoplot.high_low_storage_id
                ):
                    # Tornado plot is updated without a click in the plot, updating reals:
                    if tornado_click["sens_name"] in high_low_storage:
                        tornado_click["real_low"] = high_low_storage[
                            tornado_click["sens_name"]
                        ].get("real_low")
                        tornado_click["real_high"] = high_low_storage[
                            tornado_click["sens_name"]
                        ].get("real_high")
                    else:
                        # fallback in a case where chosen sens_name does not exist in updated
                        # tornado plot.
                        # (can this ever occur except when sens_name already is None?)
                        tornado_click["sens_name"] = None
                        tornado_click["real_low"] = []
                        tornado_click["real_high"] = []

            # Filter data
            data = filter_dataframe(
                self.volumes, self.selectors, ensemble, source, filters
            )

            # Volume title:
            volume_title = f"{volume_description(response)} [{volume_unit(response)}]"

            # Make Plotly figure
            layout = {}
            layout.update({"height": 600, "margin": {"l": 100, "b": 100}})
            if plot_type == "Per realization":
                # One bar per realization
                layout.update(
                    {
                        "xaxis": {"title": "Realizations"},
                        "yaxis": {"title": volume_title},
                    }
                )
                plot_data = data.groupby("REAL").sum().reset_index()

                if tornado_click:
                    figure_data = [
                        {
                            "y": plot_data[
                                plot_data["REAL"].isin(tornado_click["real_low"])
                            ][response],
                            "x": plot_data[
                                plot_data["REAL"].isin(tornado_click["real_low"])
                            ]["REAL"],
                            "tickformat": ".4s",
                            "type": "bar",
                            "showlegend": False,
                            "name": "",
                        },
                        {
                            "y": plot_data[
                                plot_data["REAL"].isin(tornado_click["real_high"])
                            ][response],
                            "x": plot_data[
                                plot_data["REAL"].isin(tornado_click["real_high"])
                            ]["REAL"],
                            "tickformat": ".4s",
                            "type": "bar",
                            "showlegend": False,
                            "name": "",
                        },
                        {
                            "y": plot_data[
                                ~plot_data["REAL"].isin(
                                    tornado_click["real_low"]
                                    + tornado_click["real_high"]
                                )
                            ][response],
                            "x": plot_data[
                                ~plot_data["REAL"].isin(
                                    tornado_click["real_low"]
                                    + tornado_click["real_high"]
                                )
                            ]["REAL"],
                            "tickformat": ".4s",
                            "type": "bar",
                            "marker": {"color": "grey"},
                            "showlegend": False,
                            "name": "",
                        },
                    ]
                else:
                    figure_data = [
                        {
                            "y": plot_data[response],
                            "x": plot_data["REAL"],
                            "tickformat": ".4s",
                            "type": "bar",
                            "marker": {"color": "grey"},
                        },
                    ]
                figure = wcc.Graph(
                    config={"displayModeBar": False},
                    id=self.uuid("graph"),
                    figure={
                        "data": figure_data,
                        "layout": self.theme.create_themed_layout(layout),
                    },
                )
            elif plot_type == "Per sensitivity case":
                # One box per sensitivity name
                layout.update(
                    {
                        "title": "Distribution for each sensitivity case",
                        "yaxis": {"title": volume_title},
                    }
                )
                figure = wcc.Graph(
                    config={"displayModeBar": False},
                    id=self.uuid("graph"),
                    figure={
                        "data": [
                            {
                                "y": senscase_df.groupby("REAL")
                                .sum()
                                .reset_index()[response],
                                "name": f"{sensname} ({senscase})",
                                "type": "box",
                            }
                            for sensname, sensname_df in data.groupby(["SENSNAME"])
                            for senscase, senscase_df in sensname_df.groupby(
                                ["SENSCASE"]
                            )
                        ],
                        "layout": self.theme.create_themed_layout(layout),
                    },
                )
            elif plot_type == "Per sensitivity name":
                # One box per sensitivity name
                layout.update(
                    {
                        "title": "Distribution for each sensitivity name",
                        "yaxis": {"title": volume_title},
                    }
                )
                figure = wcc.Graph(
                    config={"displayModeBar": False},
                    id=self.uuid("graph"),
                    figure={
                        "data": [
                            {
                                "y": sensname_df.groupby("REAL")
                                .sum()
                                .reset_index()[response],
                                "name": f"{sensname}",
                                "type": "box",
                            }
                            for sensname, sensname_df in data.groupby(["SENSNAME"])
                        ],
                        "layout": self.theme.create_themed_layout(layout),
                    },
                )
            else:
                # Should not occur unless plot_type options are changed
                figure = html.Div("Invalid plot type")

            return figure, volume_title


def calculate_table(df, response):
    table = []
    for (sensname, senscase), dframe in df.groupby(["SENSNAME", "SENSCASE"]):
        values = dframe.groupby("REAL").sum().reset_index()[response]
        try:
            table.append(
                {
                    "Sens Name": str(sensname),
                    "Sens Case": str(senscase),
                    "Minimum": values.min(),
                    "Maximum": values.max(),
                    "Mean": values.mean(),
                    "Stddev": values.std(),
                    "P10": np.percentile(values, 90),
                    "P90": np.percentile(values, 10),
                }
            )
        except KeyError:
            pass
    columns = [
        {**{"name": i[0], "id": i[0]}, **i[1]}
        for i in InplaceVolumesOneByOne.TABLE_STATISTICS
    ]
    return table, columns


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_dataframe(dframe, columns, ensemble, source, column_values):
    df = dframe.copy()
    if not isinstance(columns, list):
        columns = [columns]
    for filt, col in zip(column_values, columns):
        if isinstance(filt, list):
            df = df.loc[df[col].isin(filt)]
        else:
            df = df.loc[df[col] == filt]
    df = df.loc[df["ENSEMBLE"] == ensemble]
    df = df.loc[df["SOURCE"] == source]
    return df


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)

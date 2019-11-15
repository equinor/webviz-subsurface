import json
from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
from dash_table import DataTable
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from dash.dependencies import Input, Output, State
from webviz_config import WebvizContainerABC
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface.private_containers._tornado_plot import TornadoPlot

from ..datainput import extract_volumes, get_realizations


class InplaceVolumesOneByOne(WebvizContainerABC):
    # pylint: disable=too-many-instance-attributes
    """### InplaceVolumesOneByOne

Visualizes inplace volumetrics related to a FMU ensemble with design matrix.
Input can be given either as aggregated csv files for volumes and sensitivity information,
or as an ensemble name defined in 'container_settings' and volumetric csv files
stored per realizations.

In either case the volumetric csv files must follow FMU standards, that is it must have
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

The sensitivity information is extracted automatically if an ensemble is given as input,
as long as 'SENSCASE' and 'SENSNAME' is found in 'parameters.txt'.
If aggregated csv files are given as input a csv file with the following columns are
required: ENSEMBLE,REAL,SENSCASE,SENSNAME,SENSTYPE,RUNPATH


* `csvfile_vol`: Aggregated csvfile for volumes with 'REAL', 'ENSEMBLE' and 'SOURCE' columns
* `csvfile_reals`: Aggregated csvfile for sensitivity information
* `ensembles`: Which ensembles in `container_settings` to visualize.
* `volfiles`:  Key/value pair of csv files E.g. {geogrid: geogrid--oil.csv}
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

    FILTERS = ["ZONE", "REGION", "FACIES", "LICENSE"]

    TABLE_STATISTICS = [
        "Sens Name",
        "Sens Case",
        "Mean",
        "Stddev",
        "Minimum",
        "P90",
        "P10",
        "Maximum",
    ]

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
        container_settings,
        csvfile_vol: Path = None,
        csvfile_reals: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        response: str = "STOIIP_OIL",
    ):

        self.csvfile_vol = csvfile_vol if csvfile_vol else None
        self.csvfile_reals = csvfile_reals if csvfile_reals else None

        if csvfile_vol and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_vol" and "csvfile_reals" or '
                '"ensembles" and "volfiles"'
            )
        if csvfile_vol and csvfile_reals:
            volumes = read_csv(csvfile_vol)
            realizations = read_csv(csvfile_reals)

        elif ensembles and volfiles:
            self.ens_paths = tuple(
                (ens, container_settings["scratch_ensembles"][ens]) for ens in ensembles
            )
            self.volfiles = tuple(volfiles.items())
            self.volfolder = volfolder
            # Extract volumetric dataframe
            volumes = extract_volumes(self.ens_paths, self.volfolder, self.volfiles)
            # Extract realizations and sensitivity information
            realizations = get_realizations(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            )

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_vol" and "csvfile_reals" or '
                '"ensembles" and "volfiles"'
            )
        self.initial_response = response

        # Merge into one dataframe
        # (TODO: Should raise error if not all ensembles have sensitivity data)
        self.volumes = pd.merge(volumes, realizations, on=["ENSEMBLE", "REAL"])

        # Initialize a tornado plot. Data is added in callback
        self.tornadoplot = TornadoPlot(app, realizations, allow_click=True)
        self.make_uuids()
        self.set_callbacks(app)

    def make_uuids(self):
        uuid = f"{uuid4()}"
        self.graph_wrapper_id = f"graph-wrapper-{uuid}"
        self.plot_type_id = f"plot-type-{uuid}"
        self.graph_id = f"graph-{uuid}"
        self.table_id = f"table-{uuid}"
        self.response_id = f"response-{uuid}"
        self.tornadowrapper_id = f"tornadowrapper-{uuid}"
        self.source_id = f"source-{uuid}"
        self.ensemble_id = f"ensemble-{uuid}"
        self.filter_selectors_id = f"filter-selectors-{uuid}"
        self.selectors_id = {x: f"{x}{uuid}" for x in self.selectors}

    def add_webvizstore(self):
        return (
            [
                (
                    read_csv,
                    [{"csv_file": self.csvfile_vol}, {"csv_file": self.csvfile_reals}],
                )
            ]
            if self.csvfile_vol and self.csvfile_reals
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

    @property
    def tour_steps(self):
        return [
            {
                "id": self.graph_id,
                "content": "The chart shows inplace volumetrics results.",
            },
            {
                "id": self.table_id,
                "content": (
                    "The table shows statistics per sensitivity parameter. "
                    "Rows can be filtered by searching, and sorted by "
                    "clicking on a column header."
                ),
            },
            {
                "id": self.response_id,
                "content": "Select the volumetric calculation to display.",
            },
            {
                "id": self.plot_type_id,
                "content": (
                    "Controls the type of the visualized chart. "
                    "Per realization shows bars per realization, "
                    "while the boxplot shows the range per sensitivity."
                ),
            },
            {
                "id": self.tornadowrapper_id,
                "content": (
                    "Displays tornado plot for the currently selected data. "
                    "Differences references can be set and sensitivities "
                    "smaller than the reference can be filtered out. "
                    "Click on the bar of a sensitivity to highlight the "
                    "relevant realizations in the main chart."
                ),
            },
            {
                "id": self.ensemble_id,
                "content": (
                    "If several ensembles are available, the active ensemble "
                    "can be selected here."
                ),
            },
            {
                "id": self.source_id,
                "content": (
                    "If volumes have been calculated for different grids. "
                    "E.g. geogrid and eclipsegrid, the active grid can be selected here."
                ),
            },
            {
                "id": self.filter_selectors_id,
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
    def ensemble_selector(self):
        """Dropdown to select ensemble"""
        return html.Div(
            style={"paddingBottom": "30px"},
            children=[
                html.Label("Ensemble"),
                dcc.Dropdown(
                    id=self.ensemble_id,
                    options=[
                        {"label": i, "value": i}
                        for i in list(self.volumes["ENSEMBLE"].unique())
                    ],
                    clearable=False,
                    value=list(self.volumes["ENSEMBLE"])[0],
                ),
            ],
        )

    @property
    def plot_selector(self):
        """Radiobuttons to select plot type"""
        return html.Div(
            children=[
                html.Label("Plot Type"),
                dcc.RadioItems(
                    id=self.plot_type_id,
                    options=[
                        {"label": i, "value": i}
                        for i in ["Per Realization", "Box Plot"]
                    ],
                    labelStyle={"display": "inline-block"},
                    value="Per Realization",
                ),
            ]
        )

    @property
    def response_selector(self):
        """Dropdown to select volumetric response"""
        return html.Div(
            style={"paddingLeft": "30px"},
            children=[
                html.Label("Volumetric calculation"),
                dcc.Dropdown(
                    id=self.response_id,
                    style={"width": "75%"},
                    options=[
                        {
                            "label": InplaceVolumesOneByOne.RESPONSES.get(i, i),
                            "value": i,
                        }
                        for i in self.responses
                    ],
                    clearable=False,
                    value=self.initial_response
                    if self.initial_response in self.responses
                    else self.responses[0],
                ),
            ],
        )

    @property
    def source_selector(self):
        """Dropdown to select grid source of volume files"""
        return html.Div(
            style={"paddingBottom": "30px"},
            children=[
                html.Label("Grid source"),
                dcc.Dropdown(
                    id=self.source_id,
                    options=[
                        {"label": i, "value": i}
                        for i in list(self.volumes["SOURCE"].unique())
                    ],
                    clearable=False,
                    value=list(self.volumes["SOURCE"])[0],
                ),
            ],
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
                            dcc.Dropdown(
                                id=self.selectors_id[selector],
                                options=[
                                    {"label": i, "value": i}
                                    for i in list(self.volumes[selector].unique())
                                ],
                                value=list(self.volumes[selector].unique()),
                                multi=True,
                                clearable=False,
                            ),
                        ],
                    )
                ]
            )
            for selector in self.selectors
        ]

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    @property
    def layout(self):
        """Main layout"""
        return html.Div(
            [
                html.Div(
                    style=self.set_grid_layout("1fr 3fr 2fr"),
                    children=[
                        html.Div(
                            children=[
                                self.ensemble_selector,
                                self.source_selector,
                                html.Label("Filters"),
                                html.Div(
                                    id=self.filter_selectors_id,
                                    children=self.filter_selectors,
                                ),
                            ]
                        ),
                        html.Div(
                            children=[
                                html.Div(
                                    style=self.set_grid_layout("2fr 1fr"),
                                    children=[
                                        self.response_selector,
                                        self.plot_selector,
                                    ],
                                ),
                                html.Div(
                                    id=self.graph_wrapper_id, style={"height": "450px"}
                                ),
                                DataTable(
                                    id=self.table_id,
                                    sort_action="native",
                                    filter_action="native",
                                    page_action="native",
                                    page_size=10,
                                    columns=[
                                        {"name": i, "id": i}
                                        for i in InplaceVolumesOneByOne.TABLE_STATISTICS
                                    ],
                                ),
                            ]
                        ),
                        html.Div(
                            id=self.tornadowrapper_id,
                            style={"visibility": "visible"},
                            children=[
                                html.Label(
                                    "Tornado Plot", style={"font-weight": "bold"}
                                ),
                                self.tornadoplot.layout,
                            ],
                        ),
                    ],
                )
            ]
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.graph_wrapper_id, "children"),
                Output(self.tornadoplot.storage_id, "children"),
                Output(self.table_id, "data"),
            ],
            [
                Input(i, "value")
                for sublist in [
                    [
                        self.plot_type_id,
                        self.ensemble_id,
                        self.response_id,
                        self.source_id,
                    ],
                    list(self.selectors_id.values()),
                ]
                for i in sublist
            ],
        )
        def _render_vol_chart(plot_type, ensemble, response, source, *filters):
            """Callback to update graph, tornado and table"""

            # Filter dataframe based on dropdown choices
            data = filter_dataframe(self.volumes, self.selectors, filters)
            data = data.loc[data["ENSEMBLE"] == ensemble]
            data = data.loc[data["SOURCE"] == source]

            # Calculate statistics for table
            table = calculate_table_rows(data, response)

            # Make Plotly figure
            if plot_type == "Per Realization":
                # One bar per realization
                plot_data = data.groupby("REAL").sum().reset_index()
                figure = wcc.Graph(
                    config={"displayModeBar": False},
                    id=self.graph_id,
                    figure={
                        "data": [
                            {
                                "y": plot_data[response],
                                "x": plot_data["REAL"],
                                "marker": {"color": "grey"},
                                "type": "bar",
                            }
                        ],
                        "layout": {
                            "title": "Click on Tornado bar to highlight realizations",
                            "xaxis": {"title": "Realization"},
                        },
                    },
                )
            elif plot_type == "Box Plot":
                # One box per sensitivity name
                figure = wcc.Graph(
                    config={"displayModeBar": False},
                    id=self.graph_id,
                    figure={
                        "data": [
                            {
                                "y": dframe.groupby("REAL")
                                .sum()
                                .reset_index()[response],
                                "name": sensname,
                                "type": "box",
                            }
                            for sensname, dframe in data.groupby(["SENSNAME"])
                        ],
                        "layout": {"title": "Distribution for each sensitivity"},
                    },
                )
            tornado = json.dumps(
                {
                    "ENSEMBLE": ensemble,
                    "data": data.groupby("REAL")
                    .sum()
                    .reset_index()[["REAL", response]]
                    .values.tolist(),
                }
            )

            return figure, tornado, table

        @app.callback(
            Output(self.graph_id, "figure"),
            [Input(self.tornadoplot.click_id, "children")],
            [State(self.plot_type_id, "value"), State(self.graph_id, "figure")],
        )
        def _color_chart(hoverdata, plot_type, figure):
            """Callback to update barchart color on tornado plot click"""
            if not hoverdata or plot_type != "Per Realization":
                return figure
            hoverdata = json.loads(hoverdata)
            reals = figure["data"][0]["x"]
            colors = []
            for real in reals:
                if real in hoverdata["real_low"]:
                    colors.append("rgb(235, 0, 54)")
                elif real in hoverdata["real_high"]:
                    colors.append("rgb(36, 55, 70)")
                else:
                    colors.append("grey")
            figure["data"][0]["marker"] = {"color": colors}
            return figure


def calculate_table_rows(df, response):
    table = []
    for (sensname, senscase), dframe in df.groupby(["SENSNAME", "SENSCASE"]):
        values = dframe.groupby("REAL").sum().reset_index()[response]
        try:
            table.append(
                {
                    "Sens Name": str(sensname),
                    "Sens Case": str(senscase),
                    "Minimum": f"{values.min():.2e}",
                    "Maximum": f"{values.max():.2e}",
                    "Mean": f"{values.mean():.2e}",
                    "Stddev": f"{values.std():.2e}",
                    "P10": f"{np.percentile(values, 90):.2e}",
                    "P90": f"{np.percentile(values, 10):.2e}",
                }
            )
        except KeyError:
            pass
    return table


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

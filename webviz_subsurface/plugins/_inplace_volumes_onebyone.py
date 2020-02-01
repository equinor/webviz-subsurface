import json
from uuid import uuid4
from pathlib import Path

import numpy as np
import pandas as pd
from dash_table import DataTable
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .._private_plugins.tornado_plot import TornadoPlot
from .._datainput.inplace_volumes import extract_volumes
from .._datainput.fmu_input import get_realizations
from .._abbreviations import VOLUME_TERMINOLOGY


class InplaceVolumesOneByOne(WebvizPluginABC):
    # pylint: disable=too-many-instance-attributes
    """### InplaceVolumesOneByOne

Visualizes inplace volumetrics related to a FMU ensemble with design matrix.

Input can be given either as aggregated csv files for volumes and sensitivity information,
or as an ensemble name defined in *shared_settings* and volumetric csv files
stored per realizations.

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

#### Sensitivity input

The sensitivity information is extracted automatically if an ensemble is given as input,
as long as *SENSCASE* and *SENSNAME* is found in 'parameters.txt'.

[Example csv file](
https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/realdata.csv)

* `csvfile_vol`: Aggregated csvfile for volumes with 'REAL', 'ENSEMBLE' and 'SOURCE' columns
* `csvfile_reals`: Aggregated csvfile for sensitivity information
* `ensembles`: Which ensembles in `shared_settings` to visualize.
* `volfiles`:  Key/value pair of csv files E.g. {geogrid: geogrid--oil.csv}
* `volfolder`: Optional local folder for csv files
* `response`: Optional initial visualized volume response

"""

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
        csvfile_vol: Path = None,
        csvfile_reals: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        response: str = "STOIIP_OIL",
    ):

        super().__init__()

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
            self.ens_paths = {
                ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.volfiles = volfiles
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
        self.uid = uuid4()
        self.selectors_id = {x: self.ids(x) for x in self.selectors}
        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

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

    def selector(self, label, id_name, column):
        return html.Div(
            style={"paddingBottom": "30px"},
            children=html.Label(
                children=[
                    html.Span(f"{label}:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids(id_name),
                        options=[
                            {"label": i, "value": i}
                            for i in list(self.volumes[column].unique())
                        ],
                        clearable=False,
                        value=list(self.volumes[column])[0],
                    ),
                ]
            ),
        )

    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": (
                    "Dashboard displaying in place volumetric results "
                    "from a sensitivity study."
                ),
            },
            {
                "id": self.ids("graph"),
                "content": (
                    "Chart showing results for the current selection. "
                    "Different charts and options can be selected from the menu above. "
                    "Different sensitivities can be highlighted by clicking in the tornado plot."
                ),
            },
            {
                "id": self.ids("table"),
                "content": (
                    "The table shows statistics per sensitivity parameter. "
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
            *self.tornadoplot.tour_steps,
            {
                "id": self.ids("ensemble"),
                "content": (
                    "If several ensembles are available, the active ensemble "
                    "can be selected here."
                ),
            },
            {
                "id": self.ids("source"),
                "content": (
                    "If volumes have been calculated for different grids. "
                    "E.g. geogrid and eclipsegrid, the active grid can be selected here."
                ),
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
                dcc.RadioItems(
                    id=self.ids("plot-type"),
                    options=[
                        {"label": i, "value": i}
                        for i in ["Per realization", "Box plot"]
                    ],
                    labelStyle={"display": "inline-block"},
                    value="Per realization",
                ),
            ]
        )

    @property
    def response_selector(self):
        """Dropdown to select volumetric response"""
        return html.Div(
            style={"paddingLeft": "30px"},
            children=html.Label(
                children=[
                    html.Span("Volumetric calculation:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids("response"),
                        style={"width": "75%"},
                        options=[
                            {"label": VOLUME_TERMINOLOGY.get(i, i), "value": i,}
                            for i in self.responses
                        ],
                        clearable=False,
                        value=self.initial_response
                        if self.initial_response in self.responses
                        else self.responses[0],
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
            id=self.ids("layout"),
            children=[
                html.Div(
                    style=self.set_grid_layout("1fr 3fr 2fr"),
                    children=[
                        html.Div(
                            children=[
                                self.selector("Ensemble", "ensemble", "ENSEMBLE"),
                                self.selector("Grid source", "source", "SOURCE"),
                                html.Span("Filters:", style={"font-weight": "bold"}),
                                html.Div(
                                    id=self.ids("filters"),
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
                                    id=self.ids("graph-wrapper"),
                                    style={"height": "450px"},
                                ),
                                DataTable(
                                    id=self.ids("table"),
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
                            id=self.ids("tornado-wrapper"),
                            style={"visibility": "visible"},
                            children=[self.tornadoplot.layout],
                        ),
                    ],
                )
            ],
        )

    def set_callbacks(self, app):
        @app.callback(
            [
                Output(self.ids("graph-wrapper"), "children"),
                Output(self.tornadoplot.storage_id, "children"),
                Output(self.ids("table"), "data"),
            ],
            [
                Input(i, "value")
                for sublist in [
                    [
                        self.ids("plot-type"),
                        self.ids("ensemble"),
                        self.ids("response"),
                        self.ids("source"),
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
            layout = {}
            layout.update(self.plotly_theme["layout"])
            layout.update({"margin": {"l": 100}})
            if plot_type == "Per realization":
                # One bar per realization
                layout.update({"xaxis": {"title": "Realizations"}})
                plot_data = data.groupby("REAL").sum().reset_index()
                figure = wcc.Graph(
                    config={"displayModeBar": False},
                    id=self.ids("graph"),
                    figure={
                        "data": [
                            {
                                "y": plot_data[response],
                                "x": plot_data["REAL"],
                                "marker": {"color": "grey"},
                                "type": "bar",
                            }
                        ],
                        "layout": layout,
                    },
                )
            elif plot_type == "Box plot":
                # One box per sensitivity name
                layout.update({"title": "Distribution for each sensitivity"})
                figure = wcc.Graph(
                    config={"displayModeBar": False},
                    id=self.ids("graph"),
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
                        "layout": layout,
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
            Output(self.ids("graph"), "figure"),
            [Input(self.tornadoplot.click_id, "children")],
            [State(self.ids("plot-type"), "value"), State(self.ids("graph"), "figure")],
        )
        def _color_chart(hoverdata, plot_type, figure):
            """Callback to update barchart color on tornado plot click"""
            if not hoverdata or plot_type != "Per realization":
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

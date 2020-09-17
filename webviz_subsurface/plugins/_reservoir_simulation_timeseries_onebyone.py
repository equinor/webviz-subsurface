from pathlib import Path
from uuid import uuid4
import json

import numpy as np
import pandas as pd
import dash
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
from dash_table import DataTable
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from .._private_plugins.tornado_plot import TornadoPlot
from .._datainput.fmu_input import (
    load_smry,
    get_realizations,
    find_sens_type,
    load_smry_meta,
)
from .._abbreviations.reservoir_simulation import (
    simulation_vector_description,
    simulation_unit_reformat,
    historical_vector,
)
from .._abbreviations.number_formatting import table_statistics_base
from .._utils.simulation_timeseries import (
    set_simulation_line_shape_fallback,
    get_simulation_line_shape,
)

# pylint: disable=too-many-instance-attributes
class ReservoirSimulationTimeSeriesOneByOne(WebvizPluginABC):
    """Visualizes reservoir simulation time series data for sensitivity studies based \
on a design matrix.

A tornado plot can be calculated interactively for each date/vector by selecting a date.
After selecting a date individual sensitivities can be selected to highlight the realizations
run with that sensitivity.

---
**Two main options for input data: Aggregated and read from UNSMRY.**

**Using aggregated data**
* **`csvfile_smry`:** Aggregated `csv` file for volumes with `REAL`, `ENSEMBLE`, `DATE` and \
    vector columns (absolute path or relative to config file).
* **`csvfile_parameters`:** Aggregated `csv` file for sensitivity information with `REAL`, \
    `ENSEMBLE`, `SENSNAME` and `SENSCASE` columns (absolute path or relative to config file).

**Using simulation time series data directly from `UNSMRY` files**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`sampling`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.

**Common optional settings for both input options**
* **`initial_vector`:** Initial vector to display
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as \
    rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are \
    always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).

---
!> It is **strongly recommended** to keep the data frequency to a regular frequency (like \
`monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
(controlled by the `sampling` key). This is because the statistics and fancharts are calculated \
per DATE over all realizations in an ensemble, and the available dates should therefore not \
differ between individual realizations of an ensemble.


**Using aggregated data**

* [Example of csvfile_smry]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/smry.csv).

* [Example of csvfile_parameters]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/parameters.csv).


**Using simulation time series data directly from `.UNSMRY` files**

Time series data are extracted automatically from the `UNSMRY` files in the individual
realizations, using the `fmu-ensemble` library. The `SENSNAME` and `SENSCASE` values are read
directly from the `parameters.txt` files of the individual realizations, assuming that these
exist. If the `SENSCASE` of a realization is `p10_p90`, the sensitivity case is regarded as a
**Monte Carlo** style sensitivity, otherwise the case is evaluated as a **scalar** sensitivity.

?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a \
rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and \
cumulatives are used to decide the line shapes in the plot. Aggregated data may on the other \
speed up the build of the app, as processing of `UNSMRY` files can be slow for large models.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
individual realizations. You should therefore not have more than one `UNSMRY` file in this \
folder, to avoid risk of not extracting the right data.
"""

    ENSEMBLE_COLUMNS = [
        "REAL",
        "ENSEMBLE",
        "DATE",
        "SENSCASE",
        "SENSNAME",
        "SENSTYPE",
        "RUNPATH",
    ]

    TABLE_STAT = [("Sensitivity", {}), ("Case", {})] + table_statistics_base()

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app,
        csvfile_smry: Path = None,
        csvfile_parameters: Path = None,
        ensembles: list = None,
        column_keys: list = None,
        initial_vector=None,
        sampling: str = "monthly",
        line_shape_fallback: str = "linear",
    ):

        super().__init__()

        self.time_index = sampling
        self.column_keys = column_keys
        self.csvfile_smry = csvfile_smry
        self.csvfile_parameters = csvfile_parameters

        if csvfile_smry and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_smry" and "csvfile_parameters" or '
                '"ensembles"'
            )
        if csvfile_smry and csvfile_parameters:
            smry = read_csv(csvfile_smry)
            parameters = read_csv(csvfile_parameters)
            parameters["SENSTYPE"] = parameters.apply(
                lambda row: find_sens_type(row.SENSCASE), axis=1
            )
            self.smry_meta = None

        elif ensembles:
            self.ens_paths = {
                ensemble: app.webviz_settings["shared_settings"]["scratch_ensembles"][
                    ensemble
                ]
                for ensemble in ensembles
            }
            # Extract realizations and sensitivity information
            parameters = get_realizations(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            )
            smry = load_smry(
                ensemble_paths=self.ens_paths,
                ensemble_set_name="EnsembleSet",
                time_index=self.time_index,
                column_keys=self.column_keys,
            )
            self.smry_meta = load_smry_meta(
                ensemble_paths=self.ens_paths,
                ensemble_set_name="EnsembleSet",
                column_keys=self.column_keys,
            )
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_smry" and "csvfile_parameters" or '
                '"ensembles"'
            )

        self.data = pd.merge(smry, parameters, on=["ENSEMBLE", "REAL"])
        self.smry_cols = [
            c
            for c in self.data.columns
            if c not in ReservoirSimulationTimeSeriesOneByOne.ENSEMBLE_COLUMNS
            and not historical_vector(c, self.smry_meta, False) in self.data.columns
        ]
        self.initial_vector = (
            initial_vector
            if initial_vector and initial_vector in self.smry_cols
            else self.smry_cols[0]
        )
        self.line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )
        self.tornadoplot = TornadoPlot(app, parameters, allow_click=True)
        self.uid = uuid4()
        self.theme = app.webviz_settings["theme"]
        self.set_callbacks(app)

    def ids(self, element):
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self):
        return [
            {
                "id": self.ids("layout"),
                "content": (
                    "Dashboard displaying time series from a sensitivity study."
                ),
            },
            {
                "id": self.ids("graph-wrapper"),
                "content": (
                    "Selected time series displayed per realization. "
                    "Click in the plot to calculate tornadoplot for the "
                    "corresponding date, then click on the tornado plot to "
                    "highlight the corresponding sensitivity."
                ),
            },
            {
                "id": self.ids("table"),
                "content": (
                    "Table statistics for all sensitivities for the selected date."
                ),
            },
            *self.tornadoplot.tour_steps,
            {"id": self.ids("vector"), "content": "Select time series"},
            {"id": self.ids("ensemble"), "content": "Select ensemble"},
        ]

    @property
    def ensemble_selector(self):
        """Dropdown to select ensemble"""
        return html.Div(
            style={"paddingBottom": "30px"},
            children=html.Label(
                children=[
                    html.Span("Ensemble:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids("ensemble"),
                        options=[
                            {"label": i, "value": i}
                            for i in list(self.data["ENSEMBLE"].unique())
                        ],
                        clearable=False,
                        value=list(self.data["ENSEMBLE"].unique())[0],
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
        )

    @property
    def smry_selector(self):
        """Dropdown to select ensemble"""
        return html.Div(
            style={"paddingBottom": "30px"},
            children=html.Label(
                children=[
                    html.Span("Time series:", style={"font-weight": "bold"}),
                    dcc.Dropdown(
                        id=self.ids("vector"),
                        options=[
                            {
                                "label": f"{simulation_vector_description(vec)} ({vec})",
                                "value": vec,
                            }
                            for vec in self.smry_cols
                        ],
                        clearable=False,
                        value=self.initial_vector,
                        persistence=True,
                        persistence_type="session",
                    ),
                ]
            ),
        )

    @property
    def initial_date(self):
        df = self.data[self.data["ENSEMBLE"] == self.data["ENSEMBLE"].unique()[0]]
        return df["DATE"].max()

    def add_webvizstore(self):
        return (
            [
                (
                    read_csv,
                    [
                        {"csv_file": self.csvfile_smry},
                        {"csv_file": self.csvfile_parameters},
                    ],
                )
            ]
            if self.csvfile_smry and self.csvfile_parameters
            else [
                (
                    load_smry,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                            "time_index": self.time_index,
                            "column_keys": self.column_keys,
                        }
                    ],
                ),
                (
                    load_smry_meta,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                            "column_keys": self.column_keys,
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
    def layout(self):
        return html.Div(
            children=[
                wcc.FlexBox(
                    id=self.ids("layout"),
                    children=[
                        html.Div(
                            style={"flex": 2},
                            children=[
                                wcc.FlexBox(
                                    children=[
                                        self.ensemble_selector,
                                        self.smry_selector,
                                        dcc.Store(
                                            id=self.ids("date-store"),
                                            storage_type="session",
                                        ),
                                    ],
                                ),
                                wcc.FlexBox(
                                    children=[
                                        html.Div(
                                            id=self.ids("graph-wrapper"),
                                            style={"height": "450px"},
                                            children=wcc.Graph(
                                                id=self.ids("graph"),
                                                clickData={
                                                    "points": [{"x": self.initial_date}]
                                                },
                                            ),
                                        ),
                                    ]
                                ),
                                html.Div(
                                    children=[
                                        html.Div(
                                            id=self.ids("table_title"),
                                            style={"textAlign": "center"},
                                            children="",
                                        ),
                                        DataTable(
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
                        html.Div(
                            style={"flex": 1},
                            id=self.ids("tornado-wrapper"),
                            children=self.tornadoplot.layout,
                        ),
                    ],
                ),
            ]
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app):
        @app.callback(
            [
                # Output(self.ids("date-store"), "children"),
                Output(self.ids("table"), "data"),
                Output(self.ids("table"), "columns"),
                Output(self.ids("table_title"), "children"),
                Output(self.tornadoplot.storage_id, "data"),
            ],
            [
                Input(self.ids("ensemble"), "value"),
                Input(self.ids("graph"), "clickData"),
                Input(self.ids("vector"), "value"),
            ],
        )
        def _render_date(ensemble, clickdata, vector):
            """Store selected date and tornado input. Write statistics
            to table"""
            try:
                date = clickdata["points"][0]["x"]
            except TypeError as exc:
                raise PreventUpdate from exc
            data = filter_ensemble(self.data, ensemble, [vector])
            data = data.loc[data["DATE"].astype(str) == date]
            table_rows, table_columns = calculate_table(data, vector)
            return (
                # json.dumps(f"{date}"),
                table_rows,
                table_columns,
                (
                    f"{simulation_vector_description(vector)} ({vector})"
                    + (
                        ""
                        if get_unit(self.smry_meta, vector) is None
                        else f" [{get_unit(self.smry_meta, vector)}]"
                    )
                ),
                json.dumps(
                    {
                        "ENSEMBLE": ensemble,
                        "data": data[["REAL", vector]].values.tolist(),
                        "number_format": "#.4g",
                        "unit": (
                            ""
                            if get_unit(self.smry_meta, vector) is None
                            else get_unit(self.smry_meta, vector)
                        ),
                    }
                ),
            )

        @app.callback(
            Output(self.ids("graph"), "figure"),
            [
                Input(self.tornadoplot.click_id, "data"),
                Input(self.tornadoplot.high_low_storage_id, "data"),
            ],
            [
                State(self.ids("ensemble"), "value"),
                State(self.ids("vector"), "value"),
                State(self.ids("graph"), "clickData"),
                State(self.ids("graph"), "figure"),
            ],
        )  # pylint: disable=too-many-branches, too-many-locals
        def _render_tornado(
            tornado_click, high_low_storage, ensemble, vector, date_click, figure
        ):
            """Update graph with line coloring, vertical line and title"""
            if dash.callback_context.triggered is None:
                raise PreventUpdate
            ctx = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
            if tornado_click:
                tornado_click = json.loads(tornado_click)
                reset_click = tornado_click["sens_name"] is None
            else:
                reset_click = False

            # Draw initial figure and redraw if ensemble/vector changes
            if ctx in ["", self.tornadoplot.high_low_storage_id] or reset_click:
                if historical_vector(vector, self.smry_meta, True) in self.data.columns:
                    data = filter_ensemble(
                        self.data,
                        ensemble,
                        [vector, historical_vector(vector, self.smry_meta, True)],
                    )
                else:
                    data = filter_ensemble(self.data, ensemble, [vector])
                line_shape = get_simulation_line_shape(
                    line_shape_fallback=self.line_shape_fallback,
                    vector=vector,
                    smry_meta=self.smry_meta,
                )
                traces = [
                    {
                        "type": "line",
                        "marker": {"color": "grey"},
                        "hoverinfo": "x+y+text",
                        "hovertext": f"Real: {r}",
                        "x": df["DATE"],
                        "y": df[vector],
                        "customdata": r,
                        "line": {"shape": line_shape},
                        "meta": {
                            "SENSCASE": df["SENSCASE"].values[0],
                            "SENSTYPE": df["SENSTYPE"].values[0],
                        },
                        "name": ensemble,
                        "legendgroup": ensemble,
                        "showlegend": r == data["REAL"][0],
                    }
                    for r, df in data.groupby(["REAL"])
                ]
                if historical_vector(vector, self.smry_meta, True) in data.columns:
                    hist = data[data["REAL"] == data["REAL"][0]]
                    traces.append(
                        {
                            "type": "line",
                            "x": hist["DATE"],
                            "y": hist[historical_vector(vector, self.smry_meta, True)],
                            "line": {
                                "shape": line_shape,
                                "color": "black",
                                "width": 3,
                            },
                            "name": "History",
                            "legendgroup": "History",
                            "showlegend": True,
                        }
                    )
                # traces[0]["hoverinfo"] = "x"
                figure = {
                    "data": traces,
                    "layout": {"margin": {"t": 60}, "hovermode": "closest"},
                }

            # Update line colors if a sensitivity is selected in tornado
            # pylint: disable=too-many-nested-blocks
            if tornado_click and tornado_click["sens_name"] in high_low_storage:
                if ctx == self.tornadoplot.high_low_storage_id:
                    tornado_click["real_low"] = high_low_storage[
                        tornado_click["sens_name"]
                    ].get("real_low")
                    tornado_click["real_high"] = high_low_storage[
                        tornado_click["sens_name"]
                    ].get("real_high")
                if reset_click:
                    add_legend = True
                    for trace in figure["data"]:
                        if trace["name"] != "History":
                            if add_legend:
                                trace["showlegend"] = True
                                add_legend = False
                            else:
                                trace["showlegend"] = False
                            trace["marker"] = {"color": "grey"}
                            trace["opacity"] = 1
                            trace["name"] = ensemble
                            trace["legendgroup"] = ensemble
                            trace["hoverinfo"] = "all"
                            trace["hovertext"] = f"Real: {trace['customdata']}"

                else:
                    add_legend_low = True
                    add_legend_high = True
                    for trace in figure["data"]:
                        if trace["name"] != "History":
                            if trace["customdata"] in tornado_click["real_low"]:
                                trace["marker"] = {
                                    "color": self.theme.plotly_theme["layout"][
                                        "colorway"
                                    ][0]
                                }
                                trace["opacity"] = 1
                                trace["legendgroup"] = "real_low"
                                trace["hoverinfo"] = "all"
                                trace["name"] = (
                                    "Below ref"
                                    if trace["meta"]["SENSTYPE"] == "mc"
                                    else trace["meta"]["SENSCASE"]
                                )
                                if add_legend_low:
                                    add_legend_low = False
                                    trace["showlegend"] = True
                                else:
                                    trace["showlegend"] = False
                            elif trace["customdata"] in tornado_click["real_high"]:
                                trace["marker"] = {
                                    "color": self.theme.plotly_theme["layout"][
                                        "colorway"
                                    ][1]
                                }
                                trace["opacity"] = 1
                                trace["legendgroup"] = "real_high"
                                trace["hoverinfo"] = "all"
                                trace["name"] = (
                                    "Above ref"
                                    if trace["meta"]["SENSTYPE"] == "mc"
                                    else trace["meta"]["SENSCASE"]
                                )
                                if add_legend_high:
                                    add_legend_high = False
                                    trace["showlegend"] = True
                                else:
                                    trace["showlegend"] = False
                            else:
                                trace["marker"] = {"color": "lightgrey"}
                                trace["opacity"] = 0.02
                                trace["showlegend"] = False
                                trace["hoverinfo"] = "skip"

            date = date_click["points"][0]["x"]
            if figure is None:
                raise PreventUpdate
            ymin = min([min(trace["y"]) for trace in figure["data"]])
            ymax = max([max(trace["y"]) for trace in figure["data"]])
            figure["layout"]["shapes"] = [
                {"type": "line", "x0": date, "x1": date, "y0": ymin, "y1": ymax}
            ]
            figure["layout"]["title"] = (
                f"Date: {date}, "
                f"Sensitivity: {tornado_click['sens_name'] if tornado_click else None}"
            )
            figure["layout"]["yaxis"] = {
                "title": f"{simulation_vector_description(vector)} ({vector})"
                + (
                    ""
                    if get_unit(self.smry_meta, vector) is None
                    else f" [{get_unit(self.smry_meta, vector)}]"
                )
            }
            figure["layout"]["legend"] = {
                "orientation": "h",
                # "traceorder": "reversed",
                "y": 1.1,
                "x": 1,
                "xanchor": "right",
            }
            figure["layout"] = self.theme.create_themed_layout(figure["layout"])
            return figure


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_table(df, vector):
    table = []
    for (sensname, senscase), dframe in df.groupby(["SENSNAME", "SENSCASE"]):
        values = dframe[vector]
        try:
            table.append(
                {
                    "Sensitivity": str(sensname),
                    "Case": str(senscase),
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
        for i in ReservoirSimulationTimeSeriesOneByOne.TABLE_STAT
    ]
    return table, columns


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_ensemble(data, ensemble, vector):
    return data.loc[data["ENSEMBLE"] == ensemble][
        ["DATE", "REAL", "SENSCASE", "SENSNAME", "SENSTYPE"] + vector
    ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_unit(smry_meta, vec):
    return None if smry_meta is None else simulation_unit_reformat(smry_meta.unit[vec])

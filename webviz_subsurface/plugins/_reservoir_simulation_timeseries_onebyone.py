import datetime
import json
from pathlib import Path
from typing import Callable, List, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._components import TornadoWidget
from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)

from .._abbreviations.number_formatting import table_statistics_base
from .._abbreviations.reservoir_simulation import (
    historical_vector,
    simulation_unit_reformat,
    simulation_vector_description,
)
from .._datainput.fmu_input import find_sens_type, get_realizations
from .._utils.simulation_timeseries import (
    get_simulation_line_shape,
    set_simulation_line_shape_fallback,
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

    TABLE_STAT: List[Tuple[str, dict]] = [
        ("Sensitivity", {}),
        ("Case", {}),
    ] + table_statistics_base()

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        csvfile_smry: Path = None,
        csvfile_parameters: Path = None,
        ensembles: list = None,
        column_keys: list = None,
        initial_vector: str = None,
        sampling: str = "monthly",
        line_shape_fallback: str = "linear",
    ) -> None:

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
            self.smry = read_csv(csvfile_smry)
            self.parameters = read_csv(csvfile_parameters)
            self.parameters["SENSTYPE"] = self.parameters.apply(
                lambda row: find_sens_type(row.SENSCASE), axis=1
            )
            self.smry_meta = None

        elif ensembles:
            self.ens_paths = {
                ensemble: webviz_settings.shared_settings["scratch_ensembles"][ensemble]
                for ensemble in ensembles
            }
            self.emodel: EnsembleSetModel = (
                caching_ensemble_set_model_factory.get_or_create_model(
                    ensemble_paths=self.ens_paths,
                    time_index=self.time_index,
                    column_keys=self.column_keys,
                )
            )
            self.smry = self.emodel.get_or_load_smry_cached()
            self.smry_meta = self.emodel.load_smry_meta()

            # Extract realizations and sensitivity information
            self.parameters = get_realizations(
                ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
            )
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_smry" and "csvfile_parameters" or '
                '"ensembles"'
            )
        self.smry_cols = [
            c
            for c in self.smry.columns
            if c not in ReservoirSimulationTimeSeriesOneByOne.ENSEMBLE_COLUMNS
            and historical_vector(c, self.smry_meta, False) not in self.smry.columns
        ]
        self.initial_vector = (
            initial_vector
            if initial_vector and initial_vector in self.smry_cols
            else self.smry_cols[0]
        )
        self.ensembles = list(self.parameters["ENSEMBLE"].unique())
        self.line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )
        self.tornadoplot = TornadoWidget(
            app, webviz_settings, self.parameters, allow_click=True
        )
        self.uid = uuid4()
        self.theme = webviz_settings.theme
        self.set_callbacks(app)

    def ids(self, element: str) -> str:
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    @property
    def tour_steps(self) -> List[dict]:
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
    def ensemble_selector(self) -> html.Div:
        """Dropdown to select ensemble"""
        return wcc.Dropdown(
            label="Ensemble",
            id=self.ids("ensemble"),
            options=[{"label": i, "value": i} for i in self.ensembles],
            clearable=False,
            value=self.ensembles[0],
        )

    @property
    def smry_selector(self) -> html.Div:
        """Dropdown to select ensemble"""
        return wcc.Dropdown(
            label="Time series",
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
        )

    @property
    def initial_date(self) -> datetime.date:
        df = self.smry[["ENSEMBLE", "DATE"]]
        return df.loc[df["ENSEMBLE"] == df["ENSEMBLE"].unique()[0]]["DATE"].max()

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
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
            else self.emodel.webvizstore
            + [
                (
                    get_realizations,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                        }
                    ],
                )
            ]
        )

    @property
    def layout(self) -> html.Div:
        return wcc.FlexBox(
            id=self.ids("layout"),
            children=[
                wcc.FlexColumn(
                    flex=1,
                    children=wcc.Frame(
                        style={"height": "90vh"},
                        children=[
                            wcc.Selectors(
                                label="Selectors",
                                children=[self.ensemble_selector, self.smry_selector],
                            ),
                            dcc.Store(
                                id=self.ids("date-store"),
                                storage_type="session",
                            ),
                        ],
                    ),
                ),
                wcc.FlexColumn(
                    flex=3,
                    children=wcc.Frame(
                        style={"height": "90vh"},
                        color="white",
                        highlight=False,
                        children=[
                            html.Div(
                                id=self.ids("graph-wrapper"),
                                style={"height": "450px"},
                                children=wcc.Graph(
                                    id=self.ids("graph"),
                                    clickData={"points": [{"x": self.initial_date}]},
                                ),
                            ),
                            html.Div(
                                children=[
                                    html.Div(
                                        id=self.ids("table_title"),
                                        style={"textAlign": "center"},
                                        children="",
                                    ),
                                    html.Div(
                                        style={"fontSize": "15px"},
                                        children=dash_table.DataTable(
                                            id=self.ids("table"),
                                            sort_action="native",
                                            filter_action="native",
                                            page_action="native",
                                            page_size=10,
                                        ),
                                    ),
                                ],
                            ),
                        ],
                    ),
                ),
                wcc.FlexColumn(
                    flex=3,
                    children=wcc.Frame(
                        style={"height": "90vh"},
                        color="white",
                        highlight=False,
                        id=self.ids("tornado-wrapper"),
                        children=self.tornadoplot.layout,
                    ),
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app: Dash) -> None:
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
        def _render_date(
            ensemble: str, clickdata: dict, vector: str
        ) -> Tuple[list, list, str, str]:
            """Store selected date and tornado input. Write statistics
            to table"""
            try:
                date = clickdata["points"][0]["x"]
            except TypeError as exc:
                raise PreventUpdate from exc
            data = filter_ensemble(self.smry, self.parameters, ensemble, [vector])
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
        )
        def _render_tornado(  # pylint: disable=too-many-branches, too-many-locals
            tornado_click_data_str: Union[str, None],
            high_low_storage: dict,
            ensemble: str,
            vector: str,
            date_click: dict,
            figure: dict,
        ) -> dict:
            """Update graph with line coloring, vertical line and title"""
            if callback_context.triggered is None:
                raise PreventUpdate
            ctx = callback_context.triggered[0]["prop_id"].split(".")[0]

            tornado_click: Union[dict, None] = (
                json.loads(tornado_click_data_str) if tornado_click_data_str else None
            )
            if tornado_click:
                reset_click = tornado_click["sens_name"] is None
            else:
                reset_click = False

            # Draw initial figure and redraw if ensemble/vector changes
            if ctx in ["", self.tornadoplot.high_low_storage_id] or reset_click:
                vectors = [vector]
                historical_vector_name = historical_vector(vector, self.smry_meta, True)

                if (
                    historical_vector_name is not None
                    and historical_vector_name in self.smry.columns
                ):
                    vectors.append(historical_vector_name)
                data = filter_ensemble(
                    self.smry,
                    self.parameters,
                    ensemble,
                    vectors,
                )

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
                ),
                "uirevision": vector,
            }
            figure["layout"]["xaxis"] = {"uirevision": "locked"}
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
def calculate_table(df: pd.DataFrame, vector: str) -> Tuple[List[dict], List[dict]]:
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


def filter_ensemble(
    smry: pd.DataFrame, parameters: pd.DataFrame, ensemble: str, vector: List[str]
) -> pd.DataFrame:
    smry_columns = ["DATE", "REAL"] + vector
    parameter_columns = ["REAL", "SENSCASE", "SENSNAME", "SENSTYPE"]
    return pd.merge(
        smry[smry_columns + ["ENSEMBLE"]].loc[smry["ENSEMBLE"] == ensemble][
            smry_columns
        ],
        parameters[parameter_columns + ["ENSEMBLE"]].loc[
            parameters["ENSEMBLE"] == ensemble
        ][parameter_columns],
        on=["REAL"],
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_unit(smry_meta: Union[pd.DataFrame, None], vec: str) -> Union[str, None]:
    return None if smry_meta is None else simulation_unit_reformat(smry_meta.unit[vec])

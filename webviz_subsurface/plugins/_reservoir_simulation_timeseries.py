# pylint: disable=too-many-lines
import sys
from pathlib import Path
import json

import pandas as pd
from plotly.subplots import make_subplots
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.webviz_store import webvizstore
from webviz_config.common_cache import CACHE

from .._datainput.fmu_input import load_smry, load_smry_meta
from .._abbreviations.reservoir_simulation import (
    simulation_vector_description,
    simulation_unit_reformat,
    historical_vector,
)
from .._utils.simulation_timeseries import (
    set_simulation_line_shape_fallback,
    get_simulation_line_shape,
    calc_series_statistics,
    add_fanchart_traces,
    render_hovertemplate,
    date_to_interval_conversion,
    check_and_format_observations,
)
from .._utils.unique_theming import unique_colors
from .._datainput.from_timeseries_cumulatives import (
    calc_from_cumulatives,
    rename_vec_from_cum,
)


class ReservoirSimulationTimeSeries(WebvizPluginABC):
    """Visualizes reservoir simulation time series data for FMU ensembles.

**Features**
* Visualization of realization time series as line charts.
* Visualization of ensemble time series statistics as fan charts.
* Visualization of single date ensemble statistics as histograms.
* Calculation and visualization of delta ensembles.
* Calculation and visualization of average rates and cumulatives over a specified time interval.
* Download of visualized data to csv files (except histogram data).

---
**Two main options for input data: Aggregated and read from UNSMRY.**

**Using aggregated data**
* **`csvfile`:** Aggregated csv file with `REAL`, `ENSEMBLE`, \
    `DATE` and vector columns.

**Using simulation time series data directly from `UNSMRY` files**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`sampling`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.

**Common optional settings for both input options**
* **`obsfile`**: File with observations to plot together with the relevant time series. \
(absolute path or relative to config file).
* **`options`:** Options to initialize plots with:
    * `vector1` : First vector to display
    * `vector2` : Second vector to display
    * `vector3` : Third vector to display
    * `visualization` : `realizations`, `statistics` or `statistics_hist`
    * `date` : Date to show in histograms
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as \
    rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are \
    always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).

---

?> Vectors that are identified as historical vectors (e.g. FOPTH is the history of FOPT) will \
be plotted together with their non-historical counterparts as reference lines, and they are \
therefore not selectable as vectors to plot initially.

?> The `obsfile` is a common (optional) file for all ensembles, which currently has to be made \
manually. [An example of the format can be found here]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/\
reek_history_match/share/observations/observations.yml).

!> It is **strongly recommended** to keep the data frequency to a regular frequency (like \
`monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
(controlled by the `sampling` key). This is because the statistics and fancharts are calculated \
per DATE over all realizations in an ensemble, and the available dates should therefore not \
differ between individual realizations of an ensemble.

**Using aggregated data**

The `csvfile` must have columns `ENSEMBLE`, `REAL` and `DATE` in addition to the individual
vectors.
* [Example of aggregated file]\
(https://github.com/equinor/webviz-subsurface-testdata/blob/master/aggregated_data/smry.csv).

**Using simulation time series data directly from `.UNSMRY` files**

Vectors are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a \
rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and \
cumulatives are used to decide the line shapes in the plot. Aggregated data may on the other \
speed up the build of the app, as processing of `UNSMRY` files can be slow for large models. \
Using this method is required to use the average rate and interval cumulative functionalities, \
as they require identification of vectors that are cumulatives.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
individual realizations. You should therefore not have more than one `UNSMRY` file in this \
folder, to avoid risk of not extracting the right data.
"""

    ENSEMBLE_COLUMNS = ["REAL", "ENSEMBLE", "DATE"]
    # pylint:disable=too-many-arguments
    def __init__(
        self,
        app,
        csvfile: Path = None,
        ensembles: list = None,
        obsfile: Path = None,
        column_keys: list = None,
        sampling: str = "monthly",
        options: dict = None,
        line_shape_fallback: str = "linear",
    ):

        super().__init__()

        self.csvfile = csvfile
        self.obsfile = obsfile
        self.time_index = sampling
        self.column_keys = column_keys
        if csvfile and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )
        self.observations = {}
        if obsfile:
            self.observations = check_and_format_observations(get_path(self.obsfile))

        if csvfile:
            self.smry = read_csv(csvfile)
            self.smry_meta = None
            # Check of time_index for data to use in resampling. Quite naive as it only checks for
            # unique values of the DATE column, and not per realization.
            #
            # Currently not necessary as we don't allow resampling for average rates and intervals
            # unless we have metadata, which csvfile input currently doesn't support.
            # See: https://github.com/equinor/webviz-subsurface/issues/402
            self.time_index = pd.infer_freq(
                sorted(pd.to_datetime(self.smry["DATE"]).unique())
            )
        elif ensembles:
            self.ens_paths = {
                ensemble: app.webviz_settings["shared_settings"]["scratch_ensembles"][
                    ensemble
                ]
                for ensemble in ensembles
            }
            self.smry = load_smry(
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
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )
        if any([col.startswith(("AVG_", "INTVL_")) for col in self.smry.columns]):
            raise ValueError(
                "Your data set includes time series vectors which have names starting with"
                "'AVG_' and/or 'INTVL_'. These prefixes are not allowed, as they are used"
                "internally in the plugin."
            )
        self.smry_cols = [
            c
            for c in self.smry.columns
            if c not in ReservoirSimulationTimeSeries.ENSEMBLE_COLUMNS
            and not historical_vector(c, self.smry_meta, False) in self.smry.columns
        ]

        self.dropdown_options = []
        for vec in self.smry_cols:
            self.dropdown_options.append(
                {"label": f"{simulation_vector_description(vec)} ({vec})", "value": vec}
            )
            if (
                self.smry_meta is not None
                and self.smry_meta.is_total[vec]
                and self.time_index is not None
            ):
                # Get the likely name for equivalent rate vector and make dropdown options.
                # Requires that the time_index was either defined or possible to infer.
                avgrate_vec = rename_vec_from_cum(vector=vec, as_rate=True)
                interval_vec = rename_vec_from_cum(vector=vec, as_rate=False)
                self.dropdown_options.append(
                    {
                        "label": f"{simulation_vector_description(avgrate_vec)} ({avgrate_vec})",
                        "value": avgrate_vec,
                    }
                )
                self.dropdown_options.append(
                    {
                        "label": f"{simulation_vector_description(interval_vec)} ({interval_vec})",
                        "value": interval_vec,
                    }
                )

        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        self.theme = app.webviz_settings["theme"]
        self.plot_options = options if options else {}
        self.plot_options["date"] = (
            str(self.plot_options.get("date"))
            if self.plot_options.get("date")
            else None
        )
        self.line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )
        # Check if initially plotted vectors exist in data, raise ValueError if not.
        missing_vectors = [
            value
            for key, value in self.plot_options.items()
            if key in ["vector1", "vector2", "vector3"] and value not in self.smry_cols
        ]
        if missing_vectors:
            raise ValueError(
                f"Cannot find: {', '.join(missing_vectors)} to plot initially in "
                "ReservoirSimulationTimeSeries. Check that the vectors exist in your data, and "
                "that they are not missing in a non-default column_keys list in the yaml config "
                "file."
            )
        self.allow_delta = len(self.ensembles) > 1
        self.set_callbacks(app)

    @property
    def ens_colors(self):
        return unique_colors(self.ensembles, self.theme)

    @property
    def tour_steps(self):
        return [
            {
                "id": self.uuid("layout"),
                "content": "Dashboard displaying reservoir simulation time series.",
            },
            {
                "id": self.uuid("graph"),
                "content": (
                    "Visualization of selected time series. "
                    "Different options can be set in the menu to the left."
                ),
            },
            {
                "id": self.uuid("ensemble"),
                "content": (
                    "Display time series from one or several ensembles. "
                    "Different ensembles will be overlain in the same plot."
                ),
            },
            {
                "id": self.uuid("vectors"),
                "content": (
                    "Display up to three different time series. "
                    "Each time series will be visualized in a separate plot. "
                    "Vectors prefixed with AVG_ and INTVL_ are calculated in the fly "
                    "from cumulative vectors, providing average rates and interval cumulatives "
                    "over a time interval that can be defined in the menu."
                ),
            },
            {
                "id": self.uuid("visualization"),
                "content": (
                    "Choose between different visualizations. 1. Show time series as "
                    "individual lines per realization. 2. Show statistical fanchart per "
                    "ensemble. 3. Show statistical fanchart per ensemble and histogram "
                    "per date. Select a data by clicking in the plot."
                ),
            },
            {
                "id": self.uuid("cum_interval"),
                "content": (
                    "Defines the time interval the average rates (prefixed AVG_) and interval "
                    "cumulatives (prefixed INTVL_) are calculated over. Disabled unless at least "
                    "one time series dependent on the interval setting is chosen."
                    "The option might be completely hidden if the data input does not support "
                    "calculation from cumulatives."
                ),
            },
        ]

    @staticmethod
    def set_grid_layout(columns, padding=0):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
            "padding": f"{padding}px",
        }

    @property
    def time_interval_options(self):
        if self.time_index == "daily":
            return ["daily", "monthly", "yearly"]
        if self.time_index == "monthly":
            return ["monthly", "yearly"]
        if self.time_index == "yearly":
            return ["yearly"]
        return []

    @property
    def delta_layout(self):
        show_delta = "block" if self.allow_delta else "none"
        return html.Div(
            children=[
                html.Div(
                    style={"display": show_delta},
                    children=html.Label(
                        children=[
                            html.Span("Mode:", style={"font-weight": "bold"}),
                            dcc.RadioItems(
                                id=self.uuid("mode"),
                                style={"marginBottom": "25px"},
                                options=[
                                    {
                                        "label": "Individual ensembles",
                                        "value": "ensembles",
                                    },
                                    {
                                        "label": "Delta between ensembles",
                                        "value": "delta_ensembles",
                                    },
                                ],
                                value="ensembles",
                                persistence=True,
                                persistence_type="session",
                            ),
                        ]
                    ),
                ),
                html.Div(
                    id=self.uuid("show_ensembles"),
                    children=html.Label(
                        children=[
                            html.Span(
                                "Selected ensembles:", style={"font-weight": "bold"}
                            ),
                            dcc.Dropdown(
                                id=self.uuid("ensemble"),
                                clearable=False,
                                multi=True,
                                options=[
                                    {"label": i, "value": i} for i in self.ensembles
                                ],
                                value=self.ensembles[0],
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                ),
                html.Div(
                    id=self.uuid("calc_delta"),
                    style={"display": "none"},
                    children=[
                        html.Span(
                            "Selected ensemble delta (A-B):",
                            style={"font-weight": "bold"},
                        ),
                        html.Div(
                            style=self.set_grid_layout("1fr 1fr"),
                            children=[
                                html.Div(
                                    [
                                        html.Label(
                                            style={"fontSize": "12px"},
                                            children="Ensemble A",
                                        ),
                                        dcc.Dropdown(
                                            id=self.uuid("base_ens"),
                                            clearable=False,
                                            options=[
                                                {"label": i, "value": i}
                                                for i in self.ensembles
                                            ],
                                            value=self.ensembles[0],
                                            persistence=True,
                                            persistence_type="session",
                                        ),
                                    ]
                                ),
                                html.Div(
                                    [
                                        html.Label(
                                            style={"fontSize": "12px"},
                                            children="Ensemble B",
                                        ),
                                        dcc.Dropdown(
                                            id=self.uuid("delta_ens"),
                                            clearable=False,
                                            options=[
                                                {"label": i, "value": i}
                                                for i in self.ensembles
                                            ],
                                            value=self.ensembles[-1],
                                            persistence=True,
                                            persistence_type="session",
                                        ),
                                    ]
                                ),
                            ],
                        ),
                    ],
                ),
            ]
        )

    @property
    def from_cumulatives_layout(self):
        return html.Div(
            style=(
                {"marginTop": "25px", "display": "block"}
                if len(self.time_interval_options) > 0 and self.smry_meta is not None
                else {"display": "none"}
            ),
            children=[
                html.Span(
                    "Calculated from cumulatives:",
                    style={"font-weight": "bold"},
                ),
                html.Div(
                    "Average (AVG_) and interval (INTVL_) time series",
                    style={"font-style": "italic", "font-size": "0.75em"},
                ),
                html.Div(
                    dcc.RadioItems(
                        id=self.uuid("cum_interval"),
                        options=[
                            {
                                "label": (f"{i.lower().capitalize()}"),
                                "value": i,
                                "disabled": False,
                            }
                            for i in self.time_interval_options
                        ],
                        value=self.time_index,
                        persistence=True,
                        persistence_type="session",
                    ),
                ),
            ],
        )

    @property
    def layout(self):
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                html.Div(
                    style={"flex": 1},
                    children=[
                        self.delta_layout,
                        html.Div(
                            id=self.uuid("vectors"),
                            style={"marginTop": "25px"},
                            children=[
                                html.Span(
                                    "Time series:", style={"font-weight": "bold"}
                                ),
                                dcc.Dropdown(
                                    style={
                                        "marginTop": "5px",
                                        "marginBottom": "5px",
                                        "fontSize": ".95em",
                                    },
                                    optionHeight=55,
                                    id=self.uuid("vector1"),
                                    clearable=False,
                                    multi=False,
                                    options=self.dropdown_options,
                                    value=self.plot_options.get(
                                        "vector1", self.smry_cols[0]
                                    ),
                                    persistence=True,
                                    persistence_type="session",
                                ),
                                dcc.Dropdown(
                                    style={"marginBottom": "5px", "fontSize": ".95em"},
                                    optionHeight=55,
                                    id=self.uuid("vector2"),
                                    clearable=True,
                                    multi=False,
                                    placeholder="Add additional series",
                                    options=self.dropdown_options,
                                    value=self.plot_options.get("vector2", None),
                                    persistence=True,
                                    persistence_type="session",
                                ),
                                dcc.Dropdown(
                                    style={"fontSize": ".95em"},
                                    optionHeight=55,
                                    id=self.uuid("vector3"),
                                    clearable=True,
                                    multi=False,
                                    placeholder="Add additional series",
                                    options=self.dropdown_options,
                                    value=self.plot_options.get("vector3", None),
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
                        ),
                        html.Div(
                            id=self.uuid("visualization"),
                            style={"marginTop": "25px"},
                            children=[
                                html.Span(
                                    "Visualization:", style={"font-weight": "bold"}
                                ),
                                dcc.RadioItems(
                                    id=self.uuid("statistics"),
                                    options=[
                                        {
                                            "label": "Individual realizations",
                                            "value": "realizations",
                                        },
                                        {
                                            "label": "Statistical fanchart",
                                            "value": "statistics",
                                        },
                                        {
                                            "label": "Statistical fanchart and histogram",
                                            "value": "statistics_hist",
                                        },
                                    ],
                                    value=self.plot_options.get(
                                        "visualization", "statistics"
                                    ),
                                    persistence=True,
                                    persistence_type="session",
                                ),
                            ],
                        ),
                        self.from_cumulatives_layout,
                    ],
                ),
                html.Div(
                    style={"flex": 3},
                    children=[
                        html.Div(
                            children=wcc.Graph(
                                id=self.uuid("graph"),
                            ),
                        ),
                        dcc.Store(
                            id=self.uuid("date"),
                            storage_type="session",
                            data=json.dumps(self.plot_options.get("date", None)),
                        ),
                    ],
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("graph"), "figure"),
            [
                Input(self.uuid("vector1"), "value"),
                Input(self.uuid("vector2"), "value"),
                Input(self.uuid("vector3"), "value"),
                Input(self.uuid("ensemble"), "value"),
                Input(self.uuid("mode"), "value"),
                Input(self.uuid("base_ens"), "value"),
                Input(self.uuid("delta_ens"), "value"),
                Input(self.uuid("statistics"), "value"),
                Input(self.uuid("cum_interval"), "value"),
                Input(self.uuid("date"), "data"),
            ],
        )
        # pylint: disable=too-many-instance-attributes, too-many-arguments, too-many-locals, too-many-branches
        def _update_graph(
            vector1,
            vector2,
            vector3,
            ensembles,
            calc_mode,
            base_ens,
            delta_ens,
            visualization,
            cum_interval,
            stored_date,
        ):
            """Callback to update all graphs based on selections"""

            if calc_mode not in ["ensembles", "delta_ensembles"]:
                raise PreventUpdate

            # Combine selected vectors
            vectors = [vector1]
            if vector2:
                vectors.append(vector2)
            if vector3:
                vectors.append(vector3)

            # Ensure selected ensembles is a list and prevent update if invalid calc_mode
            if calc_mode == "delta_ensembles":
                ensembles = [base_ens, delta_ens]
            elif calc_mode == "ensembles":
                ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
            else:
                raise PreventUpdate

            # Retrieve previous/current selected date
            date = json.loads(stored_date) if stored_date else None

            # Titles for subplots
            titles = []
            for vec in vectors:
                if sys.version_info >= (3, 9):
                    unit_vec = vec.removeprefix("AVG_").removeprefix("INTVL_")
                else:
                    unit_vec = (
                        vec[4:]
                        if vec.startswith("AVG_")
                        else (vec[6:] if vec.startswith("INTVL_") else vec)
                    )
                if self.smry_meta is None:
                    titles.append(simulation_vector_description(vec))
                else:
                    titles.append(
                        f"{simulation_vector_description(vec)}"
                        f" [{simulation_unit_reformat(self.smry_meta.unit[unit_vec])}]"
                    )
                if visualization == "statistics_hist":
                    titles.append(
                        date_to_interval_conversion(
                            date=date, vector=vec, interval=cum_interval, as_date=False
                        )
                    )

            # Make a plotly subplot figure
            fig = make_subplots(
                rows=len(vectors),
                cols=2 if visualization == "statistics_hist" else 1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                subplot_titles=titles,
            )

            # Loop through each vector and calculate relevant plot
            legends = []
            dfs = calculate_vector_dataframes(
                smry=self.smry,
                smry_meta=self.smry_meta,
                ensembles=ensembles,
                vectors=vectors,
                calc_mode=calc_mode,
                visualization=visualization,
                time_index=self.time_index,
                cum_interval=cum_interval,
            )
            for i, vector in enumerate(vectors):
                if dfs[vector]["data"].empty:
                    continue
                line_shape = get_simulation_line_shape(
                    line_shape_fallback=self.line_shape_fallback,
                    vector=vector,
                    smry_meta=self.smry_meta,
                )
                if visualization in ["statistics", "statistics_hist"]:
                    traces = add_statistic_traces(
                        dfs[vector]["stat"],
                        vector,
                        colors=self.ens_colors,
                        line_shape=line_shape,
                        interval=cum_interval,
                    )
                    if visualization == "statistics_hist":
                        histdata = add_histogram_traces(
                            dfs[vector]["data"],
                            vector,
                            date=date,
                            colors=self.ens_colors,
                            interval=cum_interval,
                        )
                        for trace in histdata:
                            fig.add_trace(trace, i + 1, 2)
                elif visualization == "realizations":
                    traces = add_realization_traces(
                        dfs[vector]["data"],
                        vector,
                        colors=self.ens_colors,
                        line_shape=line_shape,
                        interval=cum_interval,
                    )
                else:
                    raise PreventUpdate

                if (
                    historical_vector(vector=vector, smry_meta=self.smry_meta)
                    in dfs[vector]["data"].columns
                ):
                    traces.append(
                        add_history_trace(
                            dfs[vector]["data"],
                            historical_vector(vector=vector, smry_meta=self.smry_meta),
                            line_shape,
                        )
                    )

                # Remove unwanted legends(only keep one for each ensemble)
                for trace in traces:
                    if trace.get("showlegend"):
                        if trace.get("legendgroup") in legends:
                            trace["showlegend"] = False
                        else:
                            legends.append(trace.get("legendgroup"))
                    fig.add_trace(trace, i + 1, 1)
                # Add observations
                if calc_mode != "delta_ensembles" and self.observations.get(vector):
                    for trace in add_observation_trace(self.observations.get(vector)):
                        fig.add_trace(trace, i + 1, 1)

            fig = fig.to_dict()
            fig["layout"].update(
                height=800,
                margin={"t": 20, "b": 0},
                barmode="overlay",
                bargap=0.01,
                bargroupgap=0.2,
            )
            fig["layout"] = self.theme.create_themed_layout(fig["layout"])

            if visualization == "statistics_hist":
                # Remove linked x-axis for histograms
                if "xaxis2" in fig["layout"]:
                    fig["layout"]["xaxis2"]["matches"] = None
                    fig["layout"]["xaxis2"]["showticklabels"] = True
                if "xaxis4" in fig["layout"]:
                    fig["layout"]["xaxis4"]["matches"] = None
                    fig["layout"]["xaxis4"]["showticklabels"] = True
                if "xaxis6" in fig["layout"]:
                    fig["layout"]["xaxis6"]["matches"] = None
                    fig["layout"]["xaxis6"]["showticklabels"] = True
            return fig

        @app.callback(
            self.plugin_data_output,
            [self.plugin_data_requested],
            [
                State(self.uuid("vector1"), "value"),
                State(self.uuid("vector2"), "value"),
                State(self.uuid("vector3"), "value"),
                State(self.uuid("ensemble"), "value"),
                State(self.uuid("mode"), "value"),
                State(self.uuid("base_ens"), "value"),
                State(self.uuid("delta_ens"), "value"),
                State(self.uuid("statistics"), "value"),
                State(self.uuid("cum_interval"), "value"),
            ],
        )
        def _user_download_data(
            data_requested,
            vector1,
            vector2,
            vector3,
            ensembles,
            calc_mode,
            base_ens,
            delta_ens,
            visualization,
            cum_interval,
        ):
            """Callback to download data based on selections"""

            # Combine selected vectors
            vectors = [vector1]
            if vector2:
                vectors.append(vector2)
            if vector3:
                vectors.append(vector3)
            # Ensure selected ensembles is a list and prevent update if invalid calc_mode
            if calc_mode == "delta_ensembles":
                ensembles = [base_ens, delta_ens]
            elif calc_mode == "ensembles":
                ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
            else:
                raise PreventUpdate

            dfs = calculate_vector_dataframes(
                smry=self.smry,
                smry_meta=self.smry_meta,
                ensembles=ensembles,
                vectors=vectors,
                calc_mode=calc_mode,
                visualization=visualization,
                time_index=self.time_index,
                cum_interval=cum_interval,
            )
            for vector, df in dfs.items():
                if visualization in ["statistics", "statistics_hist"]:
                    dfs[vector]["stat"] = df["stat"].sort_values(
                        by=[("", "ENSEMBLE"), ("", "DATE")]
                    )
                    if vector.startswith(("AVG_", "INTVL_")):
                        dfs[vector]["stat"]["", "DATE"] = dfs[vector]["stat"][
                            "", "DATE"
                        ].astype(str)
                        dfs[vector]["stat"]["", "DATE"] = dfs[vector]["stat"][
                            "", "DATE"
                        ].apply(
                            date_to_interval_conversion,
                            vector=vector,
                            interval=cum_interval,
                            as_date=False,
                        )
                else:
                    dfs[vector]["data"] = df["data"].sort_values(
                        by=["ENSEMBLE", "REAL", "DATE"]
                    )
                    # Reorder columns
                    dfs[vector]["data"] = dfs[vector]["data"][
                        ["ENSEMBLE", "REAL", "DATE"]
                        + [
                            col
                            for col in dfs[vector]["data"].columns
                            if col not in ["ENSEMBLE", "REAL", "DATE"]
                        ]
                    ]
                    if vector.startswith(("AVG_", "INTVL_")):
                        dfs[vector]["data"]["DATE"] = dfs[vector]["data"][
                            "DATE"
                        ].astype(str)
                        dfs[vector]["data"]["DATE"] = dfs[vector]["data"]["DATE"].apply(
                            date_to_interval_conversion,
                            vector=vector,
                            interval=cum_interval,
                            as_date=False,
                        )

            # : is replaced with _ in filenames to stay within POSIX portable pathnames
            # (e.g. : is not valid in a Windows path)
            return (
                WebvizPluginABC.plugin_data_compress(
                    [
                        {
                            "filename": f"{vector.replace(':', '_')}.csv",
                            "content": df.get("stat", df["data"]).to_csv(index=False),
                        }
                        for vector, df in dfs.items()
                    ]
                )
                if data_requested
                else ""
            )

        @app.callback(
            [
                Output(self.uuid("show_ensembles"), "style"),
                Output(self.uuid("calc_delta"), "style"),
            ],
            [Input(self.uuid("mode"), "value")],
        )
        def _update_mode(mode):
            """Switch displayed ensemble selector for delta/no-delta"""
            if mode == "ensembles":
                style = {"display": "block"}, {"display": "none"}
            else:
                style = {"display": "none"}, {"display": "block"}
            return style

        @app.callback(
            Output(self.uuid("date"), "data"),
            [Input(self.uuid("graph"), "clickData")],
            [State(self.uuid("date"), "data")],
        )
        def _update_date(clickdata, date):
            """Store clicked date for use in other callback"""
            date = clickdata["points"][0]["x"] if clickdata else json.loads(date)
            return json.dumps(date)

        @app.callback(
            Output(self.uuid("cum_interval"), "options"),
            [
                Input(self.uuid("vector1"), "value"),
                Input(self.uuid("vector2"), "value"),
                Input(self.uuid("vector3"), "value"),
            ],
            [State(self.uuid("cum_interval"), "options")],
        )
        def _activate_interval_radio_buttons(vector1, vector2, vector3, options):
            """Switch activate/deactivate radio buttons for selectibg interval for
            calculations from cumulatives"""
            active = False
            for vector in [vector1, vector2, vector3]:
                if vector is not None and vector.startswith(("AVG_", "INTVL_")):
                    active = True
                    break
            if active:
                return [dict(option, **{"disabled": False}) for option in options]
            return [dict(option, **{"disabled": True}) for option in options]

    def add_webvizstore(self):
        functions = []
        if self.csvfile:
            functions.append((read_csv, [{"csv_file": self.csvfile}]))
        else:
            functions.append(
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
                )
            )
            functions.append(
                (
                    load_smry_meta,
                    [
                        {
                            "ensemble_paths": self.ens_paths,
                            "ensemble_set_name": "EnsembleSet",
                            "column_keys": self.column_keys,
                        }
                    ],
                )
            )
        if self.obsfile:
            functions.append((get_path, [{"path": self.obsfile}]))
        return functions


# pylint: disable=too-many-arguments
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_vector_dataframes(
    smry,
    smry_meta,
    ensembles,
    vectors,
    calc_mode,
    visualization,
    time_index,
    cum_interval,
):
    dfs = {}
    for vector in vectors:
        if vector.startswith("AVG_"):
            total_vector = f"{vector[4:7] + vector[7:].replace('R', 'T', 1)}"
            data = filter_df(smry, ensembles, total_vector, smry_meta)
            data = calc_from_cumulatives(
                data=data,
                column_keys=total_vector,
                time_index=cum_interval,
                time_index_input=time_index,
                as_rate=True,
            )
            vector = rename_vec_from_cum(vector=vector[4:], as_rate=True)
        elif vector.startswith("INTVL_"):
            total_vector = vector.lstrip("INTVL_")
            data = filter_df(smry, ensembles, total_vector, smry_meta)
            data = calc_from_cumulatives(
                data=data,
                column_keys=total_vector,
                time_index=cum_interval,
                time_index_input=time_index,
                as_rate=False,
            )
        else:
            data = filter_df(smry, ensembles, vector, smry_meta)

        if calc_mode == "delta_ensembles":
            data = calculate_delta(data, ensembles[0], ensembles[1])

        dfs[vector] = {"data": data}
        if visualization in ["statistics", "statistics_hist"]:
            dfs[vector]["stat"] = calc_series_statistics(data, [vector])

    return dfs


def filter_df(df, ensembles, vector, smry_meta):
    """Filter dataframe for current vector. Include history
    vector if present"""
    columns = ["REAL", "ENSEMBLE", "DATE", vector]
    if historical_vector(vector=vector, smry_meta=smry_meta) in df.columns:
        columns.append(historical_vector(vector=vector, smry_meta=smry_meta))
    return df.loc[df["ENSEMBLE"].isin(ensembles)][columns]


def calculate_delta(df, base_ens, delta_ens):
    """Calculate delta between two ensembles"""
    base_df = (
        df.loc[df["ENSEMBLE"] == base_ens]
        .set_index(["DATE", "REAL"])
        .drop("ENSEMBLE", axis=1)
    )
    delta_df = (
        df.loc[df["ENSEMBLE"] == delta_ens]
        .set_index(["DATE", "REAL"])
        .drop("ENSEMBLE", axis=1)
    )
    dframe = base_df.sub(delta_df).reset_index()
    dframe["ENSEMBLE"] = f"({base_ens}) - ({delta_ens})"
    return dframe.dropna(axis=0, how="any")


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def add_histogram_traces(dframe, vector, date, colors, interval):
    """Renders a histogram trace per ensemble for a given date"""
    dframe[("DATE")] = dframe[("DATE")].astype(str)
    date = date_to_interval_conversion(
        date=date, vector=vector, interval=interval, as_date=True
    )
    data = dframe.loc[dframe[("DATE")] == date]

    return [
        {
            "type": "histogram",
            "x": list(ens_df[vector]),
            "name": ensemble,
            "marker": {
                "color": colors.get(ensemble, colors[list(colors.keys())[0]]),
                "line": {"color": "black", "width": 1},
            },
            "showlegend": False,
        }
        for ensemble, ens_df in data.groupby(("ENSEMBLE"))
    ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def add_observation_trace(obs):
    return [
        {
            "x": [value.get("date"), []],
            "y": [value.get("value"), []],
            "marker": {"color": "black"},
            "text": value.get("comment", None),
            "hoverinfo": "y+x+text",
            "showlegend": False,
            "error_y": {
                "type": "data",
                "array": [value.get("error"), []],
                "visible": True,
            },
        }
        for value in obs.get("observations", [])
    ]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def add_realization_traces(dframe, vector, colors, line_shape, interval):
    """Renders line trace for each realization, includes history line if present"""
    hovertemplate = render_hovertemplate(vector, interval)
    return [
        {
            "line": {"shape": line_shape},
            "x": list(real_df["DATE"]),
            "y": list(real_df[vector]),
            "hovertemplate": f"{hovertemplate}Realization: {real}, Ensemble: {ensemble}",
            "name": ensemble,
            "legendgroup": ensemble,
            "marker": {"color": colors.get(ensemble, colors[list(colors.keys())[0]])},
            "showlegend": real_no == 0,
        }
        for ens_no, (ensemble, ens_df) in enumerate(dframe.groupby("ENSEMBLE"))
        for real_no, (real, real_df) in enumerate(ens_df.groupby("REAL"))
    ]


def add_history_trace(dframe, vector, line_shape):
    """Renders the history line"""
    df = dframe.loc[
        (dframe["REAL"] == dframe["REAL"].unique()[0])
        & (dframe["ENSEMBLE"] == dframe["ENSEMBLE"].unique()[0])
    ]
    return {
        "line": {"shape": line_shape},
        "x": df["DATE"],
        "y": df[vector],
        "hovertext": "History",
        "hoverinfo": "y+x+text",
        "name": "History",
        "marker": {"color": "black"},
        "showlegend": True,
        "legendgroup": "History",
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def add_statistic_traces(stat_df, vector, colors, line_shape, interval):
    """Add fanchart traces for selected vector"""
    traces = []
    for ensemble, ens_df in stat_df.groupby(("", "ENSEMBLE")):
        traces.extend(
            add_fanchart_traces(
                ens_stat_df=ens_df,
                vector=vector,
                color=colors.get(ensemble, colors[list(colors.keys())[0]]),
                legend_group=ensemble,
                line_shape=line_shape,
                hovertemplate=render_hovertemplate(vector=vector, interval=interval),
            )
        )
    return traces


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)


@webvizstore
def get_path(path) -> Path:
    return Path(path)

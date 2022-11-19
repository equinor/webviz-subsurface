# pylint: disable=too-many-lines
import fnmatch
import json
import warnings
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import webviz_core_components as wcc
import yaml
from dash import (
    ALL,
    Dash,
    Input,
    Output,
    State,
    callback_context,
    dash_table,
    dcc,
    html,
)
from dash.exceptions import PreventUpdate
from webviz_config import WebvizConfigTheme, WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)

from .._abbreviations.number_formatting import table_statistics_base
from .._abbreviations.reservoir_simulation import (
    historical_vector,
    simulation_region_vector_breakdown,
    simulation_region_vector_recompose,
    simulation_unit_reformat,
    simulation_vector_base,
    simulation_vector_description,
)
from .._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    get_fanchart_traces,
)
from .._utils.simulation_timeseries import (
    get_simulation_line_shape,
    set_simulation_line_shape_fallback,
)
from .._utils.unique_theming import unique_colors


class ReservoirSimulationTimeSeriesRegional(WebvizPluginABC):
    """Aggregates and visualizes regional time series data from simulation ensembles. That
is: cumulatives, rates and inplace volumes. Allows human friendly filter names, e.g. regions,
zones and etc based on user input.

In addition recovery is calculated based on the changes in aggregated inplace volumes,
as long as all historical data is present in the data.

Example of aggregation of ROIP over regions in filter:

$$\\sf Agg(\\sf ROIP)_{\\sf date} = \\sum_{N\\in \\sf filter}\\sf ROIP_{N,\\sf date}$$

Example of recovery calculation for ROIP (where ROIP is already aggregated over the filtered
regions):

$$\\sf Rec(\\sf ROIP)_{\\sf date} = \\frac{\\sf ROIP_{\\sf init} - \
\\sf ROIP_{\\sf date}}{\\sf ROIP_{\\sf init}}$$

---

* **`ensembles`:** Which ensembles in `shared_settings` to include in the plugin.
* **`fipfile`:** Path to a yaml-file that defines a match between FIPXXX (e.g. FIPNUM) regions
    and human readable regions, zones and etc to be used as filters. If undefined, the FIPXXX \
    region numbers will be used for filtering (absolute path or relative to config file).
* **`initial_vector`:** First vector to plot (default is `ROIP` if it exists, otherwise first \
    found).
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
Vectors that don't match the following patterns will be filtered out for this plugin:
    * `R[OGW]IP*` (regional in place),
    * `R[OGW][IP][RT]*` (regional injection and production rates and cumulatives)
* **`sampling`:** Time series data will be sampled (and interpolated) at this frequency. Options:
    * `daily`
    * `monthly` (default)
    * `yearly`
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as \
    rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are \
    always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).

---
Vectors are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

The `fipfile` is an optional user defined yaml-file to use for more human friendly filtering. If
undefined (either in general, or for the specific FIPXXX), the region numbers of FIPXXX will be
used as filters. If all region numbers for a filter value in `fipfile` are missing in the data,
this filter value will be silently ignored. E.g. if no vectors match 5 or 6 in
[this example file](\
https://github.com/equinor/webviz-subsurface-testdata/tree/master/reek_history_match/share/\
regions/fip.yaml), `ZONE` == `LowerReek` would be ignored in the plugin for `FIPNUM`. This
is to allow you to use the same file for e.g. a sector and a full field model.

?> To be able to calculate recoveries from inplace volumes, it is needed to ensure that the
inplace at the first time step actually is the initial inplace. It is therefore performed a check
at start-up of `FOPT`, `FGPT` and `FWPT` (at least one has to be present), if one of them is > 0
at the first DATE, a warning is written, and this ensemble will be excluded from recovery
calculations. For a restart run, an attempt is automatically made to find the history when
loading data, but this will unfortunately not work if the path to the restart case in the
simulation run is above 72 signs due to a file format limitation in the simulation metadata files.

?> `csv` input is currently not supported as the metadata aquired when reading from `UNSMRY`
is actively used to decide which vectors that can be used for recovery factors.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the
individual realizations. You should therefore not have more than one `UNSMRY` file in this
folder, to avoid risk of not extracting the right data.
"""

    TABLE_STATISTICS: List[Tuple[str, dict]] = [("Group", {})] + table_statistics_base()
    ENSEMBLE_COLUMNS = ["REAL", "ENSEMBLE", "DATE"]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        fipfile: Path = None,
        initial_vector: str = "ROIP",
        column_keys: Optional[list] = None,
        sampling: str = "monthly",
        line_shape_fallback: str = "linear",
    ):

        super().__init__()

        self.column_keys = column_keys
        self.time_index = sampling
        if self.time_index not in ("daily", "monthly", "yearly"):
            raise ValueError(
                "Incorrent arguments. 'time_index' has to be a specified frequency 'daily',"
                "'monthly' or 'yearly', as the statistics require the same dates throughout an"
                "ensemble."
            )
        self.emodel: EnsembleSetModel = (
            caching_ensemble_set_model_factory.get_or_create_model(
                ensemble_paths={
                    ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                    for ens in ensembles
                },
                time_index=self.time_index,
                column_keys=self.column_keys,
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.smry_meta = self.emodel.load_smry_meta()

        self.field_totals = [
            col for col in self.smry.columns if fnmatch.fnmatch(col, "F[OWG]PT")
        ]
        self.rec_ensembles = set()
        if self.field_totals:
            smry_init_prod = pd.concat(
                [
                    df[df["DATE"] == min(df["DATE"])]
                    for _, df in self.smry[
                        ["ENSEMBLE", "DATE"] + self.field_totals
                    ].groupby("ENSEMBLE")
                ]
            )
            for col in smry_init_prod.columns:
                if col not in ReservoirSimulationTimeSeriesRegional.ENSEMBLE_COLUMNS:
                    for ens in smry_init_prod["ENSEMBLE"].unique():
                        if any(
                            smry_init_prod[smry_init_prod["ENSEMBLE"] == ens][col]
                            > 0.0001
                        ):
                            warnings.warn(
                                f"Ensemble '{ens}' has initial production above 0, can"
                                " therefore not calculate recovery for this ensemble"
                                " (FOPT, FGPT and/or FWPT > 0)."
                                " This ensemble probably includes restarts where we were"
                                " not able to identify the filepaths to the original cases."
                                " Note that RESTART paths with more than 72 characters are"
                                " not supported due to a simulator metadata file format"
                                " limitation."
                            )
                        else:
                            self.rec_ensembles.add(ens)
        else:
            warnings.warn(
                "No production vectors (FOPT, FGPT or FWPT) found for the provided"
                " ensembles. Recoveries can not be calculated from inplace volumes."
            )

        self.smry_cols: List[str] = []
        for col in self.smry.columns:
            if (
                col in ReservoirSimulationTimeSeriesRegional.ENSEMBLE_COLUMNS
                or historical_vector(col, False) in self.smry_cols
            ):
                continue
            if fnmatch.fnmatch(col, "R[OGW]IP*") or fnmatch.fnmatch(
                col, "R[OGW][IP][RT]*"
            ):
                self.smry_cols.append(col)

        if not self.smry_cols:
            raise ValueError(
                "No data. Either no data was found, or all ensembles were dropped due to "
                "non-zero initial production. (FOPT, FGPT and/or FWPT > 0)"
            )

        self.initial_vector = (
            initial_vector
            if any(
                col.startswith((f"{initial_vector}:", f"{initial_vector}_"))
                for col in self.smry_cols
            )
            else simulation_vector_base(self.smry_cols[0])
        )
        self.fipfile = fipfile
        self.fipdesc = (
            None if self.fipfile is None else get_fipdesc(self.fipfile, self.smry_cols)
        )
        self.theme = webviz_settings.theme
        self.line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )
        self.fip_arrays = list(
            {simulation_region_vector_breakdown(col)[1] for col in self.smry_cols}
        )
        self.set_callbacks(app)

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard visualizing regional in-place, cumulatives, rates and recovery. "
                    "Data aggregation and recovery calculation for selected regions are performed "
                    "on demand."
                ),
            },
            {
                "id": self.uuid("graph"),
                "content": (
                    "Visualization of selected data as a time series. Controlled by the options "
                    "in the menu to the left. Clicking this graph will update the date for the "
                    "statistics in the view below."
                ),
            },
            {
                "id": self.uuid("date_view_wrapper"),
                "content": (
                    "Visualization of statistics for a single date (which is selected by clicking "
                    "the time series graph above). A table, box plot, histogram or bar chart per "
                    "realization dependent on selection in the menu to the left."
                ),
            },
            {
                "id": self.uuid("fip_array"),
                "content": (
                    "Select the Eclipse FIP array, e.g. FIPNUM or a custom FIPXXX"
                ),
            },
            {
                "id": self.uuid("groupby"),
                "content": "Select how the data should be grouped.",
            },
            {
                "id": self.uuid("ensemble"),
                "content": (
                    "Select ensembles. Multiple ensembles allowed only when grouping by ensemble."
                ),
            },
            {
                "id": self.uuid("vector"),
                "content": (
                    "Select time series. The options here are the base names of the "
                    "vectors (e.g ROIP), FIP array and FIP regions (e.g. FIPNUM == 1) are decided "
                    "by the other options and filters in the menu. Recovery is added as an "
                    "additional option for oil and gas in-place vectors, and is calculated on the "
                    "fly."
                ),
            },
            {
                "id": self.uuid("timeseries_visualization"),
                "content": (
                    "Select if the time series should be plotted per realization or as a "
                    "fan chart."
                ),
            },
            {
                "id": self.uuid("date_view"),
                "content": (
                    "Select if the single date statistics should be shown as a table, box "
                    "plot, histogram or bar chart per realization."
                ),
            },
            {
                "id": self.uuid("filters"),
                "content": (
                    "Filters. If you have defined a fipfile in your config yaml, these "
                    "will be the groups defined in that file. Otherwise the only option will be "
                    "Regions, which is the numbers for each region in the selected FIP array. "
                    "E.g. if FIP array is FIPNUM, time series is ROIP and selected nodes are "
                    "1 and 2, the aggregation is ROIP:1+ROIP:2. If FIP array had been a custom "
                    "FIPXXX, the aggregation would be ROIP_XXX:1+ROIP_XXX:2."
                ),
            },
        ]

    @property
    def ensembles(self) -> List[str]:
        return list(self.smry["ENSEMBLE"].unique())

    @property
    def all_nodes(self) -> List[str]:
        sorted_int_list = sorted(
            list(
                {
                    int(col.split(":")[1])
                    for col in self.smry_cols
                    if len(col.split(":")) > 1 and col.split(":")[1].isdigit()
                }
            )
        )
        return [str(i) for i in sorted_int_list]

    @property
    def groupby_colors(self) -> dict:
        color_dict = {"ENSEMBLE": unique_colors(self.ensembles, self.theme)}
        if self.fipdesc is None:
            color_dict.update({"regions": unique_colors(self.all_nodes, self.theme)})
        else:
            color_dict.update(
                {
                    group: unique_colors(
                        group_df["SUBGROUP"].unique().tolist(), self.theme
                    )
                    for group, group_df in self.fipdesc.groupby("GROUP")
                }
            )
        return color_dict

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        functions = self.emodel.webvizstore
        if self.fipfile is not None:
            functions.append(
                (
                    get_fipdesc,
                    [{"fipfile": self.fipfile, "column_keys": self.smry_cols}],
                )
            )
        return functions

    def selectors_id(self, selector: str) -> dict:
        return {"page": self.uuid("selectors"), "value": selector}

    def selectors_context_string(self, selector: str, prop: str) -> str:
        return '{"page":"' + self.uuid("selectors") + f'","value":"{selector}"}}.{prop}'

    def selectors_unwrap_context_string(self, context_string: str) -> str:
        return (
            context_string.split(',"value":"', 1)[1]
            .split('"}')[0]
            .rstrip(self.uuid(""))
        )

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=[
                        wcc.Selectors(
                            label="Selectors",
                            children=[
                                wcc.Dropdown(
                                    label="FIP array",
                                    id=self.uuid("fip"),
                                    options=[
                                        {"label": i, "value": i}
                                        for i in self.fip_arrays
                                    ],
                                    value=(
                                        "FIPNUM"
                                        if "FIPNUM" in self.fip_arrays
                                        else self.fip_arrays[0]
                                    ),
                                    clearable=False,
                                ),
                                wcc.Dropdown(
                                    label="Group by",
                                    id=self.selectors_id("groupby"),
                                    clearable=False,
                                ),
                                wcc.Dropdown(
                                    label="Ensembles",
                                    id=self.selectors_id("ensemble"),
                                    options=[
                                        {"label": i, "value": i} for i in self.ensembles
                                    ],
                                    value=self.ensembles,
                                    multi=True,
                                    clearable=False,
                                ),
                                wcc.Dropdown(
                                    label="Time series",
                                    id=self.selectors_id("vector"),
                                    clearable=False,
                                    optionHeight=80,
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Visualization",
                            children=[
                                wcc.RadioItems(
                                    label="Time series",
                                    id=self.selectors_id("timeseries_visualization"),
                                    options=[
                                        {
                                            "label": "Individual realizations",
                                            "value": "realizations",
                                        },
                                        {
                                            "label": "Statistical fanchart",
                                            "value": "statistics",
                                        },
                                    ],
                                    value="statistics",
                                ),
                                wcc.Dropdown(
                                    label="Single date statistics as",
                                    id=self.selectors_id("date_view"),
                                    options=[
                                        {"label": i.lower().capitalize(), "value": i}
                                        for i in [
                                            "table",
                                            "box plot",
                                            "histogram",
                                            "per realization",
                                        ]
                                    ],
                                    value="table",
                                    clearable=False,
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Filters:",
                            children=html.Div(id=self.uuid("filters"), children=[]),
                        ),
                    ],
                ),
                wcc.FlexColumn(
                    flex=6,
                    style={"height": "90vh"},
                    children=[
                        wcc.Frame(
                            color="white",
                            highlight=False,
                            children=wcc.Graph(
                                id=self.uuid("graph"),
                                clickData={
                                    "points": [{"x": str(self.smry["DATE"].min())}]
                                },
                                style={"height": "40vh"},
                            ),
                        ),
                        wcc.Frame(
                            style={"height": "45vh"},
                            color="white",
                            highlight=False,
                            children=[
                                html.Div(
                                    id=self.uuid("stats_title"),
                                    style={
                                        "textAlign": "center",
                                    },
                                    children="",
                                ),
                                html.Div(id=self.uuid("date_view_wrapper")),
                            ],
                        ),
                    ],
                ),
                dcc.Store(
                    id=self.uuid("date"),
                    storage_type="session",
                    data=json.dumps(str(self.smry["DATE"].min())),
                ),
                dcc.Store(
                    id=self.uuid("ref_vec"), storage_type="session", data=json.dumps("")
                ),
            ],
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            [
                Output(self.uuid("filters"), "children"),
                Output(self.selectors_id("vector"), "options"),
                Output(self.selectors_id("vector"), "value"),
                Output(self.selectors_id("groupby"), "options"),
                Output(self.selectors_id("groupby"), "value"),
            ],
            [Input(self.uuid("fip"), "value")],
            [
                State(self.selectors_id("vector"), "value"),
                State(self.selectors_id("groupby"), "value"),
            ],
        )
        def _update_filters_vectors_groupby(
            fip: str, current_vector: str, current_groupby: str
        ) -> Tuple[List[html.Details], List[dict], str, List[dict], str]:
            """
            Makes "wcc.Select" components based on the available filters.
            If a fipfile is provided, the filters will be based on the available groups in that
            file. Otherwise the filter will be the region numbers for the specific FIP array
            (e.g. FIPNUM)
            In addition: Available vectors and groupby options are updated for the selected
            fip_array. These actions are done in the same callback to prevent multiple
            executions of the _render_charts callback at FIP array change.
            """
            fipdesc = (
                None
                if self.fipdesc is None or fip not in self.fipdesc["FIP"].values
                else self.fipdesc[self.fipdesc["FIP"] == fip]
            )
            # Creating wcc.Select components
            if fipdesc is None:
                nodes = get_fip_array_nodes(fip, self.smry_cols)
                filters = [
                    wcc.SelectWithLabel(
                        label="Regions",
                        id=self.selectors_id(fip + self.uuid("regions")),
                        options=[{"label": i, "value": i} for i in nodes],
                        size=min([len(nodes), 10]),
                        value=nodes,
                    ),
                ]

            else:
                filters = [
                    wcc.SelectWithLabel(
                        label=group.lower().capitalize(),
                        id=self.selectors_id(fip + self.uuid(group)),
                        options=[
                            {"label": i, "value": i}
                            for i in group_df["SUBGROUP"].unique()
                        ],
                        size=min([len(group_df["SUBGROUP"].unique()), 5]),
                        value=group_df["SUBGROUP"].unique(),
                    )
                    for group, group_df in fipdesc.groupby("GROUP")
                ]

            # Update vectors
            vectors = set()
            for col in self.smry_cols:
                if simulation_region_vector_breakdown(col)[1] == fip:
                    vector_base = simulation_vector_base(col)
                    vectors.add(vector_base)
                    if fnmatch.fnmatch(vector_base, "R[OG]IP*"):
                        vectors.add(
                            f"Recovery Factor of {simulation_vector_description(vector_base)} (("
                            f"{vector_base} (initial) - {vector_base} (now))/{vector_base}"
                            " (initial))"
                        )
            vector_options = [
                {
                    "label": simulation_vector_description(i)
                    + ("" if i.startswith("Recovery") else f" ({i}) "),
                    "value": i,
                }
                for i in sorted(list(vectors))
            ]
            vector_value = (
                current_vector
                if current_vector in vectors
                else self.initial_vector
                if self.initial_vector in vectors
                else sorted(list(vectors))[0]
            )
            # Update groupby
            groups = ["ENSEMBLE"] + (
                ["regions"] if fipdesc is None else fipdesc["GROUP"].unique().tolist()
            )
            groupby_options = [
                {
                    "label": i.lower().capitalize(),
                    "value": i,
                }
                for i in groups
            ]
            groupby_value = current_groupby if current_groupby in groups else "ENSEMBLE"
            return (
                filters,
                vector_options,
                vector_value,
                groupby_options,
                groupby_value,
            )

        @app.callback(
            [  # type: ignore
                Output(self.uuid("graph"), "figure"),
                Output(self.uuid("date_view_wrapper"), "children"),
                Output(self.uuid("ref_vec"), "data"),
            ],
            [Input(self.uuid("date"), "data")]
            + [Input({"page": self.uuid("selectors"), "value": ALL}, "value")],
            [State(self.uuid("fip"), "value")],
        )
        def _render_charts(  # pylint: disable=too-many-locals
            date: str, _: Any, fip_array: str
        ):
            # TODO(Sigurd) Currently giving up on deciding on the return type for
            # _render_charts() above. Some of the mypy errors indicate that there
            # are some errors in the structure of the return values of this function
            inputs = callback_context.inputs
            date = json.loads(inputs.pop(f"{self.uuid('date')}.data"))
            ensembles = inputs.pop(self.selectors_context_string("ensemble", "value"))
            ensembles = ensembles if isinstance(ensembles, list) else [ensembles]
            groupby = inputs.pop(self.selectors_context_string("groupby", "value"))
            vector = inputs.pop(self.selectors_context_string("vector", "value"))
            time_series_viz = inputs.pop(
                self.selectors_context_string("timeseries_visualization", "value")
            )
            date_viz = inputs.pop(self.selectors_context_string("date_view", "value"))
            filters = {
                self.selectors_unwrap_context_string(key)[len(fip_array) :]: (
                    value if isinstance(value, list) else [value]
                )
                for (key, value) in inputs.items()
            }
            if not filters:
                # If filter selectors are not generated yet.
                raise PreventUpdate

            if vector.startswith("Recovery Factor of"):
                mode = "rec"
                vector_base = vector.split("/")[-1].rstrip("(initial)").strip()
            else:
                mode = "agg"
                vector_base = vector
            try:
                df, ref_vector = filter_and_aggregate_vectors(
                    smry=self.smry,
                    ensembles=ensembles,
                    groupby=groupby,
                    vector=vector_base,
                    filters=filters,
                    fipdesc=self.fipdesc,
                    fip=fip_array,
                )
            except KeyError as exception:
                return [
                    [{}],
                    html.Div(
                        children=(
                            f"KeyError: {exception}\n"
                            f"Likely to be that one or more vectors are missing in your data."
                        ),
                        style={
                            "textAlign": "center",
                            "font-weight": "bold",
                            "whiteSpace": "pre-wrap",
                        },
                    ),
                    json.dumps(""),
                ]
            if len(df.columns) < 4:
                # Filter combination has removed all other vectors
                # than ENSEMBLE, REAL and DATE
                return [
                    [{}],
                    html.Div(
                        children="Filter combination yielded no matching vectors",
                        style={"textAlign": "center", "font-weight": "bold"},
                    ),
                    json.dumps(""),
                ]
            line_shape = get_simulation_line_shape(
                line_shape_fallback=self.line_shape_fallback,
                vector=ref_vector,
                smry_meta=self.smry_meta,
            )
            (timeseries_traces, df) = per_real_calculations(
                df=df,
                ensembles=ensembles,
                rec_ensembles=self.rec_ensembles,
                groupby=groupby,
                groupby_colors=self.groupby_colors,
                vector=vector_base,
                filters=filters,
                mode=mode,
                visualization=time_series_viz,
                line_shape=line_shape,
            )
            if time_series_viz == "statistics" or date_viz == "table":
                stat_df = calc_statistics(df)
            if time_series_viz == "statistics":
                timeseries_traces = add_statistic_traces(
                    stat_df=stat_df,
                    ensembles=ensembles,
                    mode=mode,
                    groupby=groupby,
                    groupby_color=self.groupby_colors,
                    line_shape=line_shape,
                )
            if date_viz == "table":
                date_view = render_table(
                    stat_df=stat_df, mode=mode, groupby=groupby, date=date
                )
            elif date_viz in ["box plot", "histogram", "per realization"]:
                date_view = render_single_date_graph(
                    date_viz=date_viz,
                    df=df,
                    mode=mode,
                    groupby=groupby,
                    date=date,
                    theme=self.theme,
                    title=make_title(self.smry_meta, ref_vector, vector, mode),
                    colors=self.groupby_colors[groupby],
                )
            else:
                date_view = html.Div(children="")
            timeseries_layout: dict = {
                "hovermode": "closest",
                "yaxis": {
                    "title": make_title(self.smry_meta, ref_vector, vector, mode),
                    "showgrid": False,
                },
                "xaxis": {"showgrid": False, "uirevision": "locked"},
                "height": 450,
            }
            if mode == "rec":
                timeseries_layout["yaxis"].update(
                    {
                        "exponentformat": "none",
                        "tickformat": ".0%",
                        "hoverformat": ".2%",
                    },
                )

            # TODO(Sigurd)
            # Must have a look at the return value structure here!
            return (
                (
                    [
                        {
                            "data": timeseries_traces,
                            "layout": self.theme.create_themed_layout(
                                timeseries_layout
                            ),
                        },
                    ]
                )
                + [date_view]
                + [json.dumps(ref_vector)]  # type: ignore
            )

        @app.callback(
            [
                Output(self.selectors_id("ensemble"), "multi"),
                Output(self.selectors_id("ensemble"), "value"),
            ],
            [Input(self.selectors_id("groupby"), "value")],
            [State(self.selectors_id("ensemble"), "multi")],
        )
        def _set_ensemble_selector(
            group_by: str, multi: bool
        ) -> Tuple[bool, Union[List[str], str]]:
            """If ensemble is selected as group by, set the ensemble
            selector to allow multiple selections. Otherwise single selection.
            """
            if group_by == "ENSEMBLE":
                if multi:
                    raise PreventUpdate
                return (True, self.ensembles)
            if not multi:
                raise PreventUpdate
            return (False, self.ensembles[0])

        @app.callback(
            Output(self.uuid("date"), "data"),
            [Input(self.uuid("graph"), "clickData")],
            [State(self.uuid("date"), "data")],
        )
        def _update_date(clickdata: dict, date: str) -> str:
            """Store clicked date for use in other callback"""
            date = clickdata["points"][0]["x"] if clickdata else json.loads(date)
            return json.dumps(date)

        @app.callback(
            Output(self.uuid("stats_title"), "children"),
            [
                Input(self.uuid("date"), "data"),
                Input(self.uuid("ref_vec"), "data"),
            ],
            [State(self.selectors_id("vector"), "value")],
        )
        def _update_single_date_title(date: str, ref_vector: str, vector: str) -> str:
            """Update single date title"""
            date = json.loads(date)
            ref_vector = json.loads(ref_vector)
            if ref_vector == "":
                return ""
            title = f"Date: {date}, {simulation_vector_description(vector)}" + (
                ""
                if vector.startswith("Recovery")
                else f" ({vector})"
                + (
                    ""
                    if get_unit(self.smry_meta, ref_vector) is None
                    else f" [{get_unit(self.smry_meta, ref_vector)}]"
                )
            )
            return title


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_title(smry_meta: pd.DataFrame, ref_vector: str, vector: str, mode: str) -> str:
    return (
        f"{simulation_vector_description(vector).split(')')[0]})"
        if mode == "rec"
        else f"{simulation_vector_description(vector)} ({vector})"
        + (
            ""
            if get_unit(smry_meta, ref_vector) is None
            else f" [{get_unit(smry_meta, ref_vector)}]"
        )
    )


def render_single_date_graph(
    date_viz: str,
    df: pd.DataFrame,
    mode: str,
    groupby: str,
    date: str,
    theme: WebvizConfigTheme,
    title: str,
    colors: dict,
) -> wcc.Graph:
    def _make_trace(
        date_viz: str, df: pd.DataFrame, col: str, name: str, color: str
    ) -> Union[dict, None]:
        if date_viz == "histogram":
            return {
                "x": df[col],
                "type": "histogram",
                "name": name,
                "marker": {"color": color},
            }
        if date_viz == "box plot":
            return {
                "y": df[col],
                "type": "box",
                "name": name,
                "marker": {"color": color},
            }
        if date_viz == "per realization":
            return {
                "x": df["REAL"],
                "y": df[col],
                "type": "bar",
                "name": name,
                "marker": {"color": color},
            }
        return None

    columns = []
    if mode == "agg":
        columns = [col for col in df.columns if col.startswith("AGG_")]
    elif mode == "rec":
        columns = [col for col in df.columns if col.startswith("REC_")]
    if not columns:
        return []
    columns = list(
        dict.fromkeys(columns)
    )  # Make unique while preserving order of first occurance.
    traces = []
    df["DATE"] = df["DATE"].astype(str)
    df = df.loc[df["DATE"] == date]
    if groupby == "ENSEMBLE":
        for ens in df["ENSEMBLE"].unique():
            if len(columns) != 1:
                # Should never occur
                raise ValueError(
                    "Not unique data for column, date and ensemble combination."
                )
            trace = _make_trace(
                date_viz, df[df["ENSEMBLE"] == ens], columns[0], ens, colors[ens]
            )
            if trace is not None:
                traces.append(trace)
    else:
        for col in columns:
            if len(df["ENSEMBLE"].unique()) > 1:
                # Should never occur
                raise ValueError(
                    "Not unique data for column, date and ensemble combination."
                )
            trace = _make_trace(
                date_viz,
                df,
                col,
                col.split("_filtered_on_")[-1],
                colors[col.split("_filtered_on_")[-1]],
            )
            if trace is not None:
                traces.append(trace)
    layout = {
        "height": 500,
        "margin": {
            "t": 10,
        },
        "showlegend": True,
    }

    if date_viz == "histogram":
        layout.update(
            {
                "barmode": "overlay",
                "bargap": 0.01,
                "bargroupgap": 0.2,
                "xaxis": {
                    "exponentformat": "none",
                    "tickformat": ".1%",
                    "hoverformat": ".2%",
                    "title": title,
                }
                if mode == "rec"
                else {"title": title},
                "yaxis": {
                    "title": "Count",
                    "tickformat": "d",
                    "exponentformat": "none",
                },
            }
        )
    else:
        layout.update(
            {
                "yaxis": {
                    "exponentformat": "none",
                    "tickformat": ".1%",
                    "hoverformat": ".2%",
                    "title": title,
                }
                if mode == "rec"
                else {"title": title},
            }
        )
        if date_viz == "per realization":
            layout.update(
                {
                    "xaxis": {
                        "exponentformat": "none",
                        "tickformat": "d",
                        "title": "Realization",
                    }
                }
            )

    return wcc.Graph(
        figure={"data": traces, "layout": theme.create_themed_layout(layout)}  # type: ignore
    )


def render_table(
    stat_df: pd.DataFrame, mode: str, groupby: str, date: str
) -> dash_table.DataTable:
    columns = []
    if mode == "agg":
        columns = [col[0] for col in stat_df.columns if col[0].startswith("AGG_")]
    elif mode == "rec":
        columns = [col[0] for col in stat_df.columns if col[0].startswith("REC_")]
    if not columns:
        return []
    columns = list(
        dict.fromkeys(columns)
    )  # Make unique while preserving order of first occurance.

    stat_df["DATE"] = stat_df["DATE"].astype(str)
    stat_df = stat_df.loc[stat_df["DATE"] == date]
    table = []
    for col in columns:
        if groupby == "ENSEMBLE":
            for ens in stat_df["ENSEMBLE"].unique():
                df = stat_df[stat_df["ENSEMBLE"] == ens][col]
                if len(df.index) > 1:
                    # Should never occur
                    raise ValueError(
                        "Not unique data for column, date and ensemble combination."
                    )
                table.append(
                    {
                        "Group": ens,
                        "Minimum": df["nanmin"].iat[0],
                        "Maximum": df["nanmax"].iat[0],
                        "Mean": df["nanmean"].iat[0],
                        "Stddev": df["nanstd"].iat[0],
                        "P10": df["p10"].iat[0],
                        "P90": df["p90"].iat[0],
                    }
                )
        else:
            df = stat_df[col]
            if len(df.index) > 1:
                # Should never occur
                raise ValueError("Not unique data for column and date combination.")
            table.append(
                {
                    "Group": col.split("_filtered_on_")[-1],
                    "Minimum": df["nanmin"].iat[0],
                    "Maximum": df["nanmax"].iat[0],
                    "Mean": df["nanmean"].iat[0],
                    "Stddev": df["nanstd"].iat[0],
                    "P10": df["p10"].iat[0],
                    "P90": df["p90"].iat[0],
                }
            )
    columns = [
        {**{"name": i[0], "id": i[0]}, **i[1]}
        for i in deepcopy(ReservoirSimulationTimeSeriesRegional.TABLE_STATISTICS)
    ]
    if mode == "rec":
        for col in columns:
            try:
                col["format"]["specifier"] = ".2%"
            except KeyError:
                pass
    return (
        dash_table.DataTable(
            sort_action="native",
            filter_action="native",
            page_action="native",
            page_size=10,
            data=table,
            columns=columns,
        ),
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_and_aggregate_vectors(
    smry: pd.DataFrame,
    ensembles: list,
    groupby: str,
    vector: str,
    filters: dict,
    fipdesc: pd.DataFrame,
    fip: str,
) -> Tuple[pd.DataFrame, str]:
    """Aggregate inplace vectors based on filters
    Note: ensemble is only in the list of inputs to reduce risk with caching
          See: https://github.com/equinor/webviz-config/issues/211
    Creating Eclipse format summary vectors from selection
    """
    if groupby != "ENSEMBLE" and len(ensembles) > 1:  # This should never happen
        raise ValueError("Cannot have multiple ensembles unless you group by ensemble")
    df = smry[smry["ENSEMBLE"].isin(ensembles)]
    if fipdesc is None or fip not in fipdesc["FIP"].values:
        if groupby == "ENSEMBLE":
            nodes = filters
        else:
            nodes = {str(node): [node] for node in filters["regions"]}
    else:
        nodes = get_nodes(
            groupby=groupby,
            fipdesc=fipdesc,
            fip=fip,
            filters=filters,
        )
    subgroup_vectors = {
        subgroup: [
            simulation_region_vector_recompose(
                vector_base_name=vector, fiparray=fip, node=node
            )
            for node in values
        ]
        for subgroup, values in nodes.items()
    }
    # Storing a full vector name that exists in the dataset to be used for metadata
    ref_vector = ""
    for _, vector_list in subgroup_vectors.items():
        for vec in vector_list:
            if vec in smry.columns:
                ref_vector = vec
                break
        else:
            continue
        break

    # Aggregate, concatenate and return.
    return (
        pd.concat(
            [df[["ENSEMBLE", "REAL", "DATE"]]]
            + [
                df[vectors].sum(axis=1).to_frame(f"AGG_{vector}_filtered_on_{subgroup}")
                for subgroup, vectors in subgroup_vectors.items()
            ],
            axis=1,
        ),
        ref_vector,
    )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_nodes(groupby: str, fipdesc: pd.DataFrame, fip: str, filters: dict) -> dict:
    df = fipdesc[fipdesc["FIP"] == fip]
    nodes: dict = {}
    for node, dfn in df.groupby("NODE"):
        node_inc = True
        node_subgroups = []
        for group, subgroups in filters.items():
            if dfn[dfn["GROUP"] == group].empty or not all(
                dfn[dfn["GROUP"] == group]["SUBGROUP"].isin(subgroups)
            ):
                node_inc = False
                break
            if group == groupby and groupby != "ENSEMBLE":
                node_subgroups.extend(dfn[dfn["GROUP"] == group]["SUBGROUP"])
        if node_inc:
            if groupby == "ENSEMBLE":
                if "ENSEMBLE" in nodes:
                    nodes["ENSEMBLE"].append(node)
                else:
                    nodes["ENSEMBLE"] = [node]
            elif len(node_subgroups) == 1:
                if node_subgroups[0] in nodes:
                    nodes[node_subgroups[0]].append(node)
                else:
                    nodes[node_subgroups[0]] = [node]
            elif len(node_subgroups) > 1:
                raise ValueError(
                    f"This should not occur, likely to be a bug. Vector nr {node} matched several"
                    f"{groupby} that your tried to group by."
                    "Please report this at https://github.com/equinor/webviz-subsurface/issues"
                )
    return nodes


# TODO(Sigurd) What is the correct return type of this function? numpy.ndarray?
def calc_real_recovery(df: pd.DataFrame, agg_vectors: List[str]):  # type: ignore
    first = df[agg_vectors].values[0]
    with np.errstate(invalid="ignore"):
        return (first - df[agg_vectors].values) / first


# pylint: disable=too-many-arguments, too-many-locals, unused-argument
@CACHE.memoize(timeout=CACHE.TIMEOUT)
def per_real_calculations(
    df: pd.DataFrame,
    ensembles: list,
    rec_ensembles: list,
    groupby: str,
    groupby_colors: dict,
    vector: str,  # only used too reduce caching risk
    filters: dict,
    mode: str,
    visualization: str,
    line_shape: str,
) -> tuple:
    """All calls that are per realization are called here to avoid multiple loops:
    That includes calculation of recovery and making traces per realization.
    This method assumes that the DataFrame 'df' has already been processed with
    the 'filter_and_aggregate_vectors' method.
    """
    if groupby != "ENSEMBLE" and len(ensembles) > 1:  # This should never happen
        raise ValueError("Cannot have multiple ensembles unless you group by ensemble")
    traces = []
    ens_dfs = []
    # Find aggregated vectors
    agg_vectors = df.columns[df.columns.str.contains("AGG_.*")]
    # Subgroups from aggregated vector names to be used for e.g. legend.
    groupby_names = [
        agg_vector.split("_filtered_on_")[-1] for agg_vector in agg_vectors
    ]
    # Make recovery vector names if relevant
    if mode == "rec":
        rec_vectors = ["REC" + vec[3:] for vec in agg_vectors]
    # Iterate over ensembles and realizations
    for ens, ens_df in df.groupby("ENSEMBLE"):
        ens_rec = []
        if mode == "rec" and ens not in rec_ensembles:
            continue
        for real_no, (real, real_df) in enumerate(ens_df.groupby("REAL")):
            if mode == "rec":
                rec = calc_real_recovery(real_df, agg_vectors)
                ens_rec.extend(rec)

            if visualization == "realizations":
                for i, vec in enumerate(agg_vectors):
                    name = ens if groupby == "ENSEMBLE" else groupby_names[i]
                    traces.append(
                        {
                            "x": real_df["DATE"],
                            "y": rec[:, i] if mode == "rec" else real_df[vec],
                            "hovertext": (
                                f"{groupby.lower().capitalize()}: {name} "
                                + f"Realization: {real}"
                            ),
                            "name": name,
                            "legendgroup": name,
                            "marker": {"color": groupby_colors[groupby][name]},
                            "showlegend": real_no == 0,
                            "line": {"shape": line_shape},
                        }
                    )
        if mode == "rec":
            # We want to store calculated recovery for statistical graphs and tables
            ens_dfs.append(
                pd.concat(
                    [
                        ens_df.reset_index(drop=True),
                        pd.DataFrame(ens_rec, columns=rec_vectors).reset_index(
                            drop=True
                        ),
                    ],
                    axis=1,
                )
            )
    # Concat ensemble dfs with calculated recovery
    if ens_dfs:
        df = pd.concat(ens_dfs, ignore_index=True)
    return (traces, df)


def calc_statistics(df: pd.DataFrame) -> pd.DataFrame:
    # Switched P10 and P90 due to convention in petroleum industry
    def p10(x: np.ndarray) -> float:
        return np.nanpercentile(x, q=90)

    def p90(x: np.ndarray) -> float:
        return np.nanpercentile(x, q=10)

    stat_dfs = []
    for ens, ens_df in df.groupby("ENSEMBLE"):
        stat_dfs.append(
            ens_df.drop(columns=["REAL", "ENSEMBLE"])
            .groupby("DATE", as_index=False)
            .agg([np.nanmean, np.nanstd, np.nanmin, np.nanmax, p10, p90])
            .reset_index()
            .assign(ENSEMBLE=ens)
        )
    return pd.concat(stat_dfs)


def add_statistic_traces(
    stat_df: pd.DataFrame,
    ensembles: List[str],
    mode: str,
    groupby: str,
    groupby_color: dict,
    line_shape: str,
) -> list:
    columns: List[str] = []
    if mode == "agg":
        columns = [col[0] for col in stat_df.columns if col[0].startswith("AGG_")]
    elif mode == "rec":
        columns = [col[0] for col in stat_df.columns if col[0].startswith("REC_")]
    if not columns:
        return []
    columns = list(
        dict.fromkeys(columns)
    )  # Make unique while preserving order of first occurance.

    traces = []
    for col in columns:
        if groupby == "ENSEMBLE":
            for ens in ensembles:
                traces.extend(
                    _get_fanchart_traces(
                        stat_df=stat_df[stat_df["ENSEMBLE"] == ens],
                        column=col,
                        legend_group=ens,
                        color=groupby_color[groupby][ens],
                        line_shape=line_shape,
                    )
                )
        else:
            traces.extend(
                _get_fanchart_traces(
                    stat_df=stat_df,
                    column=col,
                    legend_group=col.split("_filtered_on_")[-1],
                    color=groupby_color[groupby][col.split("_filtered_on_")[-1]],
                    line_shape=line_shape,
                )
            )
    return traces


def _get_fanchart_traces(
    stat_df: pd.DataFrame, column: str, legend_group: str, color: str, line_shape: str
) -> List[Dict[str, Any]]:
    """Renders a fanchart"""

    x = stat_df["DATE"].tolist()

    data = FanchartData(
        samples=x,
        low_high=LowHighData(
            low_data=stat_df[column]["p90"].values,
            low_name="P90",
            high_data=stat_df[column]["p10"].values,
            high_name="P10",
        ),
        minimum_maximum=MinMaxData(
            minimum=stat_df[column]["nanmin"].values,
            maximum=stat_df[column]["nanmax"].values,
        ),
        free_line=FreeLineData("Mean", stat_df[column]["nanmean"].values),
    )

    hovertemplate = f"{legend_group}"

    return get_fanchart_traces(
        data=data,
        hex_color=color,
        legend_group=legend_group,
        line_shape=line_shape,
        hovertext=hovertemplate,
    )


def get_fip_array_nodes(fip: str, smry_cols: list) -> List[int]:
    """Sorted list of all available nodes for a given fip array (e.g FIPNUM)"""
    sorted_int_list = sorted(
        list(
            {
                int(col.split(":")[1])
                for col in smry_cols
                if (
                    len(col.split(":")) > 1
                    and col.split(":")[1].isdigit()
                    and simulation_region_vector_breakdown(col)[1] == fip
                )
            }
        )
    )
    return sorted_int_list


@webvizstore
def get_fipdesc(fipfile: Path, column_keys: list) -> pd.DataFrame:
    fipdesc: list = []
    with open(Path(fipfile), "r") as stream:
        fipdict = yaml.safe_load(stream)
    for fip, fipdef in fipdict.items():
        for group, group_def in fipdef.get("groups").items():
            for key, fip_nodes in group_def.items():
                for x in fip_nodes:
                    if not isinstance(x, int):
                        raise TypeError(
                            f"FIP: {fip}, group: {group}, subgroup: {key} has non-integer input."
                        )
                    if (fip, group, x) in fipdesc:
                        raise ValueError(
                            f"FIP: {fip}, group: {group} has input which is not unique."
                            f"Value {x}  is used for multiple subgroups."
                        )
                    fipdesc.append((str(fip), str(group), str(key), x))
    df_before_data_verification = pd.DataFrame(
        fipdesc, columns=("FIP", "GROUP", "SUBGROUP", "NODE")
    )
    dfs = []
    for fip, fip_df in df_before_data_verification.groupby("FIP"):
        nodes_in_data = get_fip_array_nodes(fip, column_keys)
        dfs.extend(
            [
                subgroup_df
                for _, subgroup_df in fip_df.groupby(["GROUP", "SUBGROUP"])
                if not subgroup_df[subgroup_df["NODE"].isin(nodes_in_data)].empty
            ]
        )
    return pd.concat(dfs).sort_index()


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_unit(smry_meta: pd.DataFrame, vec: str) -> Union[str, None]:
    return (
        None
        if (smry_meta is None or vec not in smry_meta.index)
        else simulation_unit_reformat(smry_meta.unit[vec])
    )

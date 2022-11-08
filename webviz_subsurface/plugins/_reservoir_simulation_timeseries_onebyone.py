import datetime
import json
from pathlib import Path
from typing import Callable, List, Optional, Tuple, Union
from uuid import uuid4

import numpy as np
import pandas as pd
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from webviz_subsurface._components import TornadoWidget
from webviz_subsurface._figures import TimeSeriesFigure
from webviz_subsurface._models.parameter_model import ParametersModel
from webviz_subsurface._providers import (
    EnsembleSummaryProviderFactory,
    EnsembleTableProviderFactory,
    EnsembleTableProviderSet,
    Frequency,
)
from webviz_subsurface._utils.dataframe_utils import merge_dataframes_on_realization
from webviz_subsurface._utils.datetime_utils import from_str, to_str
from webviz_subsurface.plugins._parameter_analysis.models import (
    ProviderTimeSeriesDataModel,
    SimulationTimeSeriesModel,
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

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        csvfile_smry: Path = None,
        csvfile_parameters: Path = None,
        time_index: str = "monthly",
        sampling: str = "monthly",
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        ensembles: list = None,
        column_keys: list = None,
        initial_vector: str = None,
        line_shape_fallback: str = "linear",
    ) -> None:

        super().__init__()

        self.csvfile_smry = csvfile_smry
        self.csvfile_parameters = csvfile_parameters
        self.ensembles = ensembles
        self.vmodel: Optional[
            Union[SimulationTimeSeriesModel, ProviderTimeSeriesDataModel]
        ] = None
        table_provider = EnsembleTableProviderFactory.instance()

        if csvfile_smry and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_smry" and "csvfile_parameters" or '
                '"ensembles"'
            )
        if csvfile_smry and csvfile_parameters:
            smry_df = read_csv(csvfile_smry)
            parameter_df = read_csv(csvfile_parameters)

            self.vmodel = SimulationTimeSeriesModel(
                dataframe=smry_df, line_shape_fallback=line_shape_fallback
            )

        elif ensembles:

            ensemble_paths = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }

            resampling_frequency = Frequency(time_index)
            provider_factory = EnsembleSummaryProviderFactory.instance()

            try:
                provider_set = {
                    ens: provider_factory.create_from_arrow_unsmry_presampled(
                        str(ens_path), rel_file_pattern, resampling_frequency
                    )
                    for ens, ens_path in ensemble_paths.items()
                }
                self.vmodel = ProviderTimeSeriesDataModel(
                    provider_set=provider_set, column_keys=column_keys
                )

            except ValueError as error:
                message = (
                    f"Some/all ensembles are missing arrow files at {rel_file_pattern}.\n"
                    "If no arrow files have been generated with `ERT` using `ECL2CSV`, "
                    "the commandline tool `smry2arrow_batch` can be used to generate arrow "
                    "files for an ensemble"
                )
                raise ValueError(message) from error

            parameter_df = self.create_df_from_table_provider(
                table_provider.create_provider_set_from_per_realization_parameter_file(
                    ensemble_paths
                )
            )

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile_smry" and "csvfile_parameters" or '
                '"ensembles"'
            )

        self.pmodel = ParametersModel(dataframe=parameter_df, drop_constants=True)
        self.parameter_df = self.pmodel.dataframe

        self.vectors = self.vmodel.vectors
        self.smry_meta = None

        self.initial_vector = (
            initial_vector
            if initial_vector and initial_vector in self.vectors
            else self.vectors[0]
        )
        self.ensembles = list(self.parameter_df["ENSEMBLE"].unique())
        self.realizations = list(self.parameter_df["REAL"].unique())
        self.tornadoplot = TornadoWidget(
            app, webviz_settings, self.parameter_df, allow_click=True
        )
        self.uid = uuid4()
        self.theme = webviz_settings.theme
        self.set_callbacks(app)

    def ids(self, element: str) -> str:
        """Generate unique id for dom element"""
        return f"{element}-id-{self.uid}"

    def create_df_from_table_provider(
        self, provider: EnsembleTableProviderSet
    ) -> pd.DataFrame:
        dfs = []
        for ens in provider.ensemble_names():
            df = provider.ensemble_provider(ens).get_column_data(
                column_names=provider.ensemble_provider(ens).column_names()
            )
            df["ENSEMBLE"] = df.get("ENSEMBLE", ens)
            dfs.append(df)
        return pd.concat(dfs)

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
    def visualization_selector(self) -> html.Div:
        """Dropdown to select ensemble"""
        return wcc.RadioItems(
            id=self.ids("visualization"),
            options=[
                {"label": "Individual realizations", "value": "realizations"},
                {"label": "Mean over Sensitivities", "value": "sensmean"},
            ],
            value="realizations",
        )

    @property
    def sensitivity_selector(self) -> html.Div:
        """Dropdown to select ensemble"""
        return wcc.SelectWithLabel(
            id=self.ids("sensitivity_filter"),
            options=[{"label": i, "value": i} for i in self.pmodel.sensitivities],
            value=self.pmodel.sensitivities,
            size=min(20, len(self.pmodel.sensitivities)),
        )

    @property
    def vector_selector(self) -> html.Div:
        """Dropdown to select ensemble"""
        return wsc.VectorSelector(
            id=self.ids("vector"),
            maxNumSelectedNodes=1,
            data=self.vmodel.vector_selector_data,
            persistence=True,
            persistence_type="session",
            selectedTags=[self.initial_vector],
            numSecondsUntilSuggestionsAreShown=0.5,
            lineBreakAfterTag=True,
        )

    @property
    def colormap(self) -> dict:
        return {
            sens: color
            for sens, color in zip(
                self.parameter_df["SENSNAME_CASE"],
                (self.theme.plotly_theme["layout"]["colorway"] * 3),
            )
        }

    @property
    def initial_date(self) -> str:
        return to_str(max(self.vmodel.dates))

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
            else []
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
                                children=[
                                    self.ensemble_selector,
                                    self.vector_selector,
                                ],
                            ),
                            wcc.Selectors(
                                label="Visualization",
                                children=self.visualization_selector,
                            ),
                            wcc.Selectors(
                                label="Sensitivity filter",
                                children=[self.sensitivity_selector],
                            ),
                        ],
                    ),
                ),
                wcc.FlexColumn(
                    flex=3,
                    children=[
                        wcc.Frame(
                            style={"height": "48vh"},
                            color="white",
                            highlight=False,
                            children=wcc.Graph(
                                id=self.ids("graph"),
                                style={"height": "46vh"},
                                clickData={"points": [{"x": self.initial_date}]},
                            ),
                        ),
                    ],
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

    def create_vectors_statistics_df(self, dframe, vector) -> pd.DataFrame:
        return (
            dframe[["DATE", vector, "SENSNAME_CASE"]]
            .groupby(["DATE", "SENSNAME_CASE"])
            .mean()
            .reset_index()
        )

    # pylint: disable=too-many-statements
    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            [
                Output(self.tornadoplot.storage_id, "data"),
            ],
            [
                Input(self.ids("ensemble"), "value"),
                Input(self.ids("graph"), "clickData"),
                Input(self.ids("vector"), "selectedNodes"),
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
            vector = vector[0]

            vector_df = self.vmodel.get_vector_df(
                ensemble=ensemble, realizations=self.realizations, vectors=[vector]
            )

            vector_df = vector_df.loc[vector_df["DATE"] == from_str(date)]

            return (
                json.dumps(
                    {
                        "ENSEMBLE": ensemble,
                        "data": vector_df[["REAL", vector]].values.tolist(),
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
            Input(self.tornadoplot.click_id, "data"),
            Input(self.tornadoplot.high_low_storage_id, "data"),
            Input(self.ids("sensitivity_filter"), "value"),
            Input(self.ids("visualization"), "value"),
            State(self.ids("ensemble"), "value"),
            State(self.ids("vector"), "selectedNodes"),
            State(self.ids("graph"), "clickData"),
            State(self.ids("graph"), "figure"),
        )
        def _render_tornado(  # pylint: disable=too-many-branches, too-many-locals
            tornado_click_data_str: Union[str, None],
            high_low_storage: dict,
            sensitivites,
            visualization,
            ensemble: str,
            vector: str,
            date_click: dict,
            figure: dict,
        ) -> dict:
            """Update graph with line coloring, vertical line and title"""
            if callback_context.triggered is None:
                raise PreventUpdate
            ctx = callback_context.triggered[0]["prop_id"].split(".")[0]
            vector = vector[0]
            tornado_click: Union[dict, None] = (
                json.loads(tornado_click_data_str) if tornado_click_data_str else None
            )
            if tornado_click:
                reset_click = tornado_click["sens_name"] is None
            else:
                reset_click = False
            print(ctx)
            # # Draw initial figure and redraw if ensemble/vector changes
            # if ctx in ["", self.tornadoplot.high_low_storage_id] or reset_click:

            realizations = list(
                self.parameter_df[self.parameter_df["SENSNAME"].isin(sensitivites)][
                    "REAL"
                ].unique()
            )
            # Update line colors if a sensitivity is selected in tornado
            # pylint: disable=too-many-nested-blocks
            #     if tornado_click and tornado_click["sens_name"] in high_low_storage:
            if tornado_click and ctx in [
                self.tornadoplot.click_id,
                self.tornadoplot.high_low_storage_id,
            ]:
                tornado_click["real_low"] = high_low_storage[
                    tornado_click["sens_name"]
                ].get("real_low")
                tornado_click["real_high"] = high_low_storage[
                    tornado_click["sens_name"]
                ].get("real_high")
                realizations = tornado_click["real_low"] + tornado_click["real_high"]
                print(realizations)

            # Get dataframe with vectors and dataframe with parameters and merge
            vector_df = self.vmodel.get_vector_df(
                ensemble=ensemble, realizations=realizations, vectors=[vector]
            )

            param_df = self.parameter_df[
                self.parameter_df["ENSEMBLE"] == ensemble
            ].copy()
            data = merge_dataframes_on_realization(dframe1=vector_df, dframe2=param_df)

            date = date_click["points"][0]["x"]

            if visualization == "sensmean":
                data = self.create_vectors_statistics_df(data, vector)

            figure = TimeSeriesFigure(
                dframe=data,
                visualization="realizations",
                vector=vector,
                ensemble=ensemble,
                dateline=from_str(date),
                historical_vector_df=self.vmodel.get_historical_vector_df(
                    vector, ensemble
                ),
                color_col="SENSNAME_CASE",
                line_shape_fallback=self.vmodel.line_shape_fallback,
                discrete_color=True,
                discrete_color_map=self.colormap,
                groupby="SENSNAME_CASE" if visualization == "sensmean" else "REAL",
            ).figure
            figure["layout"]["title"] = (
                f"Date: {date}, "
                f"Sensitivity: {tornado_click['sens_name'] if tornado_click else None}"
            )
            return figure


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=None)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_unit(smry_meta: Union[pd.DataFrame, None], vec: str) -> Union[str, None]:
    return None if smry_meta is None else simulation_unit_reformat(smry_meta.unit[vec])

from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple, Type

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, dcc, html
from dash.development.base_component import Component
from plotly.subplots import make_subplots
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.utils import calculate_slider_step
from webviz_config.webviz_store import webvizstore

import webviz_subsurface._utils.parameter_response as parresp
from webviz_subsurface._datainput.fmu_input import load_csv
from webviz_subsurface._figures import create_figure
from webviz_subsurface._models import ParametersModel
from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    EnsembleTableProviderFactory,
    EnsembleTableProviderSet,
    Frequency,
    get_matching_vector_names,
)

from ._error import error
from ._plugin_ids import PluginIds
from .views import Filter, ResponseView


class ParameterResponseCorrelation(WebvizPluginABC):
    """Visualizes correlations between numerical input parameters and responses.

---
**Three main options for input data: Aggregated, file per realization and read from `.arrow`.**

**Using aggregated data**
* **`parameter_csv`:** Aggregated csvfile for input parameters with `REAL` and `ENSEMBLE` columns \
(absolute path or relative to config file).
* **`response_csv`:** Aggregated csvfile for response parameters with `REAL` and `ENSEMBLE` \
columns (absolute path or relative to config file).


**Using a response file per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`response_file`:** Local (per realization) csv file for response parameters (Cannot be \
                    combined with `response_csv` and `parameter_csv`).


**Using simulation time series data directly from `UNSMRY` files as responses**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize. The lack of `response_file` \
                implies that the input data should be time series data from `.arrow` file \
* **`rel_file_pattern`:** Relative file path to `.arrow` file.
* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading \
                from UNSMRY-files in the defined ensembles (default is all vectors). * can be \
                used as wild card.
* **`sampling`:** (Optional) sampling frequency when reading simulation data directly from \
               `.UNSMRY`-files (default is monthly).

?> The `.arrow` input method implies that the "DATE" vector will be used as a filter \
   of type `single` (as defined below under `response_filters`).


**Common settings for all input options**

All of these are optional, some have defaults seen in the code snippet below.

* **`response_filters`:** Optional dictionary of responses (columns in csv file or simulation \
                       vectors) that can be used as row filtering before aggregation. \
                       Valid options:
    * `single`: Dropdown with single selection.
    * `multi`: Dropdown with multiple selection.
    * `range`: Slider with range selection.
* **`response_ignore`:** List of response (columns in csv or simulation vectors) to ignore \
                      (cannot use with response_include).
* **`response_include`:** List of response (columns in csv or simulation vectors) to include \
                       (cannot use with response_ignore).
* **`aggregation`:** Initial way to aggregate responses per realization. Either `sum` or `mean`.
* **`corr_method`:** Initial correlation method. Either `pearson` or `spearman`.

---

?> Non-numerical (string-based) input parameters and responses are removed.

?> The responses will be aggregated per realization; meaning that if your filters do not reduce \
the response to a single value per realization in your data, the values will be aggregated \
accoording to your defined `aggregation`. If e.g. the response is a form of volume, \
and the filters are regions (or other subdivisions of the total volume), then `sum` would \
be a natural aggregation. If on the other hand the response is the pressures in the \
same volume, aggregation as `mean` over the subdivisions of the same volume \
would make more sense (though the pressures in this case would not be volume weighted means, \
and the aggregation would therefore likely be imprecise).

!> It is **strongly recommended** to keep the data frequency to a regular frequency (like \
`monthly` or `yearly`). This applies to both csv input and when reading from `.arrow` \
(controlled by the `sampling` key). This is because the statistics are calculated per DATE over \
all realizations in an ensemble, and the available dates should therefore not differ between \
individual realizations of an ensemble.

**Using aggregated data**

The `parameter_csv` file must have columns `REAL`, `ENSEMBLE` and the parameter columns.

The `response_csv` file must have columns `REAL`, `ENSEMBLE` and the response columns \
(and the columns to use as `response_filters`, if that option is used).


**Using a response file per realization**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations, using the `fmu-ensemble` library.

The `response_file` must have the response columns (and the columns to use as `response_filters`, \
if that option is used).


**Using simulation time series data directly from `.arrow` files as responses**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations.

Responses are extracted automatically from the `.arrow` files in the individual realizations.
"""

    # pylint:disable=too-many-arguments, too-many-locals
    def __init__(
        self,
        app,
        webviz_settings: WebvizSettings,
        parameter_csv: Path = None,
        response_csv: Path = None,
        ensembles: list = None,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        response_file: str = None,
        response_filters: dict = None,
        response_ignore: list = None,
        response_include: list = None,
        column_keys: list = None,
        sampling: str = "monthly",
        aggregation: str = "sum",
        corr_method: str = "pearson",
    ):

        super().__init__()

        self.parameter_csv = parameter_csv if parameter_csv else None
        self.response_csv = response_csv if response_csv else None
        self.response_file = response_file if response_file else None
        self.response_filters = response_filters if response_filters else {}
        self.column_keys = column_keys
        self._sampling = Frequency(sampling)
        self.corr_method = corr_method
        self.aggregation = aggregation
        if response_ignore and response_include:
            raise ValueError(
                'Incorrent argument. either provide "response_include", '
                '"response_ignore" or neither'
            )
        if parameter_csv and response_csv:
            if ensembles or response_file:
                raise ValueError(
                    'Incorrect arguments. Either provide "csv files" or '
                    '"ensembles and response_file".'
                )
            parameterdf = read_csv(self.parameter_csv)
            self.responsedf = read_csv(self.response_csv)

        elif ensembles:
            self.ens_paths = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }
            table_provider_factory = EnsembleTableProviderFactory.instance()
            parameterdf = create_df_from_table_provider(
                table_provider_factory.create_provider_set_from_per_realization_parameter_file(
                    self.ens_paths
                )
            )
            if self.response_file:
                self.responsedf = load_csv(
                    ensemble_paths=self.ens_paths,
                    csv_file=response_file,
                    ensemble_set_name="EnsembleSet",
                )
            else:
                smry_provider_factory = EnsembleSummaryProviderFactory.instance()
                provider_set = {
                    ens_name: smry_provider_factory.create_from_arrow_unsmry_presampled(
                        ens_path, rel_file_pattern, self._sampling
                    )
                    for ens_name, ens_path in self.ens_paths.items()
                }
                self.response_filters["DATE"] = "single"
                self.responsedf = create_df_from_summary_provider(
                    provider_set,
                    self.column_keys,
                )
        else:
            raise ValueError(
                'Incorrect arguments. Either provide "csv files" or "ensembles and response_file".'
            )
        pmodel = ParametersModel(
            dataframe=parameterdf, keep_numeric_only=True, drop_constants=True
        )
        self.parameterdf = pmodel.dataframe
        self.parameter_columns = pmodel.parameters

        parresp.check_runs(self.parameterdf, self.responsedf)
        parresp.check_response_filters(self.responsedf, self.response_filters)

        # Only select numerical responses
        self.response_columns = parresp.filter_numerical_columns(
            df=self.responsedf,
            column_ignore=response_ignore,
            column_include=response_include,
            filter_columns=self.response_filters.keys(),
        )

        self.theme = webviz_settings.theme
        self.error_message = ""

        # add views
        self.add_store(
            PluginIds.Stores.INITIAL_PARAMETER, WebvizPluginABC.StorageType.SESSION
        )

        """self.add_shared_settings_group(
            Filter(
                self.responsedf,
                self.ensembles,
                self.response_filters,
                self.parameter_columns,
                self.response_columns,
                self.aggregation,
                self.corr_method,
            ),
            PluginIds.SharedSettings.FILTER,
        )"""

        self.add_view(
            ResponseView(
                self.responsedf,
                webviz_settings,
                self.ensembles,
                self.response_filters,
                self.parameter_columns,
                self.response_columns,
                self.aggregation,
                self.corr_method,
                self.parameterdf,
            ),
            PluginIds.ResponseID.RESPONSE_CHART,
        )

    @property
    def tour_steps(self) -> List[Dict[str, Any]]:
        steps = [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard displaying correlation between selected "
                    "response and input parameters."
                ),
            },
            {
                "id": self.uuid("correlation-graph"),
                "content": (
                    "Visualization of the correlations between currently selected "
                    "response and input parameters ranked by the absolute correlation "
                    "coefficient. Click on any correlation to visualize the distribution "
                    "between that parameter and the response."
                ),
            },
            {
                "id": self.uuid("distribution-graph"),
                "content": (
                    "Visualization of the distribution of the response and the selected "
                    "input parameter in the correlation chart."
                ),
            },
            {
                "id": self.uuid("ensemble"),
                "content": ("Select the active ensemble."),
            },
            {
                "id": self.uuid("responses"),
                "content": ("Select the active response."),
            },
            {
                "id": self.uuid("correlation-method"),
                "content": ("Select Pearson or Spearman correlation."),
            },
            {
                "id": self.uuid("aggregation"),
                "content": (
                    "Select whether the response after filtering should be aggregated "
                    "by summation or mean."
                ),
            },
            {
                "id": self.uuid("correlation-cutoff"),
                "content": (
                    "Slider to set a minimum correlation factor for parameters shown "
                    "in plots."
                ),
            },
            {
                "id": self.uuid("max-params"),
                "content": ("Slider to set a maximum number of parameters shown"),
            },
            {
                "id": self.uuid("filters"),
                "content": ("Filters for response and parameters to correlate with."),
            },
        ]

        return steps

    @property
    def ensembles(self) -> List[str]:
        """Returns list of ensembles"""
        return list(self.parameterdf["ENSEMBLE"].unique())

    @property
    def layout(self) -> Type[Component]:
        """Main layout"""
        return error(self.error_message)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)


def create_df_from_table_provider(provider: EnsembleTableProviderSet) -> pd.DataFrame:
    """Aggregates parameters from all ensemble into a common dataframe."""
    dfs = []
    for ens in provider.ensemble_names():
        df = provider.ensemble_provider(ens).get_column_data(
            column_names=provider.ensemble_provider(ens).column_names()
        )
        df["ENSEMBLE"] = df.get("ENSEMBLE", ens)
        dfs.append(df)
    return pd.concat(dfs)


def create_df_from_summary_provider(
    provider_set: Dict[str, EnsembleSummaryProvider], column_keys: List[str]
) -> pd.DataFrame:
    """Aggregates summary data from all ensembles into a common dataframe."""
    dfs = []
    for ens_name, provider in provider_set.items():
        matching_sumvecs = get_matching_vector_names(provider, column_keys)
        if not matching_sumvecs:
            raise ValueError(
                f"No vectors matching the given column_keys: {column_keys} for ensemble: {ens_name}"
            )
        df = provider.get_vectors_df(matching_sumvecs, None)
        df["ENSEMBLE"] = ens_name
        dfs.append(df)

    df_all = pd.concat(dfs)
    df_all["DATE"] = pd.to_datetime(df_all["DATE"]).dt.strftime("%Y-%m-%d")
    return df_all

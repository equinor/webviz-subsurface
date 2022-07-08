from pathlib import Path

import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, html
from dash.exceptions import PreventUpdate
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

import webviz_subsurface._utils.parameter_response as parresp
from webviz_subsurface._models import (
    EnsembleSetModel,
    caching_ensemble_set_model_factory,
)

from ._plugin_ids import PluginIds
from .shared_settings import Filter
from .views import EnsembleView


class ParameterParallelCoordinates(WebvizPluginABC):
    """Visualizes parameters used in FMU ensembles side-by-side. Also supports response coloring.

Useful to investigate:
* Initial parameter distributions, and convergence of parameters over multiple iterations.
* Trends in relations between parameters and responses.

!> At least two parameters have to be selected to make the plot work.

---
**Three main options for input data: Aggregated, file per realization and read from UNSMRY.**

**Using aggregated data**
* **`parameter_csv`:** Aggregated csvfile for input parameters with `REAL` and `ENSEMBLE` columns \
(absolute path or relative to config file).
* **`response_csv`:** Aggregated csvfile for response parameters with `REAL` and `ENSEMBLE` \
columns (absolute path or relative to config file).


**Using a response file per realization**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`response_file`:** Local (per realization) csv file for response parameters (Cannot be \
                    combined with `response_csv` and `parameter_csv`).
* Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

**Using simulation time series data directly from `UNSMRY` files as responses**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize. The lack of `response_file` \
                implies that the input data should be time series data from simulation `.UNSMRY` \
                files, read using `fmu-ensemble`.
* **`column_keys`:** (Optional) slist of simulation vectors to include as responses when reading \
                from UNSMRY-files in the defined ensembles (default is all vectors). * can be \
                used as wild card.
* **`sampling`:** (Optional) sampling frequency when reading simulation data directly from \
               `.UNSMRY`-files (default is monthly).
* Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

?> The `UNSMRY` input method implies that the "DATE" vector will be used as a filter \
   of type `single` (as defined below under `response_filters`).

**Using the plugin without responses**
It is possible to use the plugin with only parameter data, in that case set the option \
`no_responses` to True, and give either `ensembles` or `parameter_csv` as input as described \
above. Response coloring and filtering will then not be available.

**Common settings for responses**
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
* **`aggregation`:** How to aggregate responses per realization. Either `sum` or `mean`.

Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations of your defined `ensembles`, using the `fmu-ensemble` library.

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
`monthly` or `yearly`). This applies to both csv input and when reading from `UNSMRY` \
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


**Using simulation time series data directly from `UNSMRY` files as responses**

Parameters are extracted automatically from the `parameters.txt` files in the individual
realizations, using the `fmu-ensemble` library.

Responses are extracted automatically from the `UNSMRY` files in the individual realizations,
using the `fmu-ensemble` library.

!> The `UNSMRY` files are auto-detected by `fmu-ensemble` in the `eclipse/model` folder of the \
individual realizations. You should therefore not have more than one `UNSMRY` file in this \
folder, to avoid risk of not extracting the right data.

"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list = None,
        parameter_csv: Path = None,
        response_csv: Path = None,
        response_file: str = None,
        response_filters: dict = None,
        response_ignore: list = None,
        response_include: list = None,
        parameter_ignore: list = None,
        column_keys: list = None,
        sampling: str = "monthly",
        aggregation: str = "sum",
        no_responses=False,
    ):

        super().__init__()

        self.parameter_csv = parameter_csv if parameter_csv else None
        self.response_csv = response_csv if response_csv else None
        self.response_file = response_file if response_file else None
        self.response_filters = response_filters if response_filters else {}
        self.column_keys = column_keys
        self.time_index = sampling
        self.aggregation = aggregation
        self.no_responses = no_responses
        self.response_columns = []

        if response_ignore and response_include:
            raise ValueError(
                'Incorrent argument. Either provide "response_include", '
                '"response_ignore" or neither'
            )
        if parameter_csv:
            if ensembles or response_file:
                raise ValueError(
                    'Incorrect arguments. Either provide "parameter_csv" or '
                    '"ensembles and/or response_file".'
                )
            if not self.no_responses:
                if self.response_csv:
                    self.responsedf = read_csv(self.response_csv)
                else:
                    raise ValueError("Incorrect arguments. Missing response_csv.")
            self.parameterdf = read_csv(self.parameter_csv)

        elif ensembles:
            if self.response_csv:
                raise ValueError(
                    'Incorrect arguments. Either provide "response_csv" or '
                    '"ensembles and/or response_file".'
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
            self.parameterdf = self.emodel.load_parameters()
            if not self.no_responses:
                if self.response_file:
                    self.responsedf = self.emodel.load_csv(csv_file=response_file)
                else:
                    self.responsedf = self.emodel.get_or_load_smry_cached()
                    self.response_filters["DATE"] = "single"
        else:
            raise ValueError(
                "Incorrect arguments."
                'You have to define at least "ensembles" or "parameter_csv".'
            )

        if not self.no_responses:
            parresp.check_runs(parameterdf=self.parameterdf, responsedf=self.responsedf)
            parresp.check_response_filters(
                responsedf=self.responsedf, response_filters=self.response_filters
            )
            # only select numerical responses
            self.response_columns = parresp.filter_numerical_columns(
                df=self.responsedf,
                column_ignore=response_ignore,
                column_include=response_include,
                filter_columns=self.response_filters.keys(),
            )

        # Only select numerical parameters
        self.parameter_columns = parresp.filter_numerical_columns(
            df=self.parameterdf, column_ignore=parameter_ignore
        )

        self.theme = webviz_settings.theme

        # Stores, views and settings
        self.add_store(
            PluginIds.Stores.SELECTED_ENSEMBLE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_EXCLUDE_INCLUDE,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PluginIds.Stores.SELECTED_PARAMETERS, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_RESPONSE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PluginIds.Stores.SELECTED_DATE, WebvizPluginABC.StorageType.SESSION
        )

        self.add_shared_settings_group(
            Filter(self.parameterdf, self.ensembles, self.parameter_columns),
            PluginIds.SharedSettings.FILTER,
        )

        self.add_view(
            EnsembleView(
                self.parameterdf,
                self.theme,
                self.parameter_columns,
                self.ensembles,
                self.ens_colormap,
            ),
            PluginIds.ParallelID.ENSEMBLE_CHART,
        )

    @property
    def ensembles(self):
        """Returns list of ensembles"""
        return list(self.parameterdf["ENSEMBLE"].unique())

    @property
    def ens_colormap(self):
        """Returns a discrete colormap with one color per ensemble"""
        colors = self.theme.plotly_theme["layout"]["colorway"]
        colormap = []
        for i in range(0, len(self.ensembles)):
            colormap.append([i / len(self.ensembles), colors[i]])
            colormap.append([(i + 1) / len(self.ensembles), colors[i]])

        return colormap

    @property
    def layout(self):
        """Main layout"""
        return wcc.FlexBox(
            id=self.uuid("layout"),
            style={"height": "90vh"},
        )

    def add_webvizstore(self):
        functions = []
        if self.parameter_csv:
            functions.append(
                (
                    read_csv,
                    [
                        {
                            "csv_file": self.parameter_csv,
                        }
                    ],
                )
            )
            if self.response_csv:
                functions.append(
                    (
                        read_csv,
                        [
                            {
                                "csv_file": self.response_csv,
                            }
                        ],
                    )
                )
        else:
            functions.extend(self.emodel.webvizstore)

        return functions


def render_parcoord(plot_df, theme, colormap, color_col, ens, mode, params, response):
    """Renders parallel coordinates plot"""
    colormap = (
        colormap if mode == "ensemble" else theme.plotly_theme["layout"]["colorway"]
    )
    if response:
        response = f"Response: {response}"
        params = [response] + params
    # Create parcoords dimensions (one per parameter)
    dimensions = [{"label": param, "values": plot_df[param]} for param in params]
    data = [
        {
            "line": {
                "color": plot_df[color_col].values.tolist(),
                "colorscale": colormap,
                "cmin": -0.5,
                "cmax": len(ens) - 0.5,
                "showscale": True,
                "colorbar": {
                    "tickvals": list(range(0, len(ens))),
                    "ticktext": ens,
                    "title": "Ensemble",
                    "xanchor": "right",
                    "x": -0.02,
                    "len": 0.2 * len(ens),
                },
            },
            "dimensions": dimensions,
            "labelangle": 60,
            "labelside": "bottom",
            "type": "parcoords",
        }
        if mode == "ensemble"
        else {
            "type": "parcoords",
            "line": {
                "color": plot_df[response],
                "colorscale": colormap,
                "showscale": True,
                "colorbar": {
                    "title": {"text": response},
                    "xanchor": "right",
                    "x": -0.02,
                },
            },
            "dimensions": dimensions,
            "labelangle": 60,
            "labelside": "bottom",
        }
        if mode == "response"
        else {}
    ]

    # Ensure sufficient spacing between each dimension and margin for labels
    width = len(dimensions) * 80 + 250
    layout = {"width": width, "height": 1200, "margin": {"b": 740, "t": 30}}
    return {"data": data, "layout": theme.create_themed_layout(layout)}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file) -> pd.DataFrame:
    return pd.read_csv(csv_file, index_col=False)

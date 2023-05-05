from typing import Dict

import pandas as pd
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from webviz_subsurface._models.parameter_model import ParametersModel
from webviz_subsurface._providers import (
    EnsembleSummaryProviderFactory,
    EnsembleTableProviderFactory,
    EnsembleTableProvider,
    Frequency,
)

from ._views._onebyone_view import OneByOneView
# from ._business_logic import SimulationTimeSeriesOneByOneDataModel
# from ._callbacks import plugin_callbacks
# from ._layout import main_view
# from .models import ProviderTimeSeriesDataModel


class SimulationTimeSeriesOneByOne(WebvizPluginABC):
    """Visualizes reservoir simulation time series data for sensitivity studies based \
on a design matrix.
A tornado plot can be calculated interactively for each date/vector by selecting a date.
After selecting a date individual sensitivities can be selected to highlight the realizations
run with that sensitivity.
---
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
**Using simulation time series data directly from `.UNSMRY` files**
Time series data are extracted automatically from the `UNSMRY` files in the individual
realizations, using the `fmu-ensemble` library. The `SENSNAME` and `SENSCASE` values are read
directly from the `parameters.txt` files of the individual realizations, assuming that these
exist. If the `SENSCASE` of a realization is `p10_p90`, the sensitivity case is regarded as a
**Monte Carlo** style sensitivity, otherwise the case is evaluated as a **scalar** sensitivity.
?> Using the `UNSMRY` method will also extract metadata like units, and whether the vector is a \
rate, a cumulative, or historical. Units are e.g. added to the plot titles, while rates and \
cumulatives are used to decide the line shapes in the plot.
"""
    class Ids(StrEnum):
        ONEBYONE_VIEW = "onebyone-view"

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        time_index: str = "monthly",
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        column_keys: list = None,
        initial_vector: str = None,
        line_shape_fallback: str = "linear",
    ) -> None:

        super().__init__()

        # vectormodel: ProviderTimeSeriesDataModel
        table_provider = EnsembleTableProviderFactory.instance()
        provider_factory = EnsembleSummaryProviderFactory.instance()
        resampling_frequency = Frequency(time_index)

        ensemble_paths = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }
        try:
            provider_set = {
                ens: provider_factory.create_from_arrow_unsmry_presampled(
                    str(ens_path), rel_file_pattern, resampling_frequency
                )
                for ens, ens_path in ensemble_paths.items()
            }
            # vectormodel = ProviderTimeSeriesDataModel(
            #     provider_set=provider_set,
            #     column_keys=column_keys,
            #     line_shape_fallback=line_shape_fallback,
            # )
        except ValueError as error:
            message = (
                f"Some/all ensembles are missing arrow files at {rel_file_pattern}.\n"
                "If no arrow files have been generated with `ERT` using `ECL2CSV`, "
                "the commandline tool `smry2arrow_batch` can be used to generate arrow "
                "files for an ensemble"
            )
            raise ValueError(message) from error

        parameterproviderset = {
            ens_name: table_provider.create_from_per_realization_parameter_file(
                ens_path
            )
            for ens_name, ens_path in ensemble_paths.items()
        }
        parameter_df = create_df_from_table_provider(parameterproviderset)

        parametermodel = ParametersModel(dataframe=parameter_df, drop_constants=True)
        # self.datamodel = SimulationTimeSeriesOneByOneDataModel(
        #     vectormodel=vectormodel,
        #     parametermodel=parametermodel,
        #     webviz_settings=webviz_settings,
        #     initial_vector=initial_vector,
        # )

        self.add_view(
            OneByOneView(
                provider_set=provider_set,
                parameter_model=parametermodel
            ),
            self.Ids.ONEBYONE_VIEW,
        )

    # @property
    # def tour_steps(self) -> List[dict]:
    #     return [
    #         {
    #             "id": self.uuid("layout"),
    #             "content": (
    #                 "Dashboard displaying time series from a sensitivity study."
    #             ),
    #         },
    #         {
    #             "id": self.uuid("graph-wrapper"),
    #             "content": (
    #                 "Selected time series displayed per realization. "
    #                 "Click in the plot to calculate tornadoplot for the "
    #                 "corresponding date, then click on the tornado plot to "
    #                 "highlight the corresponding sensitivity."
    #             ),
    #         },
    #         {
    #             "id": self.uuid("table"),
    #             "content": (
    #                 "Table statistics for all sensitivities for the selected date."
    #             ),
    #         },
    #         {"id": self.uuid("vector"), "content": "Select time series"},
    #         {"id": self.uuid("ensemble"), "content": "Select ensemble"},
    #     ]


def create_df_from_table_provider(
    providerset: Dict[str, EnsembleTableProvider]
) -> pd.DataFrame:
    dfs = []
    for ens, provider in providerset.items():
        df = provider.get_column_data(column_names=provider.column_names())
        df["ENSEMBLE"] = ens
        dfs.append(df)
    return pd.concat(dfs)
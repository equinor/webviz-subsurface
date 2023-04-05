from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from webviz_subsurface._providers import (
    EnsembleSummaryProviderFactory,
    EnsembleTableProvider,
    EnsembleTableProviderFactory,
    Frequency,
)

from ..._utils.simulation_timeseries import check_and_format_observations
from ..._utils.webvizstore_functions import get_path
from ._utils import ParametersModel, ProviderTimeSeriesDataModel
from ._views._parameter_distributions_view import ParameterDistributionView
from ._views._parameter_response_view import ParameterResponseView


class ParameterAnalysis(WebvizPluginABC):
    """This plugin visualizes parameter distributions and statistics.
for FMU ensembles, and can be used to investigate parameter correlations
on reservoir simulation time series data.

---

**Using raw ensemble data stored in realization folders**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`rel_file_pattern`:** path to `.arrow` files with summary data.
* **`time_index`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.
* **`drop_constants`:** Bool used to determine if constant parameters should be dropped. \
    Default is True.
* **`column_keys`:** List of vectors to extract. If not given, all vectors \
    from the simulations will be extracted. Wild card asterisk `*` can be used.
* **`obsfile`:** `.yaml` file with observations to be displayed in the time series plot \
* **`perform_presampled`:** Summary data will be presampled when loading the plugin, \
    and the resampling dropdown will be disabled.
---

?> `Arrow` format for simulation time series data can be generated using the `ECL2CSV` forward \
model in ERT. On existing ensembles the command line tool `smry2arrow_batch` can be used to \
generate arrow files.

!> For smry data it is **strongly recommended** to keep the data frequency to a regular frequency \
(like `monthly` or `yearly`). This is because the statistics are calculated \
per DATE over all realizations in an ensemble, and the available dates should therefore not \
differ between individual realizations of an ensemble.

?> Vectors that are identified as historical vectors (e.g. FOPTH is the history of FOPT) will \
be plotted together with their non-historical counterparts as reference lines.

!> Parameter values are extracted automatically from the `parameters.txt` files in the individual
realizations if you have defined `ensembles`.


"""

    class Ids(StrEnum):
        PARAM_DIST_VIEW = "param-dist-view"
        PARAM_RESP_VIEW = "param-resp-view"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: List[str] = None,
        time_index: str = Frequency.MONTHLY.value,
        column_keys: Optional[list] = None,
        drop_constants: bool = True,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        obsfile: Path = None,
        perform_presampling: bool = False,
    ):
        super().__init__()

        self._ensembles = ensembles
        self._theme = webviz_settings.theme
        self._obsfile = obsfile

        self._observations = {}
        if self._obsfile:
            self._observations = check_and_format_observations(get_path(self._obsfile))

        if ensembles is None:
            raise ValueError('Incorrect argument, must provide "ensembles"')

        ensemble_paths: Dict[str, str] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        table_provider_factory = EnsembleTableProviderFactory.instance()

        resampling_frequency = Frequency(time_index)
        provider_factory = EnsembleSummaryProviderFactory.instance()

        if perform_presampling:
            self._input_provider_set = {
                ens: provider_factory.create_from_arrow_unsmry_presampled(
                    str(ens_path), rel_file_pattern, resampling_frequency
                )
                for ens, ens_path in ensemble_paths.items()
            }
        else:
            self._input_provider_set = {
                ens: provider_factory.create_from_arrow_unsmry_lazy(
                    str(ens_path), rel_file_pattern
                )
                for ens, ens_path in ensemble_paths.items()
            }

        self._vmodel = ProviderTimeSeriesDataModel(
            provider_set=self._input_provider_set, column_keys=column_keys
        )
        self._vmodel.set_dates(
            self._vmodel.get_dates(resampling_frequency=resampling_frequency)
        )

        parameter_df = create_df_from_table_provider(
            provider_set={
                ens_name: table_provider_factory.create_from_per_realization_parameter_file(
                    ens_path
                )
                for ens_name, ens_path in ensemble_paths.items()
            }
        )

        self._pmodel = ParametersModel(
            dataframe=parameter_df,
            theme=self._theme,
            drop_constants=drop_constants,
        )

        self.add_view(
            ParameterResponseView(
                parametermodel=self._pmodel,
                vectormodel=self._vmodel,
                observations=self._observations,
                selected_resampling_frequency=resampling_frequency,
                disable_resampling_dropdown=perform_presampling,
                theme=self._theme,
            ),
            self.Ids.PARAM_RESP_VIEW,
        )
        self.add_view(
            ParameterDistributionView(self._pmodel),
            self.Ids.PARAM_DIST_VIEW,
        )


def create_df_from_table_provider(
    provider_set: Dict[str, EnsembleTableProvider]
) -> pd.DataFrame:
    """Aggregates parameters from all ensemble into a common dataframe."""
    dfs = []
    for ens_name, provider in provider_set.items():
        df = provider.get_column_data(column_names=provider.column_names())
        df["ENSEMBLE"] = ens_name
        dfs.append(df)
    return pd.concat(dfs)

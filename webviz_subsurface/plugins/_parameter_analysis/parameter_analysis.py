from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
from dash import dcc
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.deprecation_decorators import deprecated_plugin_arguments

from webviz_subsurface._providers import (
    EnsembleSummaryProviderFactory,
    EnsembleTableProviderFactory,
    Frequency,
)

from .controllers import parameter_qc_controller, parameter_response_controller
from .models import (
    ParametersModel,
    ProviderTimeSeriesDataModel,
    SimulationTimeSeriesModel,
)
from .views import main_view


def check_deprecation_argument(
    csvfile_parameters: Optional[Path], csvfile_smry: Optional[Path]
) -> Optional[Tuple[str, str]]:
    if any(elm is not None for elm in [csvfile_parameters, csvfile_smry]):
        return (
            "The usage of aggregated csvfiles as user input options are deprecated. "
            "Please provide feedback if you see a need for a continuation "
            "of this functionality ",
            "",
        )
    return None


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

    # pylint: disable=too-many-arguments, too-many-locals
    @deprecated_plugin_arguments(check_deprecation_argument)
    def __init__(
        self,
        app,
        webviz_settings: WebvizSettings,
        ensembles: Optional[list] = None,
        time_index: str = "monthly",
        column_keys: Optional[list] = None,
        drop_constants: bool = True,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        csvfile_parameters: Optional[Path] = None,
        csvfile_smry: Optional[Path] = None,
    ):
        super().__init__()

        self.theme = webviz_settings.theme
        self.ensembles = ensembles

        table_provider = EnsembleTableProviderFactory.instance()

        if ensembles is not None:
            ensemble_paths = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }

            resampling_frequency = Frequency(time_index)
            provider_factory = EnsembleSummaryProviderFactory.instance()

            provider_set = {}
            for ens, ens_path in ensemble_paths.items():
                try:
                    provider_set[
                        ens
                    ] = provider_factory.create_from_arrow_unsmry_presampled(
                        str(ens_path), rel_file_pattern, resampling_frequency
                    )
                except ValueError as error:
                    message = (
                        f"No arrow files found at {rel_file_pattern} for ensemble {ens}. \n"
                        "If no arrow files have been generated with `ERT` using `ECL2CSV`, "
                        "the commandline tool `smry2arrow_batch` can be used to generate arrow "
                        "files for an ensemble"
                    )
                    raise ValueError(message) from error

            self.vmodel = ProviderTimeSeriesDataModel(
                provider_set=provider_set, column_keys=column_keys
            )

            parameterproviderset = (
                table_provider.create_provider_set_from_per_realization_parameter_file(
                    ensemble_paths
                )
            )

        elif csvfile_parameters is None:
            raise ValueError("Either ensembles or csvfile_parameters must be specified")
        else:
            parameterproviderset = (
                table_provider.create_provider_set_from_aggregated_csv_file(
                    csvfile_parameters
                )
            )
            if csvfile_smry is not None:
                smryprovider = (
                    table_provider.create_provider_set_from_aggregated_csv_file(
                        csvfile_smry
                    )
                )
                self.vmodel = SimulationTimeSeriesModel(
                    dataframe=create_df_from_table_provider(smryprovider)
                )
            else:
                self.vmodel = None

        self.pmodel = ParametersModel(
            dataframe=create_df_from_table_provider(parameterproviderset),
            theme=self.theme,
            drop_constants=drop_constants,
        )

        self.set_callbacks(app)

    @property
    def layout(self) -> dcc.Tabs:
        return main_view(
            get_uuid=self.uuid,
            vectormodel=self.vmodel,
            parametermodel=self.pmodel,
            theme=self.theme,
        )

    def set_callbacks(self, app) -> None:
        parameter_qc_controller(app=app, get_uuid=self.uuid, parametermodel=self.pmodel)
        if self.vmodel is not None:
            parameter_response_controller(
                app=app,
                get_uuid=self.uuid,
                parametermodel=self.pmodel,
                vectormodel=self.vmodel,
            )


def create_df_from_table_provider(provider) -> pd.DataFrame:
    dfs = []
    for ens in provider.ensemble_names():
        df = provider.ensemble_provider(ens).get_column_data(
            column_names=provider.ensemble_provider(ens).column_names()
        )
        df["ENSEMBLE"] = df.get("ENSEMBLE", ens)
        dfs.append(df)
    return pd.concat(dfs)

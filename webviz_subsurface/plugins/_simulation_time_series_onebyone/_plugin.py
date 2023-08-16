from pathlib import Path
from typing import Dict

from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from webviz_subsurface._models.parameter_model import ParametersModel
from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.ensemble_summary_provider_set_factory import (
    create_lazy_ensemble_summary_provider_set_from_paths,
    create_presampled_ensemble_summary_provider_set_from_paths,
)
from webviz_subsurface._utils.ensemble_table_provider_set_factory import (
    create_parameter_providerset_from_paths,
)

from ._utils import SimulationTimeSeriesOneByOneDataModel
from ._views._onebyone_view import OneByOneView


class SimulationTimeSeriesOneByOne(WebvizPluginABC):
    """Visualizes reservoir simulation time series data for sensitivity studies based \
on a design matrix.
A tornado plot can be calculated interactively for each date/vector by selecting a date.
After selecting a date individual sensitivities can be selected to highlight the realizations
run with that sensitivity.
---
**Input arguments**
* **`ensembles`:** Which ensembles in `shared_settings` to visualize.
* **`rel_file_pattern`:** Path to `.arrow` files with summary data.
* **`sampling`:** Time separation between extracted values. Can be e.g. `monthly` (default) or \
    `yearly`.
* **`perform_presampling`:** Presample summary data instead of lazy sampling.
* **`initial_vector`:** Initial vector to display
* **`line_shape_fallback`:** Fallback interpolation method between points. Vectors identified as \
    rates or phase ratios are always backfilled, vectors identified as cumulative (totals) are \
    always linearly interpolated. The rest use the fallback.
    Supported options:
    * `linear` (default)
    * `backfilled`
    * `hv`, `vh`, `hvh`, `vhv` and `spline` (regular Plotly options).
"""

    class Ids(StrEnum):
        ONEBYONE_VIEW = "onebyone-view"

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        sampling: str = Frequency.MONTHLY.value,
        perform_presampling: bool = False,
        initial_vector: str = None,
        line_shape_fallback: str = "linear",
    ) -> None:
        super().__init__()

        # vectormodel: ProviderTimeSeriesDataModel
        resampling_frequency = Frequency(sampling)

        if ensembles is not None:
            ensemble_paths: Dict[str, Path] = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }
            if perform_presampling:
                self._presampled_frequency = resampling_frequency
                summary_provider_set = (
                    create_presampled_ensemble_summary_provider_set_from_paths(
                        ensemble_paths, rel_file_pattern, self._presampled_frequency
                    )
                )
            else:
                summary_provider_set = (
                    create_lazy_ensemble_summary_provider_set_from_paths(
                        ensemble_paths, rel_file_pattern
                    )
                )
        else:
            raise ValueError('Incorrect argument, must provide "ensembles"')

        if not summary_provider_set:
            raise ValueError(
                "Initial provider set is undefined, and ensemble summary providers"
                " are not instantiated for plugin"
            )

        parameter_provider_set = create_parameter_providerset_from_paths(ensemble_paths)
        parameter_df = parameter_provider_set.get_aggregated_dataframe()
        parametermodel = ParametersModel(dataframe=parameter_df, drop_constants=True)

        self.add_view(
            OneByOneView(
                data_model=SimulationTimeSeriesOneByOneDataModel(
                    provider_set=summary_provider_set,
                    parametermodel=parametermodel,
                    webviz_settings=webviz_settings,
                    resampling_frequency=resampling_frequency,
                    initial_vector=initial_vector,
                    line_shape_fallback=line_shape_fallback,
                ),
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

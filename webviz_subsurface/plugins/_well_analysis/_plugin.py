from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from ..._models import GruptreeModel, WellAttributesModel
from ..._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)
from ._utils import EnsembleWellAnalysisData
from ._views._well_control_view import WellControlView, WellControlViewElement
from ._views._well_overview_view import WellOverviewView, WellOverviewViewElement


class WellAnalysis(WebvizPluginABC):
    """This plugin is for visualizing and analysing well data. There are different tabs
    for visualizing:

    * Well Production
    * Well control modes and network pressures

    ---
    * **`ensembles`:** Which ensembles in `shared_settings` to include.
    * **`rel_file_pattern`:** path to `.arrow` files with summary data.
    * **`gruptree_file`:** `.csv` with gruptree information.
    * **`time_index`:** Frequency for the data sampling.
    * **`filter_out_startswith`:** Filter out wells that starts with this string
    ---

    **Summary data**

    This plugin needs the following summary vectors to be exported:
    * WOPT, WGPT and WWPT for all wells for the well overview plots
    * WMCTL, WTHP and WBHP for all wells for the well control plots
    * GPR for all network nodes downstream/upstream the wells

    **GRUPTREE input**

    `gruptree_file` is a path to a file stored per realization (e.g. in \
    `share/results/tables/gruptree.csv"`).

    The `gruptree_file` file can be dumped to disk per realization by the `ECL2CSV` forward
    model with subcommand `gruptree`. The forward model uses `ecl2df` to export a table
    representation of the Eclipse network:
    [Link to ecl2csv gruptree documentation.](https://equinor.github.io/ecl2df/usage/gruptree.html).

    **time_index**

    This is the sampling interval of the summary data. It is `yearly` by default, but can be set
    to f.ex `monthly` if needed.

    **filter_out_startswith**

    Filter out well names that starts with this. Can f.ex be "R_" in order to filter out RFT wells
    without production.

    """

    class Ids(StrEnum):
        WELL_OVERVIEW = "well-overview"
        WELL_CONTROL = "well-control"

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: Optional[List[str]] = None,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        gruptree_file: str = "share/results/tables/gruptree.csv",
        well_attributes_file: str = "rms/output/wells/well_attributes.json",
        time_index: str = Frequency.YEARLY.value,
        filter_out_startswith: Optional[str] = None,
    ) -> None:
        super().__init__(stretch=True)

        self._ensembles = ensembles
        self._theme = webviz_settings.theme

        if ensembles is None:
            raise ValueError('Incorrect argument, must provide "ensembles"')

        self._ensemble_paths: Dict[str, Path] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        provider_factory = EnsembleSummaryProviderFactory.instance()

        self._data_models: Dict[str, EnsembleWellAnalysisData] = {}

        sampling = Frequency(time_index)
        for ens_name, ens_path in self._ensemble_paths.items():
            provider: EnsembleSummaryProvider = (
                provider_factory.create_from_arrow_unsmry_presampled(
                    str(ens_path), rel_file_pattern, sampling
                )
            )
            self._data_models[ens_name] = EnsembleWellAnalysisData(
                ens_name,
                provider,
                GruptreeModel(ens_name, ens_path, gruptree_file),
                WellAttributesModel(ens_name, ens_path, well_attributes_file),
                filter_out_startswith=filter_out_startswith,
            )

        self.add_view(
            WellOverviewView(self._data_models, self._theme),
            self.Ids.WELL_OVERVIEW,
        )
        self.add_view(
            WellControlView(self._data_models, self._theme),
            self.Ids.WELL_CONTROL,
        )

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.view(self.Ids.WELL_OVERVIEW)
                .view_element(WellOverviewView.Ids.VIEW_ELEMENT)
                .component_unique_id(WellOverviewViewElement.Ids.GRAPH),
                "content": "Shows production split on well for the various chart types",
            },
            {
                "id": self.view(self.Ids.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.CHART_TYPE)
                .get_unique_id(),
                "content": "Choose chart type: bar, pie or area chart. ",
            },
            {
                "id": self.view(self.Ids.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.SELECTIONS)
                .get_unique_id(),
                "content": "Choose ensembles, type of production and other options.",
            },
            {
                "id": self.view(self.Ids.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.LAYOUT_OPTIONS)
                .get_unique_id(),
                "content": "Chart layout options.",
            },
            {
                "id": self.view(self.Ids.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.FILTERS)
                .get_unique_id(),
                "content": "You can choose to view the production for all the wells or "
                "select only the ones you are interested in.",
            },
            {
                "id": self.view(self.Ids.WELL_CONTROL)
                .view_element(WellControlView.Ids.VIEW_ELEMENT)
                .component_unique_id(WellControlViewElement.Ids.CHART),
                "content": "Shows the number of realizations on different control modes "
                "and network pressures.",
            },
            {
                "id": self.view(self.Ids.WELL_CONTROL)
                .settings_group(WellControlView.Ids.SETTINGS)
                .get_unique_id(),
                "content": "Select the ensemble and well you are interested in."
                "The well dropdown is autmatically updated when ensemble is selected",
            },
            {
                "id": self.view(self.Ids.WELL_CONTROL)
                .settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .get_unique_id(),
                "content": "Here are some options related only to the Network pressures plot.",
            },
        ]

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return [
            webviz_store_tuple
            for _, ens_data_model in self._data_models.items()
            for webviz_store_tuple in ens_data_model.webviz_store
        ]

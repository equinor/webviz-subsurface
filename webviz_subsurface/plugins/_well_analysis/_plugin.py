from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Type

from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings

from ..._models import GruptreeModel, WellAttributesModel
from ..._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)
from ._error import error
from ._utils import EnsembleWellAnalysisData
from ._views import (
    WellControlPressurePlotOptions,
    WellControlSettings,
    WellControlView,
    WellOverviewFilters,
    WellOverviewSettings,
    WellOverviewView,
    WellOverviewViewElement,
)


class PluginIds:
    # pylint: disable=too-few-public-methods
    class ViewID(str, Enum):
        WELL_OVERVIEW = "well-overview"
        WELL_CONTROL = "well-control"


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
        super().__init__()

        self.error_message = ""

        self._ensembles = ensembles
        self._theme = webviz_settings.theme

        if ensembles is None:
            self.error_message = 'Incorrect argument, must provide "ensembles"'
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
            PluginIds.ViewID.WELL_OVERVIEW,
        )
        self.add_view(
            WellControlView(self._data_models, self._theme),
            PluginIds.ViewID.WELL_CONTROL,
        )

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.view(PluginIds.ViewID.WELL_OVERVIEW)
                .view_element(WellOverviewView.Ids.VIEW_ELEMENT)
                .component_unique_id(WellOverviewViewElement.Ids.CHART),
                "content": """Shows cumulative well oil production,
                 with the possibility to switch between different chart types.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.CHARTTYPE),
                "content": """You can choose to view your selected data in a bar,
                             pie or stacked area chart.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.ENSEMBLES),
                "content": """Lets you choose between different ensembles.
                            Several can be selected at the same time.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.RESPONSE),
                "content": """This gives you the option to see different types of production.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.SETTINGS)
                .component_unique_id(
                    WellOverviewSettings.Ids.ONLY_PRODUCTION_AFTER_DATE
                ),
                "content": """You can choose to only see the production after a certain date.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.SETTINGS)
                .component_unique_id(WellOverviewSettings.Ids.CHARTTYPE_SETTINGS),
                "content": """You can change the layout of the graph. This does not alter the data.
                            The options vary depending on your selected plot type.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_OVERVIEW)
                .settings_group(WellOverviewView.Ids.FILTERS)
                .component_unique_id(WellOverviewFilters.Ids.SELECTED_WELLS),
                "content": """You can choose to view the production for all the wells or
                                select only the ones you are interested in.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_CONTROL)
                .layout_element(WellControlView.Ids.MAIN_COLUMN)
                .get_unique_id(),
                "content": """Shows the number of realizations on different control modes.
                             The control modes are listed in the legend. Also shows
                             Network pressures according to dates.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_CONTROL)
                .settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.ENSEMBLE),
                "content": """You can choose to view data on different ensembles.
                            Only one can be selected.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_CONTROL)
                .settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.WELL),
                "content": """You can also view data on different wells.
                            Only one can be selected.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_CONTROL)
                .settings_group(WellControlView.Ids.SETTINGS)
                .component_unique_id(WellControlSettings.Ids.SHARED_X_AXIS),
                "content": """This gives you the option to view both graphs on the same x-axis.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_CONTROL)
                .settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(WellControlPressurePlotOptions.Ids.INCLUDE_BHP),
                "content": """Toggle bottom hole pressure on and off.""",
            },
            {
                "id": self.view(PluginIds.ViewID.WELL_CONTROL)
                .settings_group(WellControlView.Ids.PRESSUREPLOT_OPTIONS)
                .component_unique_id(
                    WellControlPressurePlotOptions.Ids.PRESSURE_PLOT_MODE
                ),
                "content": """You can choose to view the mean value of the realizations or
                            data on a single realization. If single realization is selected,
                            you get the option to choose which one.""",
            },
        ]

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return [
            webviz_store_tuple
            for _, ens_data_model in self._data_models.items()
            for webviz_store_tuple in ens_data_model.webviz_store
        ]

    @property
    def layout(self) -> Type[Component]:
        return error(self.error_message)

from pathlib import Path
from typing import Callable, Dict, List, Tuple

from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._models import GruptreeModel
from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)

from ._ensemble_group_tree_data import EnsembleGroupTreeData
from ._plugin_ids import PluginIds
from .shared_settings import Controls, Filters, Options
from .views import GroupTreeGraph


class GroupTree(WebvizPluginABC):
    """This plugin vizualizes the network tree and displays pressures,
    rates and other network related information.
    ---
    * **`ensembles`:** Which ensembles in `shared_settings` to include.
    * **`gruptree_file`:** `.csv` with gruptree information.
    * **`time_index`:** Frequency for the data sampling.
    ---
    **Summary data**
    This plugin needs the following summary vectors to be exported:
    * FOPR, FWPR, FOPR, FWIR and FGIR
    * GPR for all group nodes in the network
    * GOPR, GWPR and GGPR for all group nodes in the production network \
    (GOPRNB etc for BRANPROP trees)
    * GGIR and/or GWIR for all group nodes in the injection network
    * WSTAT, WTHP, WBHP, WMCTL for all wells
    * WOPR, WWPR, WGPR for all producers
    * WWIR and/or WGIR for all injectors
    **GRUPTREE input**
    `gruptree_file` is a path to a file stored per realization (e.g. in \
    `share/results/tables/gruptree.csv"`).
    The `gruptree_file` file can be dumped to disk per realization by the `ECL2CSV` forward
    model with subcommand `gruptree`. The forward model uses `ecl2df` to export a table
    representation of the Eclipse network:
    [Link to ecl2csv gruptree documentation.](https://equinor.github.io/ecl2df/usage/gruptree.html).
    **time_index**
    This is the sampling interval of the summary data. It is `yearly` by default, but can be set
    to `monthly` if needed.
    """

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        gruptree_file: str = "share/results/tables/gruptree.csv",
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        time_index: str = "yearly",
    ) -> None:
        super().__init__(stretch=True)

        self.error_message = ""

        assert time_index in [
            "monthly",
            "yearly",
        ], "time_index must be monthly or yearly"
        self._ensembles = ensembles
        self._gruptree_file = gruptree_file

        if ensembles is None:
            raise ValueError('Incorrect argument, must provide "ensembles"')

        sampling = Frequency(time_index)

        self._ensemble_paths: Dict[str, Path] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        provider_factory = EnsembleSummaryProviderFactory.instance()

        self._group_tree_data: Dict[str, EnsembleGroupTreeData] = {}

        sampling = Frequency(time_index)
        for ens_name, ens_path in self._ensemble_paths.items():
            provider: EnsembleSummaryProvider = (
                provider_factory.create_from_arrow_unsmry_presampled(
                    str(ens_path), rel_file_pattern, sampling
                )
            )
            self._group_tree_data[ens_name] = EnsembleGroupTreeData(
                provider, GruptreeModel(ens_name, ens_path, gruptree_file)
            )

        self.add_store(PluginIds.Stores.ENSEMBLES, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.TREEMODE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.STATISTICS, WebvizPluginABC.StorageType.SESSION)
        self.add_store(
            PluginIds.Stores.REALIZATION, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(PluginIds.Stores.FILTER, WebvizPluginABC.StorageType.SESSION)
        # self.add_store(PluginIds.Stores.OPTIONS, WebvizPluginABC.StorageType.SESSION)

        self.add_shared_settings_group(
            Controls(self._ensembles), PluginIds.SharedSettings.CONTROLS
        )
        self.add_shared_settings_group(
            Options(self._group_tree_data), PluginIds.SharedSettings.OPTIONS
        )
        self.add_shared_settings_group(Filters(), PluginIds.SharedSettings.FILTERS)

        self.add_view(
            GroupTreeGraph(self._group_tree_data),
            PluginIds.ProductionNetworkID.GROUP_TREE,
            PluginIds.ProductionNetworkID.GROUP_NAME,
        )

        print(Filters().component_unique_id(Filters.Ids.FILTER).to_string())

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return [
            ens_grouptree_data.webviz_store
            for _, ens_grouptree_data in self._group_tree_data.items()
        ]

    # @property
    # def layout(self) -> Type[Component]:
    #     return html.Div()

    # @property
    # def tour_steps(self) -> List[dict]:

    #     return [
    #         # {
    #         #     "id": PluginIds.SharedSettings.CONTROLS,
    #         #     "content": "Menu for selecting ensemble and tree mode.",
    #         # },
    #         {
    #             "id":Filters.component_unique_id(Filters(), Filters.Ids.FILTER).to_string(),
    #             "content": "Menu for statistical options or realization.",
    #         },
    #         # {
    #         #     "id": self.uuid(PluginIds.SharedSettings.FILTERS),
    #         #     "content": "Menu for filtering options.",
    #         # },
    #         # {
    #         #     "id": GroupTreeGraph.layout_element(GroupTreeGraph.Ids.GRAPH)
    # .get_unique_id()
    # .to_string(),
    #         #     "content": "Vizualisation of network tree.",
    #         # },
    #     ]

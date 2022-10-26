from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from webviz_subsurface._models import GruptreeModel
from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)

from ._utils import EnsembleGroupTreeData
from ._views._group_tree_view import GroupTreeView, GroupTreeViewElement


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
    * WSTAT for all wells
    * FWIR and FGIR if there are injector wells in the network
    * GOPR, GWPR and GGPR for all group nodes in the production network \
    except the terminal node (GOPRNB etc for BRANPROP trees)
    * GGIR and/or GWIR for all group nodes in the injection network \
    except the terminal node.
    * WOPR, WWPR, WGPR for all producers
    * WWIR and/or WGIR for all injectors

    The following data will be displayed if available:
    * GPR for all group nodes
    * WTHP, WBHP, WMCTL for all wells

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

    **terminal_node**

    This parameter allows you to specify the terminal node used. It is `FIELD` by default.

    **tree_type**

    This parameter allows you to specify which tree type is vizualised. It is `GRUPTREE` by
    default, but can also be set to `BRANPROP`.

    **excl_well_startswith**

    This parameter allows you to remove wells that starts with any of the strings in this list.
    It is intended to be used to remove f.ex RFT wells that don't have any production or injection.
    Be aware that if actual producers/injectors are removed, the rates in the tree might not be
    consistant.

    **excl_well_endswith**

    Same as excl_well_startswith, but removes wells that ends with any of the strings in this list.

    """

    class Ids(StrEnum):
        GROUPTREE_VIEW = "group-tree-view"

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        gruptree_file: str = "share/results/tables/gruptree.csv",
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        time_index: str = "yearly",
        terminal_node: str = "FIELD",
        tree_type: str = "GRUPTREE",
        excl_well_startswith: Optional[List] = None,
        excl_well_endswith: Optional[List] = None,
    ) -> None:
        # pylint: disable=too-many-arguments
        super().__init__(stretch=True)

        self._ensembles = ensembles
        self._gruptree_file = gruptree_file

        if excl_well_startswith is None:
            excl_well_startswith = []
        excl_well_startswith = [str(element) for element in excl_well_startswith]
        if excl_well_endswith is None:
            excl_well_endswith = []
        excl_well_endswith = [str(element) for element in excl_well_endswith]

        if ensembles is None:
            raise ValueError('Incorrect argument, must provide "ensembles"')

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
                provider=provider,
                gruptree_model=GruptreeModel(
                    ens_name=ens_name,
                    ens_path=ens_path,
                    gruptree_file=gruptree_file,
                    tree_type=tree_type,
                ),
                terminal_node=terminal_node,
                excl_well_startswith=excl_well_startswith,
                excl_well_endswith=excl_well_endswith,
            )

        self.add_view(
            GroupTreeView(self._group_tree_data),
            self.Ids.GROUPTREE_VIEW,
        )

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return [
            ens_grouptree_data.webviz_store
            for _, ens_grouptree_data in self._group_tree_data.items()
        ]

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.view(self.Ids.GROUPTREE_VIEW)
                .settings_group(GroupTreeView.Ids.CONTROLS)
                .get_unique_id(),
                "content": "Menu for selecting ensemble and tree mode.",
            },
            {
                "id": self.view(self.Ids.GROUPTREE_VIEW)
                .settings_group(GroupTreeView.Ids.OPTIONS)
                .get_unique_id(),
                "content": "Menu for statistical options or realization.",
            },
            {
                "id": self.view(self.Ids.GROUPTREE_VIEW)
                .settings_group(GroupTreeView.Ids.FILTERS)
                .get_unique_id(),
                "content": "Menu for filtering options.",
            },
            {
                "id": self.view(self.Ids.GROUPTREE_VIEW)
                .view_element(GroupTreeView.Ids.VIEW_ELEMENT)
                .component_unique_id(GroupTreeViewElement.Ids.COMPONENT),
                "content": "Vizualisation of network tree.",
            },
        ]

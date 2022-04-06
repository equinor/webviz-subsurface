from pathlib import Path
from typing import Callable, Dict, List, Tuple

import dash
from dash import html
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._models import GruptreeModel
from webviz_subsurface._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)

from ._callbacks import plugin_callbacks
from ._ensemble_group_tree_data import EnsembleGroupTreeData
from ._layout import LayoutElements, main_layout


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
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        gruptree_file: str = "share/results/tables/gruptree.csv",
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        time_index: str = "yearly",
    ):
        super().__init__()
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

        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return [
            ens_grouptree_data.webviz_store
            for _, ens_grouptree_data in self._group_tree_data.items()
        ]

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid(LayoutElements.SELECTIONS_LAYOUT),
                "content": "Menu for selecting ensemble and tree mode.",
            },
            {
                "id": self.uuid(LayoutElements.OPTIONS_LAYOUT),
                "content": "Menu for statistical options or realization.",
            },
            {
                "id": self.uuid(LayoutElements.FILTERS_LAYOUT),
                "content": "Menu for filtering options.",
            },
            {
                "id": self.uuid(LayoutElements.GRAPH),
                "content": "Vizualisation of network tree.",
            },
        ]

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                main_layout(get_uuid=self.uuid, ensembles=self._ensembles),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        plugin_callbacks(
            app=app, get_uuid=self.uuid, group_tree_data=self._group_tree_data
        )

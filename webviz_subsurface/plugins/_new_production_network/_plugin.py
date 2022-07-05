from pathlib import Path
from typing import Dict

from webviz_config import WebvizPluginABC
from webviz_subsurface._providers import (
    EnsembleSummaryProvider, 
    EnsembleSummaryProviderFactory,
    Frequency,
)

from 



class NewGroupTree(WebvizPluginABC):

    def __init__(
        self, webviz_settings: WebvizSettings,
        ensembles: list,
        gruptree_file: str = "share/results/tables/gruptree.csv",
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        time_index: str = "yearly",
    ) -> None:
        super().__init__("Production Network")
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
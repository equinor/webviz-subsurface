from typing import Callable, Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import Dash
from webviz_config import WebvizPluginABC, WebvizSettings

from ..._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)

from ._callbacks import well_overview_callbacks, well_control_callbacks
from ._ensemble_data import EnsembleData
from ._layout import main_layout


class WellAnalysis(WebvizPluginABC):
    """
    Plugin Description
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: Optional[List[str]] = None,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        time_index: str = "yearly",
    ) -> None:
        super().__init__()

        self._ensembles = ensembles

        if ensembles is None:
            raise ValueError('Incorrect argument, must provide "ensembles"')

        self._ensemble_paths: Dict[str, Path] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        provider_factory = EnsembleSummaryProviderFactory.instance()

        self._data_models: Dict[str, EnsembleData] = {}

        sampling = Frequency(time_index)
        for ens_name, ens_path in self._ensemble_paths.items():
            provider: EnsembleSummaryProvider = (
                provider_factory.create_from_arrow_unsmry_presampled(
                    str(ens_path), rel_file_pattern, sampling
                )
            )
            self._data_models[ens_name] = EnsembleData(provider)

        self.set_callbacks(app)

    # def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
    #     return self._datamodel.webviz_store

    @property
    def layout(self) -> wcc.Tabs:
        return main_layout(self.uuid, self._data_models)

    def set_callbacks(self, app: Dash) -> None:
        well_overview_callbacks(app, self.uuid, self._data_models)
        well_control_callbacks(app, self.uuid, self._data_models)

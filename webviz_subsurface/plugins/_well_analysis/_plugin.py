from pathlib import Path
from typing import Dict, List, Optional

from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface

from ..._models import GruptreeModel
from ..._providers import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
    Frequency,
)
from ._callbacks import well_control_callbacks, well_overview_callbacks
from ._ensemble_data import EnsembleWellAnalysisData
from ._layout import clientside_stores, main_layout


class WellAnalysis(WebvizPluginABC):
    """
    Plugin Description
    """

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: Optional[List[str]] = None,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        gruptree_file: str = "share/results/tables/gruptree.csv",
        time_index: str = "yearly",
        filter_out_startswith: Optional[str] = None,
    ) -> None:
        super().__init__()
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "inplace_volumes.css"
        )

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
                GruptreeModel(
                    ens_name,
                    ens_path,
                    gruptree_file,
                ),
                filter_out_startswith=filter_out_startswith,
            )

        self.set_callbacks(app)

    # def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
    #     return self._datamodel.webviz_store

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                clientside_stores(get_uuid=self.uuid),
                main_layout(self.uuid, self._data_models),
            ]
        )

    def set_callbacks(self, app: Dash) -> None:
        well_overview_callbacks(app, self.uuid, self._data_models, self._theme)
        well_control_callbacks(app, self.uuid, self._data_models, self._theme)

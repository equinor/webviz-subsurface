from pathlib import Path
from typing import Callable, Dict, List, Tuple
from dash import html
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_subsurface._providers.ensemble_grid_provider import (
    EnsembleGridProviderFactory,
    GridVizService,
    CellFilter,
)

from ._callbacks import plugin_callbacks
from ._layout import plugin_main_layout


class EclipseGridViewer(WebvizPluginABC):
    """Eclipse grid viewer"""

    def __init__(
        self, webviz_settings: WebvizSettings, ensembles: List[str], grid_name: str
    ) -> None:
        super().__init__()
        grid_provider_factory = EnsembleGridProviderFactory.instance()
        self.grid_provider = grid_provider_factory.create_from_roff_files(
            ens_path=webviz_settings.shared_settings["scratch_ensembles"][ensembles[0]],
            grid_name=grid_name,
        )
        self.grid_viz_service = GridVizService.instance()
        self.grid_viz_service.register_provider(self.grid_provider)

        plugin_callbacks(
            get_uuid=self.uuid,
            grid_provider=self.grid_provider,
            grid_viz_service=self.grid_viz_service,
        )

    @property
    def layout(self) -> wcc.FlexBox:
        return plugin_main_layout(get_uuid=self.uuid, grid_provider=self.grid_provider)

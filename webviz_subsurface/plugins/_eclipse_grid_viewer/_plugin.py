from pathlib import Path
from typing import Callable, Dict, List, Tuple
from dash import html
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_subsurface._providers.ensemble_grid_provider import (
    EnsembleGridProviderFactory,
    GridVizService,
)
from webviz_subsurface._providers.well_provider import (
    WellProvider,
    WellProviderFactory,
    WellServer,
)

from ._callbacks import plugin_callbacks
from ._layout import plugin_main_layout


class EclipseGridViewer(WebvizPluginABC):
    """Eclipse grid viewer"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        app,
        ensembles: List[str],
        grid_name: str,
        well_folder: Path = None,
        well_suffix: str = ".rmswell",
    ) -> None:
        super().__init__()
        grid_provider_factory = EnsembleGridProviderFactory.instance()
        self.grid_provider = grid_provider_factory.create_from_roff_files(
            ens_path=webviz_settings.shared_settings["scratch_ensembles"][ensembles[0]],
            grid_name=grid_name,
        )
        self.grid_viz_service = GridVizService.instance()
        self.grid_viz_service.register_provider(self.grid_provider)
        factory = WellProviderFactory.instance()

        if well_folder is not None:
            self.well_provider = factory.create_from_well_files(
                well_folder=str(well_folder),
                well_suffix=".rmswell",
                md_logname="MDepth",
            )

            self.well_server = WellServer.instance(app)
            self.well_server.register_provider(self.well_provider)
        else:
            self.well_provider = None
            self.well_server = None

        plugin_callbacks(
            get_uuid=self.uuid,
            grid_provider=self.grid_provider,
            grid_viz_service=self.grid_viz_service,
            well_provider=self.well_provider,
            well_server=self.well_server,
        )

    @property
    def layout(self) -> wcc.FlexBox:
        return plugin_main_layout(
            get_uuid=self.uuid,
            grid_provider=self.grid_provider,
            well_names=self.well_provider.well_names()
            if self.well_provider is not None
            else [],
        )

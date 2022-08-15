from typing import List, Optional
from pathlib import Path

from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._providers.ensemble_grid_provider import (
    EnsembleGridProviderFactory,
    GridVizService,
    EnsembleGridProvider,
)
from webviz_subsurface._providers.well_provider import (
    WellProvider,
    WellProviderFactory,
    WellServer,
)

from ._layout_elements import ElementIds
from .views.view_3d._view_3d import View3D


class GridViewer(WebvizPluginABC):
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        grid_name: str,
    ):
        super().__init__(stretch=True)

        self.ensembles = {
            ens_name: webviz_settings.shared_settings["scratch_ensembles"][ens_name]
            for ens_name in ensembles
        }

        self.add_grid_provider(grid_name=grid_name)

        self.add_store(
            ElementIds.GridFilter.IJK_CROP_STORE,
            storage_type=WebvizPluginABC.StorageType.SESSION,
        )
        print(self._stores)
        self.add_view(
            View3D(
                grid_provider=self.grid_provider, grid_viz_service=self.grid_viz_service
            ),
            ElementIds.ID,
        )

    def add_grid_provider(self, grid_name: str) -> None:
        factory = EnsembleGridProviderFactory.instance()
        self.grid_provider: EnsembleGridProvider = factory.create_from_roff_files(
            ens_path=list(self.ensembles.values())[0],
            grid_name=grid_name,
        )
        self.grid_viz_service = GridVizService.instance()
        self.grid_viz_service.register_provider(self.grid_provider)

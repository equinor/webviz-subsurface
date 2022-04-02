from pathlib import Path
from typing import List

import webviz_core_components as wcc
from webviz_config import WebvizPluginABC

from ._business_logic import EclipseGridDataModel
from ._callbacks import plugin_callbacks
from ._layout import plugin_main_layout


class EclipseGridViewer(WebvizPluginABC):
    """Eclipse grid viewer"""

    def __init__(
        self,
        egrid_file: Path,
        init_file: Path,
        restart_file: Path,
        init_names: List[str],
        restart_names: List[str],
    ) -> None:
        super().__init__()

        self._datamodel: EclipseGridDataModel = EclipseGridDataModel(
            egrid_file=egrid_file,
            init_file=init_file,
            restart_file=restart_file,
            init_names=init_names,
            restart_names=restart_names,
        )
        plugin_callbacks(get_uuid=self.uuid, datamodel=self._datamodel)

    @property
    def layout(self) -> wcc.FlexBox:
        return plugin_main_layout(
            get_uuid=self.uuid, esg_provider=self._datamodel.esg_provider
        )

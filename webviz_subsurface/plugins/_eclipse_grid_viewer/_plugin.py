from pathlib import Path
from typing import Callable, Dict, List, Tuple

import webviz_core_components as wcc
from webviz_config import WebvizPluginABC

from ._eclipse_grid_datamodel import EclipseGridDataModel
from ._roff_grid_datamodel import RoffGridDataModel
from ._callbacks import plugin_callbacks
from ._layout import plugin_main_layout


class EclipseGridViewer(WebvizPluginABC):
    """Eclipse grid viewer"""

    def __init__(
        self,
        roff_folder: Path = None,
        roff_grid_name: str = None,
        egrid_file: Path = None,
        init_file: Path = None,
        restart_file: Path = None,
        init_names: List[str] = None,
        restart_names: List[str] = None,
    ) -> None:
        super().__init__()
        if roff_folder is not None and roff_grid_name is not None:
            self._datamodel = RoffGridDataModel(roff_folder, roff_grid_name)
        else:
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
            get_uuid=self.uuid, esg_accessor=self._datamodel.esg_accessor
        )

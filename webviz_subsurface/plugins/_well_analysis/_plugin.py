from typing import Callable, Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import Dash
from webviz_config import WebvizPluginABC, WebvizSettings

from ._callbacks import plugin_callbacks
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
    ) -> None:
        super().__init__()

        # self.set_callbacks(app)

    # def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
    #     return self._datamodel.webviz_store

    @property
    def layout(self) -> wcc.Tabs:
        return main_layout(self.uuid)  # , self._datamodel)

    def set_callbacks(self, app: Dash) -> None:
        plugin_callbacks(app, self.uuid)  # , self._datamodel)

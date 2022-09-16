from typing import Any, Dict, List, Optional, Tuple

import webviz_core_components as wcc
from dash import Input, Output, State, callback, html
from dash.development.base_component import Component
from webviz_config import WebvizConfigTheme
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from ..._utils import RftPlotterDataModel
from ._settings import MapSettings

class MapView(ViewABC):
    class Ids(StrEnum):
        MAP_SETTINGS = "map-plot-settings"
        FORMATION_PLOT_SETTINGS = "formation-plot-settings"
        MAP_VIEW_ELEMENT = "map-view-element"
        FORMATION_PLOT_VIEW_ELEMENT = "formation-plot-view-element"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Map")
        self._datamodel = datamodel

        self.add_settings_group(MapSettings(self._datamodel), self.Ids.MAP_SETTINGS)
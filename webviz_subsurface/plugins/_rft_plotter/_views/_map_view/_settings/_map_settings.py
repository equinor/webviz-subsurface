from typing import Any, Dict, List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._types import ColorAndSizeByType


class MapSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "map-ensemble"
        SIZE_BY = "map-size-by"
        COLOR_BY = "map-color-by"
        DATE_RANGE = "map-date-range"
        ZONES = "map-zones"

    def __init__(
        self,
        ensembles: List[str],
        zones: List[str],
        date_marks: Dict[int, Dict[str, Any]],
        unique_dates_count: int,
    ) -> None:
        super().__init__("Map settings")
        self._ensembles = ensembles
        self._zone_names = zones
        self._date_marks = date_marks
        self._unique_dates_count = unique_dates_count

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                value=self._ensembles[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Size points by",
                id=self.register_component_unique_id(self.Ids.SIZE_BY),
                options=[
                    {
                        "label": "Standard Deviation",
                        "value": ColorAndSizeByType.STDDEV,
                    },
                    {
                        "label": "Misfit",
                        "value": ColorAndSizeByType.MISFIT,
                    },
                ],
                value=ColorAndSizeByType.MISFIT,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Color points by",
                id=self.register_component_unique_id(self.Ids.COLOR_BY),
                options=[
                    {
                        "label": "Misfit",
                        "value": ColorAndSizeByType.MISFIT,
                    },
                    {
                        "label": "Standard Deviation",
                        "value": ColorAndSizeByType.STDDEV,
                    },
                    {
                        "label": "Year",
                        "value": ColorAndSizeByType.YEAR,
                    },
                ],
                value=ColorAndSizeByType.STDDEV,
                clearable=False,
            ),
            wcc.RangeSlider(
                label="Filter date range",
                id=self.register_component_unique_id(self.Ids.DATE_RANGE),
                min=0,
                max=self._unique_dates_count - 1,
                value=[0, self._unique_dates_count - 1],
                marks=self._date_marks,
            ),
            wcc.Label(
                "Zone filter",
            ),
            wcc.SelectWithLabel(
                size=min(10, len(self._zone_names)),
                id=self.register_component_unique_id(self.Ids.ZONES),
                options=[{"label": name, "value": name} for name in self._zone_names],
                value=self._zone_names,
                multi=True,
            ),
        ]

from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from ...._utils import RftPlotterDataModel


class MapSettings(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "map-ensemble"
        SIZE_BY = "map-size-by"
        COLOR_BY = "map-color-by"
        DATE_RANGE = "map-date-range"
        ZONES = "map-zones"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Map settings")
        self._datamodel = datamodel
        self._ensembles = datamodel.ensembles
        self._zone_names = datamodel.zone_names

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
                        "value": "STDDEV",
                    },
                    {
                        "label": "Misfit",
                        "value": "ABSDIFF",
                    },
                ],
                value="ABSDIFF",
                clearable=False,
            ),
            wcc.Dropdown(
                label="Color points by",
                id=self.register_component_unique_id(self.Ids.COLOR_BY),
                options=[
                    {
                        "label": "Misfit",
                        "value": "ABSDIFF",
                    },
                    {
                        "label": "Standard Deviation",
                        "value": "STDDEV",
                    },
                    {
                        "label": "Year",
                        "value": "YEAR",
                    },
                ],
                value="STDDEV",
                clearable=False,
            ),
            wcc.RangeSlider(
                label="Filter date range",
                id=self.register_component_unique_id(self.Ids.DATE_RANGE),
                min=self._datamodel.ertdatadf["DATE_IDX"].min(),
                max=self._datamodel.ertdatadf["DATE_IDX"].max(),
                value=[
                    self._datamodel.ertdatadf["DATE_IDX"].min(),
                    self._datamodel.ertdatadf["DATE_IDX"].max(),
                ],
                marks=self._datamodel.date_marks,
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

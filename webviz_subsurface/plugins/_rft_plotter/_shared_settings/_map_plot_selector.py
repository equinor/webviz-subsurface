from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._business_logic import RftPlotterDataModel


class MapPlotSelector(SettingsGroupABC):
    class Ids:
        MAP_ENSEMBLE = "map-ensemble"
        MAP_SIZE_BY = "map-size-by"
        MAP_COLOR_BY = "map-color-by"
        MAP_DATE_RANGE = "map-date-range"
        MAP_ZONES = "map-zones"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Map plot settings")
        self.datamodel = datamodel
        self.ensembles = datamodel.ensembles
        self.zone_names = datamodel.zone_names

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Ensemble",
                id=self.register_component_unique_id(self.Ids.MAP_ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in self.ensembles],
                value=self.ensembles[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Size points by",
                id=self.register_component_unique_id(self.Ids.MAP_SIZE_BY),
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
                id=self.register_component_unique_id(self.Ids.MAP_COLOR_BY),
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
                id=self.register_component_unique_id(self.Ids.MAP_DATE_RANGE),
                min=self.datamodel.ertdatadf["DATE_IDX"].min(),
                max=self.datamodel.ertdatadf["DATE_IDX"].max(),
                value=[
                    self.datamodel.ertdatadf["DATE_IDX"].min(),
                    self.datamodel.ertdatadf["DATE_IDX"].max(),
                ],
                marks=self.datamodel.date_marks,
            ),
            wcc.Selectors(
                label="Zone filter",
                open_details=False,
                children=[
                    wcc.SelectWithLabel(
                        size=min(10, len(self.zone_names)),
                        id=self.register_component_unique_id(self.Ids.MAP_ZONES),
                        options=[
                            {"label": name, "value": name} for name in self.zone_names
                        ],
                        value=self.zone_names,
                        multi=True,
                    ),
                ],
            ),
        ]

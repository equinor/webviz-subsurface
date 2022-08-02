from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Filters(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        EQLNUM = "eqlnum"

    def __init__(
        self,
        datamodel: SwatinitQcDataModel,
    ) -> None:
        super().__init__("Filters")
        self.datamodel = datamodel

    @property
    def layout(self) -> List[Component]:
        elements = [
            wcc.SelectWithLabel(
                label="EQLNUM",
                id=self.register_component_unique_id(Filters.IDs.EQLNUM),
                options=[
                    {"label": ens, "value": ens} for ens in self.datamodel.eqlnums
                ],
                value=self.datamodel.eqlnums[:1],
                size=min(8, len(self.datamodel.eqlnums)),
                multi=True,
            ),
        ]
        elements.append(self.range_filters)
        return elements

    @property
    def range_filters(uuid: str, datamodel: SwatinitQcDataModel) -> List:
        dframe = datamodel.dframe
        filters = []
        for col in datamodel.filters_continuous:
            min_val, max_val = dframe[col].min(), dframe[col].max()
            filters.append(
                wcc.RangeSlider(
                    label="Depth range" if col == "Z" else col,
                    id={"id": uuid, "col": col},
                    min=min_val,
                    max=max_val,
                    value=[min_val, max_val],
                    marks={
                        str(val): {"label": f"{val:.2f}"} for val in [min_val, max_val]
                    },
                    tooltip={"always_visible": False},
                )
            )
        return filters

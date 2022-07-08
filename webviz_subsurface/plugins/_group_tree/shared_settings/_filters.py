from typing import Type, List

from dash import callback, Input, Output
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from .._types import NodeType
from .._plugin_Ids import PluginIds
class Filters(SettingsGroupABC):

    class Ids:
        FILTER = "filter"

    def __init__(self) -> None:
        super().__init__("Filters")

    def layout(self) -> Type[Component]:
        return wcc.SelectWithLabel(
                    label="Prod/Inj/Other",
                    id=self.register_component_unique_id(self.Ids.FILTER),
                    options=[
                        {"label": "Production", "value": NodeType.PROD.value},
                        {"label": "Injection", "value": NodeType.INJ.value},
                        {"label": "Other", "value": NodeType.OTHER.value},
                    ],
                    value=[NodeType.PROD.value, NodeType.INJ.value, NodeType.OTHER.value],
                    multi=True,
                    size=3,
                )

    def set_callbacks(self) -> None:
        @callback( 
            Output(self.get_store_unique_id(PluginIds.Stores.FILTER), 'data'),
            Input(self.component_unique_id(self.Ids.FILTER).to_string(), 'value')
            )
        def _uodate_filter_store(selected_filters: List[str]) -> List[str]:
            return selected_filters
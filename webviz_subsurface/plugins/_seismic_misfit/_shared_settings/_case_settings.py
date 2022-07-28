from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class CaseSettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        ATTRIBUTE_NAME = "attribute-name"
        ENSEMBLES_NAME = "ensembles-name"

    def __init__(self, attributes: List[str], ens_names: List) -> None:
        super().__init__("Case sttings")
        self.attributes = attributes
        self.ens_names = ens_names

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Attribute selector",
                id=self.register_component_unique_id(self.Ids.ATTRIBUTE_NAME),
                optionHeight=60,
                options=[
                    {
                        "label": attr.replace(".txt", "")
                        .replace("_", " ")
                        .replace("--", " "),
                        "value": attr,
                    }
                    for attr in self.attributes
                ],
                value=self.attributes[0],
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Ensemble selector",
                id=self.register_component_unique_id(self.Ids.ENSEMBLES_NAME),
                options=[{"label": ens, "value": ens} for ens in self.ens_names],
                value=self.ens_names,
                multi=True,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
        ]

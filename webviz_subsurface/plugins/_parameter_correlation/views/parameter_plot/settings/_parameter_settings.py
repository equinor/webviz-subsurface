from typing import List

import webviz_core_components as wcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class ParameterSettings(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        SHARED_ENSEMBLE = "shared-ensemble"
        PARAMETER_H = "parameter-horizontal"
        ENSEMBLE_H = "ensemble-horizontal"
        PARAMETER_V = "parameter-vertical"
        ENSEMBLE_V = "ensemble-vertical"
        SCATTER_VISIBLE = "scatter-visible"
        SCATTER_COLOR = "scatter-color"

    def __init__(self, ensembles: dict, p_cols: List) -> None:
        super().__init__("Settings")
        self.ensembles = ensembles
        self.p_cols = p_cols

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(
                    ParameterSettings.IDs.SHARED_ENSEMBLE
                ),
                label="Ensemble in both plot",
                options=[{"label": k, "value": v} for k, v in self.ensembles.items()],
                value=list(self.ensembles.values())[0],
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ParameterSettings.IDs.PARAMETER_H),
                label="Parameter (horizontal axis)",
                options=[{"label": p, "value": p} for p in self.p_cols],
                value=self.p_cols[0] if len(self.p_cols) > 0 else "",
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ParameterSettings.IDs.ENSEMBLE_H),
                label="Ensemble (horizontal axis)",
                options=[{"label": k, "value": v} for k, v in self.ensembles.items()],
                value=list(self.ensembles.values())[0]
                if len(self.ensembles.values()) > 0
                else "",
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ParameterSettings.IDs.PARAMETER_V),
                label="Parameter (vertical axis)",
                options=[{"label": p, "value": p} for p in self.p_cols],
                value=self.p_cols[0] if len(self.p_cols) > 0 else "",
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ParameterSettings.IDs.ENSEMBLE_V),
                label="Ensemble (vertical axis)",
                options=[{"label": k, "value": v} for k, v in self.ensembles.items()],
                value=list(self.ensembles.values())[0]
                if len(self.ensembles.values()) > 0
                else "",
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(
                    ParameterSettings.IDs.SCATTER_COLOR
                ),
                label="Color points by",
                options=[{"label": p, "value": p} for p in self.p_cols],
                value=self.p_cols[0] if len(self.p_cols) > 0 else "",
                multi=False,
                clearable=True,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(
                    ParameterSettings.IDs.SCATTER_VISIBLE
                ),
                style={"padding": "5px"},
                options=[
                    {
                        "label": "Show scatterplot density",
                        "value": "density",
                    }
                ],
            ),
        ]

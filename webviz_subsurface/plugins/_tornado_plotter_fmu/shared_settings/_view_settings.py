from typing import List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback, html
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PlugInIDs


class ViewSettings(SettingsGroupABC):
    """Settingsgroup for settings for the view"""

    class IDs:
        # pylint: disable=too-few-public-methods
        REFERENCE = "reference"
        SCALE = "scale"
        SENSITIVITEIS = "sensitivities"
        RESET_BUTTON = "reset-button"
        PLOT_OPTIONS = "plot-options"
        LABEL = "label"

    def __init__(
        self,
        realizations: pd.DataFrame,  # tror ikke dette er en Lisa
        reference: str = "rms_seed",
        allow_click: bool = False,
    ) -> None:
        super().__init__("View Settings")

        print("realixationstype: ")
        print(type(realizations))

        unique_realizations = realizations["SENSNAME"].unique()
        self.sensnames = list(unique_realizations)
        self.scales = [
            "Relative value (%)",
            "Relative value",
            "True value",
        ]
        self.plot_options = [
            {
                "label": "Fit all bars in figure",
                "value": "Fit all bars in figure",
            },
            {
                "label": "Remove sensitivites with no impact",
                "value": "Remove sensitivites with no impact",
            },
            {
                "label": "Show realization points",
                "value": "Show realization points",
            },
            {
                "label": "Color bars by sensitivity",
                "value": "Color bars by sensitivity",
            },
        ]
        self.label_options = [
            {"label": "No label", "value": "hide"},
            {
                "label": "Simple label",
                "value": "simple",
            },
            {
                "label": "Detailed label",
                "value": "detailed",
            },
        ]
        self.initial_reference = (
            reference if reference in self.sensnames else self.sensnames[0]
        )
        self.allow_click = allow_click

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.IDs.REFERENCE),
                label="Reference",
                options=[{"label": r, "value": r} for r in self.sensnames],
                value=self.initial_reference,
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.IDs.SCALE),
                label="Scale",
                options=[{"label": r, "value": r} for r in self.scales],
                value=self.scales[0],
                multi=False,
                clearable=False,
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(ViewSettings.IDs.SENSITIVITEIS),
                label="Select sensitivities",
                options=[{"label": r, "value": r} for r in self.sensnames],
                value=self.sensnames[0],
                multi=True,
            ),
            html.Button(
                id=self.register_component_unique_id(ViewSettings.IDs.RESET_BUTTON),
                title="Reset Selected Sesitivities",
                style={
                    "fontSize": "10px",
                    "marginTop": "10px",
                }
                if self.allow_click
                else {"display": "none"},
                children="Clear selected",
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(ViewSettings.IDs.PLOT_OPTIONS),
                label="Plot options",
                options=self.plot_options,
                value=[],
                labelStyle={"display": "block"},
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(ViewSettings.IDs.LABEL),
                label="Label",
                options=self.label_options,
                value="detailed",
                clearable=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.REFERENCE),
                "data",
            ),
            Input(
                self.component_unique_id(ViewSettings.IDs.REFERENCE).to_string(),
                "value",
            ),
        )
        def _set_reference(ref: str) -> str:
            return ref

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.SCALE), "data"
            ),
            Input(
                self.component_unique_id(ViewSettings.IDs.SCALE).to_string(), "value"
            ),
        )
        def _set_scale(scale: str) -> str:
            return scale

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.SENSITIVITIES),
                "data",
            ),
            Input(
                self.component_unique_id(ViewSettings.IDs.SENSITIVITEIS).to_string(),
                "value",
            ),
        )
        def _set_sensitivities(sens: List[str]) -> List[str]:
            return sens

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.RESET), "data"
            ),
            Input(
                self.component_unique_id(ViewSettings.IDs.RESET_BUTTON).to_string(),
                "n_clicks",
            ),
        )
        def _set_button(n_clicks: int) -> int:
            return n_clicks

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.PLOT_OPTIONS),
                "data",
            ),
            Input(
                self.component_unique_id(ViewSettings.IDs.PLOT_OPTIONS).to_string(),
                "value",
            ),
        )
        def _set_plot_options(picked_options: List[str]) -> List[str]:
            return picked_options

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.ViewSetttings.LABEL), "data"
            ),
            Input(
                self.component_unique_id(ViewSettings.IDs.LABEL).to_string(), "value"
            ),
        )
        def _set_label(label: str) -> str:
            return label

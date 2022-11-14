from typing import Any, List, Optional

import webviz_core_components as wcc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC


class Selections(SettingsGroupABC):
    class Ids(StrEnum):
        VFP_NAME = "vfp-name"
        METADATA_BUTTON = "metadata-button"
        METADATA_DIALOG = "metadata-dialog"

    def __init__(self, vfp_names: List[str]) -> None:
        super().__init__("Selections")
        self._vfp_names = vfp_names

    def layout(self) -> List[Any]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Selections.Ids.VFP_NAME),
                label="VFP name",
                options=[{"label": vfp, "value": vfp} for vfp in self._vfp_names],
                clearable=False,
                value=self._vfp_names[0] if len(self._vfp_names) > 0 else None,
                persistence=True,
                persistence_type="session",
            ),
            html.Button(
                "Show VFP Metadata",
                style={
                    "width": "100%",
                    "background-color": "white",
                    "margin-top": "5px",
                },
                id=self.register_component_unique_id(Selections.Ids.METADATA_BUTTON),
            ),
            wcc.Dialog(
                title="VFP Table Metadata",
                id=self.register_component_unique_id(Selections.Ids.METADATA_DIALOG),
                max_width="md",
                open=False,
                children=dcc.Markdown("VFP Metadata not set."),
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(self.Ids.METADATA_DIALOG).to_string(), "open"
            ),
            Input(
                self.component_unique_id(self.Ids.METADATA_BUTTON).to_string(),
                "n_clicks",
            ),
            State(
                self.component_unique_id(self.Ids.METADATA_DIALOG).to_string(), "open"
            ),
        )
        @callback_typecheck
        def open_close_metadata_dialog(n_clicks: Optional[int], is_open: bool) -> bool:
            if n_clicks is not None:
                return not is_open
            raise PreventUpdate

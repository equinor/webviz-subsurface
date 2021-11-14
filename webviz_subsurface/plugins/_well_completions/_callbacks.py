import json
from typing import Callable, List, Dict, Any

from dash import Dash, Input, Output
import webviz_subsurface_components as wsc

from ._business_logic import WellCompletionsDataModel
from ._layout import LayoutElements


def plugin_callbacks(
    app: Dash, get_uuid: Callable, data_model: WellCompletionsDataModel
) -> None:
    @app.callback(
        Output(get_uuid(LayoutElements.WELL_COMPLETIONS_COMPONENT), "children"),
        Output(get_uuid(LayoutElements.WELL_COMPLETIONS_COMPONENT), "style"),
        Input(get_uuid(LayoutElements.ENSEMBLE_DROPDOWN), "value"),
    )
    def _render_well_completions(ensemble_name: str) -> list:
        data = json.load(data_model.create_ensemble_dataset(ensemble_name))

        no_leaves = count_leaves(data["stratigraphy"])
        return [
            wsc.WellCompletions(id="well_completions", data=data),
            {
                "padding": "10px",
                "height": no_leaves * 50 + 180,
                "min-height": 500,
                "width": "98%",
            },
        ]


def count_leaves(stratigraphy: List[Dict[str, Any]]) -> int:
    """Counts the number of leaves in the stratigraphy tree"""
    return sum(
        count_leaves(zonedict["subzones"]) if "subzones" in zonedict else 1
        for zonedict in stratigraphy
    )

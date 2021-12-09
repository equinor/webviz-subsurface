from typing import Any, Callable, Dict, Tuple

from dash import Dash, Input, Output

from webviz_subsurface._models.well_set_model import WellSetModel

from ..utils.xtgeo_well_log_to_json import xtgeo_well_logs_to_json_format


def well_controller(
    app: Dash,
    well_set_model: WellSetModel,
    log_templates: Dict,
    get_uuid: Callable,
) -> None:
    @app.callback(
        Output(get_uuid("well-log-viewer"), "welllog"),
        Output(get_uuid("well-log-viewer"), "template"),
        Input(get_uuid("well"), "value"),
        Input(get_uuid("template"), "value"),
    )
    def _update_log_data(well_name: str, template: str) -> Tuple[Any, Any]:
        well = well_set_model.get_well(well_name)
        return xtgeo_well_logs_to_json_format(well), log_templates.get(template)

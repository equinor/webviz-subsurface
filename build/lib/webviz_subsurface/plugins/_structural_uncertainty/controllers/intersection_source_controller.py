from typing import Callable, Dict, List, Tuple, Union

from dash import MATCH, Dash, Input, Output


def update_intersection_source(
    app: Dash, get_uuid: Callable, surface_geometry: Dict
) -> None:
    @app.callback(
        Output(
            {"id": get_uuid("intersection-data"), "element": "well-wrapper"}, "style"
        ),
        Output(
            {"id": get_uuid("intersection-data"), "element": "xline-wrapper"}, "style"
        ),
        Output(
            {"id": get_uuid("intersection-data"), "element": "yline-wrapper"}, "style"
        ),
        Input({"id": get_uuid("intersection-data"), "element": "source"}, "value"),
    )
    def _show_source_details(source: str) -> Tuple[Dict, Dict, Dict]:
        hide = {"display": "none"}
        show = {"display": "inline"}
        if source == "well":
            return show, hide, hide
        if source == "xline":
            return hide, show, hide
        if source == "yline":
            return hide, hide, show
        return hide, hide, hide

    @app.callback(
        Output(
            {"id": get_uuid("map"), "element": "stored_xline"},
            "data",
        ),
        Input(
            {
                "id": get_uuid("intersection-data"),
                "cross-section": "xline",
                "element": "value",
            },
            "value",
        ),
    )
    def _store_xline(x_value: Union[float, int]) -> List:

        return [
            [x_value, surface_geometry["ymin"]],
            [x_value, surface_geometry["ymax"]],
        ]

    @app.callback(
        Output(
            {"id": get_uuid("map"), "element": "stored_yline"},
            "data",
        ),
        Input(
            {
                "id": get_uuid("intersection-data"),
                "cross-section": "yline",
                "element": "value",
            },
            "value",
        ),
    )
    def _store_yline(y_value: Union[float, int]) -> List:

        return [
            [surface_geometry["xmin"], y_value],
            [surface_geometry["xmax"], y_value],
        ]

    @app.callback(
        Output(
            {
                "id": get_uuid("intersection-data"),
                "cross-section": MATCH,
                "element": "value",
            },
            "step",
        ),
        Input(
            {
                "id": get_uuid("intersection-data"),
                "cross-section": MATCH,
                "element": "step",
            },
            "value",
        ),
    )
    def _set_cross_section_step(step: Union[float, int]) -> Union[float, int]:
        return step

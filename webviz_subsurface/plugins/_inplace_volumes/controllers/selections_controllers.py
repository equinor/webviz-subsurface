from typing import Callable

import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate


def selections_controllers(app: dash.Dash, get_uuid: Callable, volumemodel):
    @app.callback(
        Output(get_uuid("selections-inplace-dist"), "data"),
        Input({"id": get_uuid("selections-inplace-dist"), "selector": ALL}, "value"),
        Input({"id": get_uuid("selections-inplace-dist"), "settings": ALL}, "value"),
        State({"id": get_uuid("selections-inplace-dist"), "selector": ALL}, "id"),
        State({"id": get_uuid("selections-inplace-dist"), "settings": ALL}, "id"),
    )
    def _update_selections(selectors, settings, selctor_ids, settings_ids):
        ctx = dash.callback_context.triggered[0]
        selections = {
            id_value["selector"]: values
            for id_value, values in zip(selctor_ids, selectors)
        }
        selections.update(
            {
                id_value["settings"]: values
                for id_value, values in zip(settings_ids, settings)
            }
        )
        selections.update(ctx_clicked=ctx["prop_id"])
        return selections

    @app.callback(
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Y Response"},
            "disabled",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Y Response"},
            "value",
        ),
        Input(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Plot type"},
            "value",
        ),
    )
    def _disable_y(plot_type):
        if plot_type in ["distribution", "box", "histogram"]:
            return True, None
        return False, dash.no_update

    @app.callback(
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Subplots"},
            "disabled",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Subplots"},
            "value",
        ),
        Input(get_uuid("page-selected-inplace-dist"), "data"),
    )
    def _disable_subplots(selected_page):
        if selected_page is None or selected_page != "Custom plotting":
            return True, None
        return False, dash.no_update

    @app.callback(
        Output({"id": get_uuid("selections-inplace-dist"), "button": ALL}, "style"),
        Output(get_uuid("page-selected-inplace-dist"), "data"),
        Input({"id": get_uuid("selections-inplace-dist"), "button": ALL}, "n_clicks"),
        State({"id": get_uuid("selections-inplace-dist"), "button": ALL}, "id"),
    )
    def _update_clicked_button(_apply_click, id_all):

        ctx = dash.callback_context.triggered[0]
        page_selected = id_all[0]["button"]
        styles = []
        for button_id in id_all:
            if button_id["button"] in ctx["prop_id"]:
                styles.append({"background-color": "#7393B3", "color": "#fff"})
                page_selected = button_id["button"]
            else:
                styles.append({"background-color": "#E8E8E8"})
        if ctx["prop_id"] == ".":
            styles[0] = {"background-color": "#7393B3", "color": "#fff"}
        return styles, page_selected

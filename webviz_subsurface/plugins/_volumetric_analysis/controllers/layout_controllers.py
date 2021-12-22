from typing import Callable

from dash import ALL, Input, Output, State, callback, callback_context, no_update
from dash.exceptions import PreventUpdate

from ..utils.utils import update_relevant_components


def layout_controllers(get_uuid: Callable) -> None:
    @callback(
        Output(get_uuid("page-selected"), "data"),
        Output(get_uuid("voldist-page-selected"), "data"),
        Input({"id": get_uuid("selections"), "button": ALL}, "n_clicks"),
        Input(get_uuid("tabs"), "value"),
        State({"id": get_uuid("selections"), "button": ALL}, "id"),
        State(get_uuid("voldist-page-selected"), "data"),
    )
    def _selected_page_controllers(
        _apply_click: int,
        tab_selected: str,
        button_ids: list,
        previous_page: dict,
    ) -> tuple:

        ctx = callback_context.triggered[0]
        initial_pages = {"voldist": "custom", "tornado": "torn_multi"}

        # handle initial callback
        if ctx["prop_id"] == ".":
            page_selected = (
                tab_selected
                if not tab_selected in initial_pages
                else initial_pages[tab_selected]
            )
            previous_page = initial_pages

        elif "tabs" in ctx["prop_id"]:
            page_selected = (
                tab_selected
                if not tab_selected in initial_pages
                else previous_page[tab_selected]
            )
            previous_page = no_update

        else:
            for button_id in button_ids:
                if button_id["button"] in ctx["prop_id"]:
                    page_selected = previous_page[tab_selected] = button_id["button"]

        return page_selected, previous_page

    @callback(
        Output({"id": get_uuid("selections"), "button": ALL}, "style"),
        Input(get_uuid("page-selected"), "data"),
        State(get_uuid("tabs"), "value"),
        State({"id": get_uuid("selections"), "button": ALL}, "id"),
    )
    def _update_button_style(
        page_selected: str, tab_selected: str, button_ids: list
    ) -> list:

        if tab_selected not in ["voldist", "tornado"]:
            raise PreventUpdate

        button_styles = {
            button["button"]: {"background-color": "#E8E8E8"} for button in button_ids
        }
        button_styles[page_selected] = {"background-color": "#7393B3", "color": "#fff"}

        return update_relevant_components(
            id_list=button_ids,
            update_info=[
                {
                    "new_value": style,
                    "conditions": {"button": button},
                }
                for button, style in button_styles.items()
            ],
        )

    @callback(
        Output({"id": get_uuid("main-voldist"), "page": ALL}, "style"),
        Input(get_uuid("page-selected"), "data"),
        State({"id": get_uuid("main-voldist"), "page": ALL}, "id"),
        State(get_uuid("tabs"), "value"),
    )
    def _main_voldist_display(
        page_selected: str,
        main_layout_ids: list,
        tab_selected: str,
    ) -> list:

        if tab_selected != "voldist":
            raise PreventUpdate

        voldist_layout = []
        for page_id in main_layout_ids:
            if page_id["page"] == page_selected:
                voldist_layout.append({"display": "block"})
            else:
                voldist_layout.append({"display": "none"})
        return voldist_layout

    @callback(
        Output({"id": get_uuid("main-tornado"), "page": ALL}, "style"),
        Input(get_uuid("page-selected"), "data"),
        State({"id": get_uuid("main-tornado"), "page": ALL}, "id"),
        State(get_uuid("tabs"), "value"),
    )
    def _main_tornado_display(
        page_selected: str,
        main_layout_ids: list,
        tab_selected: str,
    ) -> list:

        if tab_selected != "tornado":
            raise PreventUpdate

        main_layout = []
        for page_id in main_layout_ids:
            if page_id["page"] == page_selected:
                main_layout.append({"display": "block"})
            else:
                main_layout.append({"display": "none"})
        return main_layout

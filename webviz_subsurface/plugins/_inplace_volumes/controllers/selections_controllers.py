from typing import Callable

import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import webviz_core_components as wcc


def selections_controllers(app: dash.Dash, get_uuid: Callable, volumemodel):
    @app.callback(
        Output(get_uuid("selections-inplace-dist"), "data"),
        Output(
            {"id": get_uuid("filter-inplace-dist"), "element": "text_selected_reals"},
            "children",
        ),
        Input({"id": get_uuid("selections-inplace-dist"), "selector": ALL}, "value"),
        Input({"id": get_uuid("filter-inplace-dist"), "selector": ALL}, "value"),
        Input(
            {"id": get_uuid("filter-inplace-dist"), "selected_reals": ALL},
            "value",
        ),
        Input(
            {"id": get_uuid("selections-inplace-dist"), "settings": "Colorscale"},
            "colorscale",
        ),
        State({"id": get_uuid("selections-inplace-dist"), "selector": ALL}, "id"),
        State({"id": get_uuid("filter-inplace-dist"), "selector": ALL}, "id"),
        State({"id": get_uuid("filter-inplace-dist"), "selected_reals": ALL}, "id"),
    )
    def _update_selections(
        selectors, filters, reals, colorscale, selctor_ids, filter_ids, real_ids
    ):
        ctx = dash.callback_context.triggered[0]
        if ctx["prop_id"] == ".":
            raise PreventUpdate

        selections = {
            id_value["selector"]: values
            for id_value, values in zip(selctor_ids, selectors)
        }
        selections["filters"] = {
            id_value["selector"]: values
            for id_value, values in zip(filter_ids, filters)
        }
        real_list = [int(real) for real in reals[0]]
        selections["filters"].update(
            REAL=(
                list(range(real_list[0], real_list[1] + 1))
                if real_ids[0]["selected_reals"] == "range"
                else real_list
            )
        )
        selections.update(Colorscale=colorscale)
        selections.update(ctx_clicked=ctx["prop_id"])

        string_selected_reals = (
            create_range_string(real_list)
            if real_ids[0]["selected_reals"] == "select"
            else f"{real_list[0]}-{real_list[1]}"
        )
        return selections, string_selected_reals

    @app.callback(
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Plot type"},
            "disabled",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Plot type"},
            "value",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Y Response"},
            "disabled",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Y Response"},
            "options",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Y Response"},
            "value",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Subplots"},
            "disabled",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Subplots"},
            "value",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Color by"},
            "options",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Color by"},
            "value",
        ),
        Input(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Plot type"},
            "value",
        ),
        Input(get_uuid("page-selected-inplace-dist"), "data"),
        Input(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Color by"},
            "value",
        ),
        State(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Subplots"},
            "value",
        ),
        State(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Y Response"},
            "options",
        ),
        State(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Y Response"},
            "value",
        ),
        State(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Plot type"},
            "options",
        ),
    )
    def _plot_options(
        plot_type,
        selected_page,
        selected_color_by,
        selected_subplot_value,
        y_options,
        selected_y,
        plot_type_options,
    ):
        ctx = dash.callback_context.triggered[0]
        if "Color by" in ctx["prop_id"] and plot_type != "box":
            raise PreventUpdate
        disable_plot_type = selected_page == "Plots per zone/region"
        if disable_plot_type:
            plot_type_value = None
        else:
            plot_type_value = (
                dash.no_update
                if plot_type is not None
                else plot_type_options[0]["value"]
            )
        plot_type_value = dash.no_update

        disable_y = (
            selected_page == "Plots per zone/region"
            or plot_type_value
            in [
                "distribution",
                "histogram",
            ]
            or plot_type
            in [
                "distribution",
                "histogram",
            ]
        )
        y_elm = (
            volumemodel.responses + volumemodel.selectors + volumemodel.parameters
            if plot_type == "scatter"
            else volumemodel.selectors
        )
        y_options = [{"label": elm, "value": elm} for elm in y_elm]

        if disable_y:
            y_value = None if selected_y is not None else dash.no_update
        else:
            if plot_type == "box" and selected_y is None:
                y_value = selected_color_by
            else:
                y_value = dash.no_update if selected_y in y_elm else y_elm[0]
        disable_subplot = selected_page != "Custom plotting"
        subplot_value = None if disable_subplot else selected_subplot_value
        if subplot_value == selected_subplot_value:
            subplot_value = dash.no_update

        colorby_elm = (
            list(volumemodel.dataframe.columns) + volumemodel.parameters
            if plot_type == "scatter"
            else volumemodel.selectors
        )
        colorby_options = [{"label": elm, "value": elm} for elm in colorby_elm]
        colorby_value = (
            dash.no_update if selected_color_by in colorby_elm else colorby_elm[0]
        )

        return (
            disable_plot_type,
            plot_type_value,
            disable_y,
            y_options,
            y_value,
            disable_subplot,
            subplot_value,
            colorby_options,
            colorby_value,
        )

    @app.callback(
        Output(
            {"id": get_uuid("filter-inplace-dist"), "element": "real-slider-wrapper"},
            "children",
        ),
        Input(
            {"id": get_uuid("filter-inplace-dist"), "element": "real-selector-option"},
            "value",
        ),
        State(get_uuid("selections-inplace-dist"), "data"),
    )
    def _update_realization_selected_info(input_selector, selections):
        reals = volumemodel.realizations
        prev_selection = (
            selections["filters"].get("REAL", []) if selections is not None else None
        )

        if input_selector == "range":
            min_value = (
                min(prev_selection) if prev_selection is not None else min(reals)
            )
            max_value = (
                max(prev_selection) if prev_selection is not None else max(reals)
            )
            return dcc.RangeSlider(
                id={
                    "id": get_uuid("filter-inplace-dist"),
                    "selected_reals": input_selector,
                },
                value=[min_value, max_value],
                min=min(reals),
                max=max(reals),
                marks={str(i): {"label": str(i)} for i in [min(reals), max(reals)]},
            )
        if input_selector == "select":
            elements = prev_selection if prev_selection is not None else reals
            return wcc.Select(
                id={
                    "id": get_uuid("filter-inplace-dist"),
                    "selected_reals": input_selector,
                },
                options=[{"label": i, "value": i} for i in reals],
                value=elements,
                multi=True,
                size=min(20, len(reals)),
                persistence=True,
                persistence_type="session",
            )

    @app.callback(
        Output({"id": get_uuid("filter-inplace-dist"), "selector": "SOURCE"}, "multi"),
        Output({"id": get_uuid("filter-inplace-dist"), "selector": "SOURCE"}, "value"),
        Output(
            {"id": get_uuid("filter-inplace-dist"), "selector": "ENSEMBLE"}, "multi"
        ),
        Output(
            {"id": get_uuid("filter-inplace-dist"), "selector": "ENSEMBLE"}, "value"
        ),
        Input(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Color by"},
            "value",
        ),
        Input(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Subplots"},
            "value",
        ),
        State({"id": get_uuid("filter-inplace-dist"), "selector": "SOURCE"}, "options"),
        State(
            {"id": get_uuid("filter-inplace-dist"), "selector": "ENSEMBLE"}, "options"
        ),
    )
    def _update_multi_option(colorby, subplot, source_values, ensemble_values):
        data_groupers = [colorby, subplot]
        return (
            "SOURCE" in data_groupers,
            [source_values[0]["value"]]
            if "SOURCE" not in data_groupers
            else [x["value"] for x in source_values],
            "ENSEMBLE" in data_groupers,
            [ensemble_values[0]["value"]]
            if "ENSEMBLE" not in data_groupers
            else [x["value"] for x in ensemble_values],
        )

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


def create_range_string(real_list):
    idx = 0
    ranges = [[real_list[0], real_list[0]]]
    for real in list(real_list):
        if ranges[idx][1] in (real, real - 1):
            ranges[idx][1] = real
        else:
            ranges.append([real, real])
            idx += 1

    return ", ".join(
        map(lambda p: "%s-%s" % tuple(p) if p[0] != p[1] else str(p[0]), ranges)
    )

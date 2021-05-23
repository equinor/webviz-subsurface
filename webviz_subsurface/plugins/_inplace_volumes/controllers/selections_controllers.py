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
        Input(
            {"id": get_uuid("selections-inplace-dist"), "settings": "sync_table"},
            "value",
        ),
        State({"id": get_uuid("selections-inplace-dist"), "selector": ALL}, "id"),
        State({"id": get_uuid("filter-inplace-dist"), "selector": ALL}, "id"),
        State({"id": get_uuid("filter-inplace-dist"), "selected_reals": ALL}, "id"),
    )
    def _update_selections(
        selectors,
        filters,
        reals,
        colorscale,
        sync_table,
        selctor_ids,
        filter_ids,
        real_ids,
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
        selections.update(sync_table=sync_table)
        selections.update(ctx_clicked=ctx["prop_id"])

        string_selected_reals = (
            create_range_string(real_list)
            if real_ids[0]["selected_reals"] == "select"
            else f"{real_list[0]}-{real_list[1]}"
        )
        return selections, string_selected_reals

    @app.callback(
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": ALL},
            "disabled",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": ALL},
            "value",
        ),
        Output(
            {"id": get_uuid("selections-inplace-dist"), "selector": ALL},
            "options",
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
        State(
            {"id": get_uuid("selections-inplace-dist"), "selector": ALL},
            "id",
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
        ids,
    ):
        ctx = dash.callback_context.triggered[0]
        if "Color by" in ctx["prop_id"] and plot_type != "box":
            raise PreventUpdate

        disable_plot_type = selected_page in [
            "Plots per zone/region",
            "Cumulative mean/p10/p90",
        ]
        if disable_plot_type:
            plot_type_value = None
        else:
            plot_type_value = (
                dash.no_update
                if plot_type is not None
                else plot_type_options[0]["value"]
            )

        disable_y = (
            selected_page
            in [
                "Plots per zone/region",
                "Cumulative mean/p10/p90",
            ]
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

        subplot_elm = (
            ["ENSEMBLE"]
            if selected_page == "Cumulative mean/p10/p90"
            else volumemodel.selectors
        )
        subplot_options = [{"label": elm, "value": elm} for elm in subplot_elm]

        disable_subplot = selected_page not in [
            "Custom plotting",
            "Cumulative mean/p10/p90",
        ]
        subplot_value = (
            None
            if disable_subplot
            and selected_subplot_value is not None
            or "page-selected" in ctx["prop_id"]
            and selected_page == "1 plot / 1 table"
            else dash.no_update
        )

        disable_colorby = selected_page in [
            "Plots per zone/region",
            "Cumulative mean/p10/p90",
        ]
        colorby_elm = (
            list(volumemodel.dataframe.columns) + volumemodel.parameters
            if plot_type == "scatter"
            else volumemodel.selectors
        )
        colorby_options = [{"label": elm, "value": elm} for elm in colorby_elm]
        colorby_value = (
            dash.no_update if selected_color_by in colorby_elm else colorby_elm[0]
        )
        if disable_colorby:
            colorby_value = None

        settings = {
            "Plot type": {
                "disable": disable_plot_type,
                "value": plot_type_value,
                "options": dash.no_update,
            },
            "Y Response": {
                "disable": disable_y,
                "value": y_value,
                "options": y_options,
            },
            "Color by": {
                "disable": disable_colorby,
                "value": colorby_value,
                "options": colorby_options,
            },
            "Subplots": {
                "disable": disable_subplot,
                "value": subplot_value,
                "options": subplot_options,
            },
        }
        disable_list = []
        value_list = []
        options_list = []
        for selector_id in ids:
            if selector_id["selector"] in settings:
                disable_list.append(settings[selector_id["selector"]]["disable"])
                value_list.append(settings[selector_id["selector"]]["value"])
                options_list.append(settings[selector_id["selector"]]["options"])
            else:
                disable_list.append(dash.no_update)
                value_list.append(dash.no_update)
                options_list.append(dash.no_update)

        return (
            disable_list,
            value_list,
            options_list,
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
        Input(
            {"id": get_uuid("selections-inplace-dist"), "selector": "Group by"},
            "value",
        ),
        State({"id": get_uuid("filter-inplace-dist"), "selector": "SOURCE"}, "options"),
        State(
            {"id": get_uuid("filter-inplace-dist"), "selector": "ENSEMBLE"}, "options"
        ),
    )
    def _update_multi_option(colorby, subplot, groupby, source_values, ensemble_values):
        data_groupers = [colorby, subplot]
        if groupby is not None:
            data_groupers.extend(groupby)
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

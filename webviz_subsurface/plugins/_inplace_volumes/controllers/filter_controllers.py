from typing import Callable

import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import webviz_core_components as wcc

import dash_table
import webviz_core_components as wcc


def filter_controllers(app: dash.Dash, get_uuid: Callable, volumemodel):
    @app.callback(
        Output(
            {"id": get_uuid("filter-inplace-dist"), "element": "text_selected_reals"},
            "children",
        ),
        Output(get_uuid("filter-inplace-dist"), "data"),
        Input({"id": get_uuid("filter-inplace-dist"), "selector": ALL}, "value"),
        Input(
            {"id": get_uuid("filter-inplace-dist"), "selected_reals": ALL},
            "value",
        ),
        State({"id": get_uuid("filter-inplace-dist"), "selector": ALL}, "id"),
        State({"id": get_uuid("filter-inplace-dist"), "selected_reals": ALL}, "id"),
    )
    def _update_filters(selectors, reals, selctor_ids, real_ids):
        if not reals or reals is None:
            raise PreventUpdate
        filters = {
            id_value["selector"]: values
            for id_value, values in zip(selctor_ids, selectors)
        }

        real_list = [int(real) for real in reals[0]]
        filters["REAL"] = (
            list(range(real_list[0], real_list[1] + 1))
            if real_ids[0]["selected_reals"] == "range"
            else real_list
        )

        string_selected_reals = (
            create_range_string(real_list)
            if real_ids[0]["selected_reals"] == "select"
            else f"{real_list[0]}-{real_list[1]}"
        )

        return string_selected_reals, filters

    @app.callback(
        Output(
            {"id": get_uuid("filter-inplace-dist"), "element": "real-slider-wrapper"},
            "children",
        ),
        Input(
            {"id": get_uuid("filter-inplace-dist"), "element": "real-selector-option"},
            "value",
        ),
        State(get_uuid("filter-inplace-dist"), "data"),
    )
    def _update_realization_selected_info_test(input_selector, previous_filter):

        reals = volumemodel.realizations
        prev_selection = (
            previous_filter.get("REAL", []) if previous_filter is not None else None
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
        Input(get_uuid("selections-inplace-dist"), "data"),
        State({"id": get_uuid("filter-inplace-dist"), "selector": "SOURCE"}, "options"),
        State(
            {"id": get_uuid("filter-inplace-dist"), "selector": "ENSEMBLE"}, "options"
        ),
    )
    def _update_multi_option(selections, source_values, ensemble_values):
        data_groupers = [selections[x] for x in ["Color by", "Subplots"]]
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

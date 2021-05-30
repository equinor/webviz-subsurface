from typing import Callable, Tuple, Union, Optional, Any

import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_subsurface._models import InplaceVolumesModel

# pylint: disable=too-many-statements, too-many-locals, too-many-arguments
def selections_controllers(
    app: dash.Dash, get_uuid: Callable, volumemodel: InplaceVolumesModel
) -> None:
    @app.callback(
        Output(get_uuid("selections-voldist"), "data"),
        Output(
            {"id": get_uuid("filter-voldist"), "element": "text_selected_reals"},
            "children",
        ),
        Input({"id": get_uuid("selections-voldist"), "selector": ALL}, "value"),
        Input({"id": get_uuid("filter-voldist"), "selector": ALL}, "value"),
        Input({"id": get_uuid("filter-voldist"), "selected_reals": ALL}, "value"),
        Input(
            {"id": get_uuid("selections-voldist"), "settings": "Colorscale"},
            "colorscale",
        ),
        State(get_uuid("page-selected-voldist"), "data"),
        State(get_uuid("selections-voldist"), "data"),
        State({"id": get_uuid("selections-voldist"), "selector": ALL}, "id"),
        State({"id": get_uuid("filter-voldist"), "selector": ALL}, "id"),
        State({"id": get_uuid("filter-voldist"), "selected_reals": ALL}, "id"),
    )
    def _update_selections(
        selectors: list,
        filters: list,
        reals: list,
        colorscale: str,
        selected_page: str,
        previous_selection: dict,
        selector_ids: dict,
        filter_ids: dict,
        real_ids: dict,
    ) -> Tuple[dict, str]:
        ctx = dash.callback_context.triggered[0]
        if ctx["prop_id"] == ".":
            raise PreventUpdate

        if previous_selection is None:
            previous_selection = {}

        page_selections = {
            id_value["selector"]: values
            for id_value, values in zip(selector_ids, selectors)
        }
        page_selections["filters"] = {
            id_value["selector"]: values
            for id_value, values in zip(filter_ids, filters)
        }
        real_list = [int(real) for real in reals[0]]
        page_selections["filters"].update(
            REAL=(
                list(range(real_list[0], real_list[1] + 1))
                if real_ids[0]["selected_reals"] == "range"
                else real_list
            )
        )

        page_selections.update(Colorscale=colorscale)
        page_selections.update(ctx_clicked=ctx["prop_id"])

        if previous_selection.get(selected_page) is not None:
            equal_list = []
            for selector, values in page_selections.items():
                if selector != "ctx_clicked":
                    equal_list.append(
                        values == previous_selection[selected_page][selector]
                    )

            page_selections.update(update=not all(equal_list))

        previous_selection[selected_page] = page_selections

        string_selected_reals = (
            create_range_string(real_list)
            if real_ids[0]["selected_reals"] == "select"
            else f"{real_list[0]}-{real_list[1]}"
        )
        return previous_selection, string_selected_reals

    @app.callback(
        Output({"id": get_uuid("selections-voldist"), "selector": ALL}, "disabled"),
        Output({"id": get_uuid("selections-voldist"), "selector": ALL}, "value"),
        Output({"id": get_uuid("selections-voldist"), "selector": ALL}, "options"),
        Input({"id": get_uuid("selections-voldist"), "selector": "Plot type"}, "value"),
        Input(get_uuid("page-selected-voldist"), "data"),
        Input({"id": get_uuid("selections-voldist"), "selector": "Color by"}, "value"),
        State({"id": get_uuid("selections-voldist"), "selector": ALL}, "value"),
        State({"id": get_uuid("selections-voldist"), "selector": ALL}, "options"),
        State({"id": get_uuid("selections-voldist"), "selector": ALL}, "id"),
        State(get_uuid("selections-voldist"), "data"),
    )
    # pylint: disable=too-many-locals
    def _plot_options(
        plot_type: str,
        selected_page: str,
        selected_color_by: list,
        selector_values: list,
        selector_options: list,
        selector_ids: list,
        previous_selection: Optional[dict],
    ) -> Tuple[list, list, list]:
        ctx = dash.callback_context.triggered[0]
        if (
            "Color by" in ctx["prop_id"]
            and plot_type != "box"
            or previous_selection is None
        ):
            raise PreventUpdate

        initial_page_load = selected_page not in previous_selection
        selections: Any = {}
        if initial_page_load:
            selections = {
                id_value["selector"]: options[0]["value"]
                if id_value["selector"] in ["Plot type", "X Response"]
                else None
                for id_value, options in zip(selector_ids, selector_options)
            }
        else:
            selections = (
                previous_selection.get(selected_page)
                if "page-selected" in ctx["prop_id"]
                else {
                    id_value["selector"]: values
                    for id_value, values in zip(selector_ids, selector_values)
                }
            )

        selectors_disable_in_pages = {
            "Plot type": ["per_zr", "conv"],
            "Y Response": ["per_zr", "conv"],
            "X Response": [],
            "Color by": ["per_zr", "conv"],
            "Subplots": ["per_zr", "1p1t"],
        }

        settings = {}
        for selector, disable_in_pages in selectors_disable_in_pages.items():
            disable = selected_page in disable_in_pages  # type: ignore
            if disable:
                value = None
            else:
                value = selections.get(selector)

            settings[selector] = {
                "disable": disable,
                "value": value,
            }

        if settings["Plot type"]["value"] in ["distribution", "histogram"]:
            settings["Y Response"]["disable"] = True
            settings["Y Response"]["value"] = None

        # update dropdown options based on plot type
        if settings["Plot type"]["value"] == "scatter":
            y_elm = x_elm = (
                volumemodel.responses + volumemodel.selectors + volumemodel.parameters
            )
        elif settings["Plot type"]["value"] == "box":
            y_elm = x_elm = volumemodel.responses + volumemodel.selectors
            if selections.get("Y Response") is None:
                settings["Y Response"]["value"] = selected_color_by
        else:
            y_elm = volumemodel.selectors
            x_elm = volumemodel.responses

        colorby_elm = (
            list(volumemodel.dataframe.columns) + volumemodel.parameters
            if settings["Plot type"]["value"] == "scatter"
            else volumemodel.selectors
        )
        settings["Y Response"]["options"] = [
            {"label": elm, "value": elm} for elm in y_elm
        ]
        settings["X Response"]["options"] = [
            {"label": elm, "value": elm} for elm in x_elm
        ]
        settings["Color by"]["options"] = [
            {"label": elm, "value": elm} for elm in colorby_elm
        ]

        disable_list = []
        value_list = []
        options_list = []
        for selector_id in selector_ids:
            if selector_id["selector"] in settings:
                disable_list.append(
                    settings[selector_id["selector"]].get("disable", dash.no_update)
                )
                value_list.append(
                    settings[selector_id["selector"]].get("value", dash.no_update)
                )
                options_list.append(
                    settings[selector_id["selector"]].get("options", dash.no_update)
                )
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
        Output({"id": get_uuid("filter-voldist"), "selector": "SOURCE"}, "multi"),
        Output({"id": get_uuid("filter-voldist"), "selector": "SOURCE"}, "value"),
        Output({"id": get_uuid("filter-voldist"), "selector": "ENSEMBLE"}, "multi"),
        Output({"id": get_uuid("filter-voldist"), "selector": "ENSEMBLE"}, "value"),
        Input({"id": get_uuid("selections-voldist"), "selector": ALL}, "value"),
        Input(get_uuid("page-selected-voldist"), "data"),
        Input(
            {"id": get_uuid("main-voldist"), "element": "plot-table-select"}, "value"
        ),
        State({"id": get_uuid("filter-voldist"), "selector": "SOURCE"}, "options"),
        State({"id": get_uuid("filter-voldist"), "selector": "ENSEMBLE"}, "options"),
        State({"id": get_uuid("selections-voldist"), "selector": ALL}, "id"),
        State(get_uuid("selections-voldist"), "data"),
    )
    def _update_filter_multi_option(
        selectors: list,
        page_selected: str,
        plot_table_select: str,
        source_options: dict,
        ensemble_options: dict,
        selector_ids: list,
        prev_selection: dict,
    ) -> tuple:
        ctx = dash.callback_context.triggered[0]
        page_selections = {
            id_value["selector"]: values
            for id_value, values in zip(selector_ids, selectors)
        }
        selected_data = [
            page_selections[x]
            for x in ["Color by", "Subplots", "X Response", "Y Response"]
        ]
        table_groups = (
            page_selections["Group by"]
            if page_selections["Group by"] is not None
            else []
        )

        if page_selected == "1p1t" and not page_selections["sync_table"]:
            selected_data.extend(table_groups)
        if (
            page_selected == "custom"
            and plot_table_select == "table"
            and not page_selections["sync_table"]
        ):
            selected_data = table_groups

        output = {}
        for selector, options in zip(
            ["SOURCE", "ENSEMBLE"], [source_options, ensemble_options]
        ):
            multi = selector in selected_data
            if not multi:
                values = [options[0]["value"]]
            else:
                values = (
                    prev_selection[page_selected]["filters"][selector]
                    if "page-selected" in ctx["prop_id"]
                    and prev_selection is not None
                    and page_selected in prev_selection
                    else [x["value"] for x in options]
                )
            output[selector] = {"multi": multi, "values": values}

        return (
            output["SOURCE"]["multi"],
            output["SOURCE"]["values"],
            output["ENSEMBLE"]["multi"],
            output["ENSEMBLE"]["values"],
        )

    @app.callback(
        Output(
            {"id": get_uuid("filter-voldist"), "element": "real-slider-wrapper"},
            "children",
        ),
        Input(
            {"id": get_uuid("filter-voldist"), "element": "real-selector-option"},
            "value",
        ),
        State(get_uuid("selections-voldist"), "data"),
        State(get_uuid("page-selected-voldist"), "data"),
    )
    # pylint: disable=inconsistent-return-statements
    def _update_realization_selected_info(
        input_selector: str, selections: dict, page_selected: str
    ) -> Union[dcc.RangeSlider, wcc.Select]:
        reals = volumemodel.realizations
        prev_selection = (
            selections[page_selected]["filters"].get("REAL", [])
            if selections is not None and page_selected in selections
            else None
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
                    "id": get_uuid("filter-voldist"),
                    "selected_reals": input_selector,
                },
                value=[min_value, max_value],
                min=min(reals),
                max=max(reals),
                marks={str(i): {"label": str(i)} for i in [min(reals), max(reals)]},
            )
        # if input_selector == "select"
        elements = prev_selection if prev_selection is not None else reals
        return wcc.Select(
            id={
                "id": get_uuid("filter-voldist"),
                "selected_reals": input_selector,
            },
            options=[{"label": i, "value": i} for i in reals],
            value=elements,
            multi=True,
            size=min(20, len(reals)),
            persistence=True,
            persistence_type="session",
        )


def create_range_string(real_list: list) -> str:
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

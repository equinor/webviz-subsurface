from typing import Callable, Optional, Any

import dash
from dash.dependencies import Input, Output, State, ALL
from dash.exceptions import PreventUpdate
import webviz_core_components as wcc
from webviz_subsurface._models import InplaceVolumesModel
from ..utils.utils import create_range_string, update_relevant_components


# pylint: disable=too-many-statements, too-many-locals, too-many-arguments
def selections_controllers(
    app: dash.Dash, get_uuid: Callable, volumemodel: InplaceVolumesModel
) -> None:
    @app.callback(
        Output(get_uuid("selections"), "data"),
        Input({"id": get_uuid("selections"), "tab": ALL, "selector": ALL}, "value"),
        Input({"id": get_uuid("filters"), "tab": ALL, "selector": ALL}, "value"),
        Input(
            {"id": get_uuid("selections"), "tab": "voldist", "settings": "Colorscale"},
            "colorscale",
        ),
        State(get_uuid("page-selected"), "data"),
        State(get_uuid("tabs"), "value"),
        State(get_uuid("selections"), "data"),
        State({"id": get_uuid("selections"), "tab": ALL, "selector": ALL}, "id"),
        State({"id": get_uuid("filters"), "tab": ALL, "selector": ALL}, "id"),
    )
    def _update_selections(
        selectors: list,
        filters: list,
        colorscale: str,
        selected_page: str,
        selected_tab: str,
        previous_selection: dict,
        selector_ids: list,
        filter_ids: list,
    ) -> dict:
        ctx = dash.callback_context.triggered[0]
        if ctx["prop_id"] == ".":
            raise PreventUpdate

        if previous_selection is None:
            previous_selection = {}

        page_selections = {
            id_value["selector"]: values
            for id_value, values in zip(selector_ids, selectors)
            if id_value["tab"] == selected_tab
        }
        page_selections["filters"] = {
            id_value["selector"]: values
            for id_value, values in zip(filter_ids, filters)
            if id_value["tab"] == selected_tab
        }

        page_selections.update(Colorscale=colorscale)
        page_selections.update(ctx_clicked=ctx["prop_id"])

        if previous_selection.get(selected_page) is None:
            page_selections.update(update=True)
        else:
            equal_list = []
            for selector, values in page_selections.items():
                if selector != "ctx_clicked":
                    equal_list.append(
                        values == previous_selection[selected_page][selector]
                    )
            page_selections.update(update=not all(equal_list))

        previous_selection[selected_page] = page_selections
        return previous_selection

    @app.callback(
        Output(
            {"id": get_uuid("selections"), "tab": "voldist", "selector": ALL},
            "disabled",
        ),
        Output(
            {"id": get_uuid("selections"), "tab": "voldist", "selector": ALL}, "value"
        ),
        Output(
            {"id": get_uuid("selections"), "tab": "voldist", "selector": ALL}, "options"
        ),
        Input(
            {"id": get_uuid("selections"), "tab": "voldist", "selector": "Plot type"},
            "value",
        ),
        Input(get_uuid("page-selected"), "data"),
        Input(
            {"id": get_uuid("selections"), "tab": "voldist", "selector": "Color by"},
            "value",
        ),
        State(
            {"id": get_uuid("selections"), "tab": "voldist", "selector": ALL}, "value"
        ),
        State(
            {"id": get_uuid("selections"), "tab": "voldist", "selector": ALL}, "options"
        ),
        State({"id": get_uuid("selections"), "tab": "voldist", "selector": ALL}, "id"),
        State(get_uuid("selections"), "data"),
        State(get_uuid("tabs"), "value"),
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
        selected_tab: str,
    ) -> tuple:
        ctx = dash.callback_context.triggered[0]
        if (
            selected_tab != "voldist"
            or ("Color by" in ctx["prop_id"] and plot_type not in ["box", "bar"])
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
            value = None if disable else selections.get(selector)

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
        elif settings["Plot type"]["value"] in ["box", "bar"]:
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
        return tuple(
            update_relevant_components(
                id_list=selector_ids,
                update_info=[
                    {
                        "new_value": values.get(prop, dash.no_update),
                        "conditions": {"selector": selector},
                    }
                    for selector, values in settings.items()
                ],
            )
            for prop in ["disable", "value", "options"]
        )

    @app.callback(
        Output({"id": get_uuid("filters"), "tab": ALL, "selector": ALL}, "multi"),
        Output({"id": get_uuid("filters"), "tab": ALL, "selector": ALL}, "value"),
        Output(
            {"id": get_uuid("filters"), "tab": ALL, "element": "real_text"}, "children"
        ),
        Input({"id": get_uuid("selections"), "tab": ALL, "selector": ALL}, "value"),
        Input(get_uuid("page-selected"), "data"),
        Input(
            {"id": get_uuid("main-voldist"), "element": "plot-table-select"}, "value"
        ),
        Input({"id": get_uuid("filters"), "tab": ALL, "component_type": ALL}, "value"),
        State({"id": get_uuid("selections"), "tab": ALL, "selector": ALL}, "id"),
        State(get_uuid("selections"), "data"),
        State(get_uuid("tabs"), "value"),
        State({"id": get_uuid("filters"), "tab": ALL, "selector": ALL}, "options"),
        State({"id": get_uuid("filters"), "tab": ALL, "selector": ALL}, "id"),
        State({"id": get_uuid("filters"), "tab": ALL, "component_type": ALL}, "id"),
        State({"id": get_uuid("filters"), "tab": ALL, "element": "real_text"}, "id"),
    )
    def _update_filter_options(
        selectors: list,
        selected_page: str,
        plot_table_select: str,
        reals: list,
        selector_ids: list,
        prev_selection: dict,
        selected_tab: str,
        filter_options: list,
        filter_ids: list,
        reals_ids: list,
        real_string_ids: list,
    ) -> tuple:
        ctx = dash.callback_context.triggered[0]

        page_selections = {
            id_value["selector"]: values
            for id_value, values in zip(selector_ids, selectors)
            if id_value["tab"] == selected_tab
        }
        page_filter_options = {
            id_value["selector"]: values
            for id_value, values in zip(filter_ids, filter_options)
            if id_value["tab"] == selected_tab
        }

        selected_data = []
        if selected_tab == "voldist":
            selected_data = [
                page_selections[x]
                for x in ["Color by", "Subplots", "X Response", "Y Response"]
            ]
            table_groups = (
                page_selections["Group by"]
                if page_selections["Group by"] is not None
                else []
            )

            if selected_page == "1p1t" and not page_selections["sync_table"]:
                selected_data.extend(table_groups)
            if (
                selected_page == "custom"
                and plot_table_select == "table"
                and not page_selections["sync_table"]
            ):
                selected_data = table_groups

        output = {}
        for selector in ["SOURCE", "ENSEMBLE"]:
            multi = selector in selected_data
            if not multi:
                values = [page_filter_options[selector][0]["value"]]
            else:
                values = (
                    prev_selection[selected_page]["filters"][selector]
                    if "page-selected" in ctx["prop_id"]
                    and prev_selection is not None
                    and selected_page in prev_selection
                    else [x["value"] for x in page_filter_options[selector]]
                )
            output[selector] = {"multi": multi, "values": values}

        # realization
        index = [x["tab"] for x in reals_ids].index(selected_tab)
        real_list = [int(real) for real in reals[index]]

        if reals_ids[index]["component_type"] == "range":
            real_list = list(range(real_list[0], real_list[1] + 1))
            text = f"{real_list[0]}-{real_list[-1]}"
        else:
            text = create_range_string(real_list)

        output["REAL"] = {"values": real_list}

        return (
            update_relevant_components(
                id_list=filter_ids,
                update_info=[
                    {
                        "new_value": output[item].get("multi", dash.no_update),
                        "conditions": {"tab": selected_tab, "selector": item},
                    }
                    for item in ["SOURCE", "ENSEMBLE", "REAL"]
                ],
            ),
            update_relevant_components(
                id_list=filter_ids,
                update_info=[
                    {
                        "new_value": output[item].get("values", dash.no_update),
                        "conditions": {"tab": selected_tab, "selector": item},
                    }
                    for item in ["SOURCE", "ENSEMBLE", "REAL"]
                ],
            ),
            update_relevant_components(
                id_list=real_string_ids,
                update_info=[{"new_value": text, "conditions": {"tab": selected_tab}}],
            ),
        )

    @app.callback(
        Output(
            {
                "id": get_uuid("filters"),
                "tab": ALL,
                "element": "real-slider-wrapper",
            },
            "children",
        ),
        Input(
            {
                "id": get_uuid("filters"),
                "tab": ALL,
                "element": "real-selector-option",
            },
            "value",
        ),
        State(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
        State(get_uuid("tabs"), "value"),
        State(
            {
                "id": get_uuid("filters"),
                "tab": ALL,
                "element": "real-selector-option",
            },
            "id",
        ),
        State(
            {
                "id": get_uuid("filters"),
                "tab": ALL,
                "element": "real-slider-wrapper",
            },
            "id",
        ),
    )
    def _update_realization_selected_info(
        input_selectors: list,
        selections: dict,
        selected_page: str,
        selected_tab: str,
        input_ids: list,
        wrapper_ids: list,
    ) -> list:
        reals = volumemodel.realizations
        prev_selection = (
            selections[selected_page]["filters"].get("REAL", [])
            if selections is not None and selected_page in selections
            else None
        )

        page_value = [
            value
            for id_value, value in zip(input_ids, input_selectors)
            if id_value["tab"] == selected_tab
        ]

        if page_value[0] == "range":
            min_value = (
                min(prev_selection) if prev_selection is not None else min(reals)
            )
            max_value = (
                max(prev_selection) if prev_selection is not None else max(reals)
            )
            return update_relevant_components(
                id_list=wrapper_ids,
                update_info=[
                    {
                        "new_value": wcc.RangeSlider(
                            id={
                                "id": get_uuid("filters"),
                                "tab": selected_tab,
                                "component_type": page_value[0],
                            },
                            value=[min_value, max_value],
                            min=min(reals),
                            max=max(reals),
                            marks={
                                str(i): {"label": str(i)}
                                for i in [min(reals), max(reals)]
                            },
                        ),
                        "conditions": {"tab": selected_tab},
                    }
                ],
            )

        # if input_selector == "select"
        elements = prev_selection if prev_selection is not None else reals
        return update_relevant_components(
            id_list=wrapper_ids,
            update_info=[
                {
                    "new_value": wcc.Select(
                        id={
                            "id": get_uuid("filters"),
                            "tab": selected_tab,
                            "component_type": page_value[0],
                        },
                        options=[{"label": i, "value": i} for i in reals],
                        value=elements,
                        multi=True,
                        size=min(20, len(reals)),
                        persistence=True,
                        persistence_type="session",
                    ),
                    "conditions": {"tab": selected_tab},
                }
            ],
        )

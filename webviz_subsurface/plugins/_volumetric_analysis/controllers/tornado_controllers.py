from typing import Any, Callable, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, callback_context, no_update
from dash.exceptions import PreventUpdate
from webviz_config import WebvizConfigTheme

from webviz_subsurface._components.tornado._tornado_bar_chart import TornadoBarChart
from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_table import TornadoTable
from webviz_subsurface._models import InplaceVolumesModel

from ..utils.table_and_figure_utils import create_data_table, create_table_columns
from ..utils.utils import update_relevant_components
from ..views.tornado_view import tornado_plots_layout


# pylint: disable=too-many-locals
def tornado_controllers(
    get_uuid: Callable, volumemodel: InplaceVolumesModel, theme: WebvizConfigTheme
) -> None:
    @callback(
        Output({"id": get_uuid("main-tornado"), "page": ALL}, "children"),
        Input(get_uuid("selections"), "data"),
        State(get_uuid("page-selected"), "data"),
        State({"id": get_uuid("main-tornado"), "page": ALL}, "id"),
    )
    def _update_tornado_pages(
        selections: dict, page_selected: str, id_list: list
    ) -> go.Figure:

        if page_selected not in ["torn_multi", "torn_bulk_inplace"]:
            raise PreventUpdate

        selections = selections[page_selected]
        if not selections["update"]:
            raise PreventUpdate

        subplots = selections["Subplots"] is not None
        groups = ["REAL", "ENSEMBLE", "SENSNAME", "SENSCASE", "SENSTYPE"]
        if subplots and selections["Subplots"] not in groups:
            groups.append(selections["Subplots"])

        filters = selections["filters"].copy()

        figures = []
        tables = []
        responses = (
            ["BULK", selections["Response"]]
            if page_selected == "torn_bulk_inplace"
            else [selections["Response"]]
        )
        for response in responses:
            if not (response == "BULK" and page_selected == "torn_bulk_inplace"):
                if selections["Reference"] not in selections["Sensitivities"]:
                    selections["Sensitivities"].append(selections["Reference"])
                filters.update(SENSNAME=selections["Sensitivities"])

            dframe = volumemodel.get_df(filters=filters, groups=groups)
            dframe.rename(columns={response: "VALUE"}, inplace=True)

            df_groups = (
                dframe.groupby(selections["Subplots"]) if subplots else [(None, dframe)]
            )

            for group, df in df_groups:
                figure, table, columns = tornado_figure_and_table(
                    df=df,
                    response=response,
                    selections=selections,
                    theme=theme,
                    sensitivity_colors=sens_colors(),
                    font_size=max((20 - (0.4 * len(df_groups))), 10),
                    group=group,
                )
                figures.append(figure)
                if selections["tornado_table"]:
                    tables.append(table)

        if selections["Shared axis"] and selections["Scale"] != "True":
            x_absmax = max([max(abs(trace.x)) for fig in figures for trace in fig.data])
            for fig in figures:
                fig.update_layout(xaxis_range=[-x_absmax, x_absmax])

        return update_relevant_components(
            id_list=id_list,
            update_info=[
                {
                    "new_value": tornado_plots_layout(
                        figures=figures,
                        table=create_data_table(
                            columns=columns,
                            selectors=[selections["Subplots"]] if subplots else [],
                            data=[x for table in tables for x in table],
                            height="42vh",
                            table_id={"table_id": f"{page_selected}-torntable"},
                        ),
                    ),
                    "conditions": {"page": page_selected},
                }
            ],
        )

    @callback(
        Output(
            {"id": get_uuid("selections"), "selector": ALL, "tab": "tornado"}, "options"
        ),
        Output(
            {"id": get_uuid("selections"), "selector": ALL, "tab": "tornado"}, "value"
        ),
        Output(
            {"id": get_uuid("selections"), "selector": ALL, "tab": "tornado"},
            "disabled",
        ),
        Input(get_uuid("page-selected"), "data"),
        State(get_uuid("tabs"), "value"),
        State({"id": get_uuid("selections"), "selector": ALL, "tab": "tornado"}, "id"),
        State(
            {"id": get_uuid("selections"), "selector": ALL, "tab": "tornado"}, "value"
        ),
        State(get_uuid("selections"), "data"),
    )
    def _update_tornado_selections(
        selected_page: str,
        selected_tab: str,
        selector_ids: list,
        selector_values: list,
        previous_selection: Optional[dict],
    ) -> tuple:
        if selected_tab != "tornado" or previous_selection is None:
            raise PreventUpdate

        ctx = callback_context.triggered[0]
        initial_page_load = selected_page not in previous_selection

        selections: Any = (
            previous_selection.get(selected_page)
            if "page-selected" in ctx["prop_id"] and selected_page in previous_selection
            else {
                id_value["selector"]: values
                for id_value, values in zip(selector_ids, selector_values)
            }
        )

        settings = {}
        if selected_page == "torn_bulk_inplace":
            volume_options = [
                x for x in ["STOIIP", "GIIP"] if x in volumemodel.responses
            ]
            settings["Response"] = {
                "options": [{"label": i, "value": i} for i in volume_options],
                "value": volume_options[0]
                if initial_page_load
                else selections["Response"],
                "disabled": len(volume_options) == 1,
            }
        else:
            responses = [x for x in volumemodel.responses if x not in ["BO", "BG"]]
            settings["Response"] = {
                "options": [{"label": i, "value": i} for i in responses],
                "disabled": False,
                "value": selections["Response"],
            }

        settings["tornado_table"] = {"value": selections["tornado_table"]}

        disable_subplots = selected_page != "torn_multi"
        settings["Subplots"] = {
            "disabled": disable_subplots,
            "value": None if disable_subplots else selections["Subplots"],
        }

        return tuple(
            update_relevant_components(
                id_list=selector_ids,
                update_info=[
                    {
                        "new_value": values.get(prop, no_update),
                        "conditions": {"selector": selector},
                    }
                    for selector, values in settings.items()
                ],
            )
            for prop in ["options", "value", "disabled"]
        )

    def sens_colors() -> dict:
        colors = [
            "#FF1243",
            "#243746",
            "#007079",
            "#80B7BC",
            "#919BA2",
            "#BE8091",
            "#B2D4D7",
            "#FF597B",
            "#BDC3C7",
            "#D8B2BD",
            "#FFE7D6",
            "#D5EAF4",
            "#FF88A1",
        ]
        sensitivities = volumemodel.dataframe["SENSNAME"].unique()
        return dict(zip(sensitivities, colors * 10))


def tornado_figure_and_table(
    df: pd.DataFrame,
    response: str,
    selections: dict,
    theme: WebvizConfigTheme,
    sensitivity_colors: dict,
    font_size: float,
    group: Optional[str] = None,
) -> Tuple[go.Figure, List[dict], List[dict]]:

    tornado_data = TornadoData(
        dframe=df,
        reference=selections["Reference"],
        response_name=response,
        scale=selections["Scale"],
        cutbyref=bool(selections["Remove no impact"]),
    )
    figure = TornadoBarChart(
        tornado_data=tornado_data,
        plotly_theme=theme.plotly_theme,
        label_options=selections["labeloptions"],
        number_format="#.3g",
        use_true_base=selections["Scale"] == "True",
        show_realization_points=bool(selections["real_scatter"]),
        show_reference=not (
            selections["Subplots"] is not None and selections["tornado_table"]
        ),
        color_by_sensitivity=selections["color_by_sens"],
        sensitivity_color_map=sensitivity_colors,
    ).figure

    figure.update_xaxes(side="bottom", title=None).update_layout(
        title_text=f"Tornadoplot for {response} <br>"
        + f"Fluid zone: {(' + ').join(selections['filters']['FLUID_ZONE'])}"
        if group is None
        else f"{response} {group}",
        title_font_size=font_size,
        margin={"t": 70},
    )

    table_data, columns = create_tornado_table(
        tornado_data, subplots=selections["Subplots"], group=group
    )
    return figure, table_data, columns


def create_tornado_table(
    tornado_data: TornadoData, subplots: str, group: Optional[str]
) -> Tuple[List[dict], List[dict]]:
    tornado_table = TornadoTable(tornado_data=tornado_data)
    table_data = tornado_table.as_plotly_table
    for data in table_data:
        data["Reference"] = tornado_data.reference_average
        if group is not None:
            data[subplots] = group

    columns = create_table_columns(columns=[subplots]) if subplots is not None else []
    columns.extend(tornado_table.columns)
    columns.extend(
        create_table_columns(columns=["Reference"], use_si_format=["Reference"])
    )
    return table_data, columns

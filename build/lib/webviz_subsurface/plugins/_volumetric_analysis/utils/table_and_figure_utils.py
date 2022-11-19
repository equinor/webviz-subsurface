import math
from typing import List, Optional, Union

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dash_table


def create_table_columns(
    columns: list,
    text_columns: list = None,
    use_si_format: Optional[list] = None,
    use_percentage: Optional[list] = None,
) -> List[dict]:

    text_columns = text_columns if text_columns is not None else []
    use_si_format = use_si_format if use_si_format is not None else []
    use_percentage = use_percentage if use_percentage is not None else []

    table_columns = []
    for col in columns:
        data = {"id": col, "name": col}
        if col not in text_columns:
            data["type"] = "numeric"
            if col in use_percentage:
                data["format"] = {"specifier": ".1f"}
            elif col in use_si_format:
                data["format"] = {"locale": {"symbol": ["", ""]}, "specifier": "$.4s"}
            else:
                data["format"] = {"specifier": ".3~r"}
        table_columns.append(data)
    return table_columns


def create_data_table(
    columns: list,
    height: str,
    data: List[dict],
    table_id: dict,
    selectors: Optional[list] = None,
    style_cell: Optional[dict] = None,
    style_cell_conditional: Optional[list] = None,
    style_data_conditional: Optional[list] = None,
) -> Union[list, wcc.WebvizPluginPlaceholder]:

    if not data:
        return []

    if selectors is None:
        selectors = []
    conditional_cell_style = [
        {
            "if": {"column_id": selectors + ["Response", "Property", "Sensitivity"]},
            "width": "10%",
            "textAlign": "left",
        },
        {"if": {"column_id": "FLUID_ZONE"}, "width": "10%", "textAlign": "right"},
    ]
    if style_cell_conditional is not None:
        conditional_cell_style.extend(style_cell_conditional)

    style_data_conditional = (
        style_data_conditional if style_data_conditional is not None else []
    )
    style_data_conditional.extend(fluid_table_style())

    return wcc.WebvizPluginPlaceholder(
        id={"request": "table_data", "table_id": table_id["table_id"]},
        buttons=["expand", "download"],
        children=dash_table.DataTable(
            id=table_id,
            sort_action="native",
            sort_mode="multi",
            filter_action="native",
            columns=columns,
            data=data,
            style_as_list_view=True,
            style_cell=style_cell,
            style_cell_conditional=conditional_cell_style,
            style_data_conditional=style_data_conditional,
            style_table={
                "height": height,
                "overflowY": "auto",
            },
        ),
    )


def fluid_table_style() -> list:
    fluid_colors = {
        "oil": "#007079",
        "gas": "#FF1243",
        "water": "#ADD8E6",
    }
    return [
        {
            "if": {
                "filter_query": "{FLUID_ZONE} = " + f"'{fluid}'",
                "column_id": "FLUID_ZONE",
            },
            "color": color,
            "fontWeight": "bold",
        }
        for fluid, color in fluid_colors.items()
    ]


def fluid_annotation(selections: dict) -> dict:
    fluid_text = (" + ").join(selections["filters"]["FLUID_ZONE"])
    return dict(
        visible=bool(selections["Fluid annotation"])
        and selections["Subplots"] != "FLUID_ZONE",
        x=1,
        y=1,
        xref="paper",
        yref="paper",
        showarrow=False,
        text="Fluid zone<br>" + fluid_text,
        font=dict(size=15, color="black"),
        bgcolor="#E8E8E8",
    )


def add_correlation_line(figure: go.Figure, xy_min: float, xy_max: float) -> go.Figure:
    return figure.add_shape(
        type="line",
        layer="below",
        xref="x",
        yref="y",
        x0=xy_min,
        y0=xy_min,
        x1=xy_max,
        y1=xy_max,
        line=dict(color="black", width=2, dash="dash"),
    )


def create_figure_matrix(figures: List[go.Figure]) -> List[List[go.Figure]]:
    """Convert a list of figures into a matrix for display"""
    figs_in_row = min(
        min([x for x in range(100) if (x * (x + 1)) > len(figures)]),
        20,
    )
    len_of_matrix = figs_in_row * math.ceil(len(figures) / figs_in_row)
    # extend figure list with None to fit size of matrix
    figures.extend([None] * (len_of_matrix - len(figures)))
    return [figures[i : i + figs_in_row] for i in range(0, len_of_matrix, figs_in_row)]


def update_tornado_figures_xaxis(figures: List[go.Figure]) -> None:
    """
    Update the x-axis range for a list of tornado figures with the maximum absolute
    x-value from all figures. Axis will be centered around 0.
    """
    x_absmax = max([max(abs(trace.x)) for fig in figures for trace in fig.data])
    for fig in figures:
        fig.update_layout(xaxis_range=[-x_absmax, x_absmax])

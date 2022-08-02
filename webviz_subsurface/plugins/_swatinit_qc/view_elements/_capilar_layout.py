from typing import List

import pandas as pd
import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dash_table, dcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._swatint import SwatinitQcDataModel
from ._dash_table import DashTable
from ._fullscreen import FullScreen
from ._layout_style import LayoutStyle


class CapilarViewelement(ViewElementABC):
    """All elements visible in the 'Caplillary pressure scaling'-tab
    gathered in one viewelement"""

    class IDs:
        # pylint: disable=too-few-public-methods
        INFO_TEXT = "info-text"
        MAP = "map"
        TABLE = "table"

    def __init__(
        self,
        datamodel: SwatinitQcDataModel,
        dframe: pd.DataFrame,
        selectors: list,
        map_figure: go.Figure,
    ) -> None:
        super().__init__()
        self.datamodel = datamodel
        self.dframe = dframe
        self.selectors = selectors
        self.map_figure = map_figure

    def inner_layout(self) -> List[Component]:
        return [
            wcc.Header("Maximum capillary pressure scaling", style=LayoutStyle.HEADER),
            wcc.FlexBox(
                style={"margin-top": "10px", "height": "40vh"},
                children=[
                    wcc.FlexColumn(
                        dcc.Markdown(pc_columns_description()),
                        id=self.register_component_unique_id(
                            CapilarViewelement.IDs.INFO_TEXT
                        ),
                        flex=7,
                        style={"margin-right": "40px"},
                    ),
                    wcc.FlexColumn(
                        FullScreen(
                            wcc.Graph(
                                style={"height": "100%", "min-height": "35vh"},
                                figure=self.map_figure,
                                id=self.register_component_unique_id(
                                    CapilarViewelement.IDs.MAP
                                ),
                            )
                        ),
                        flex=3,
                    ),
                ],
            ),
            self.max_pc_table(text_columns=self.selectors),
        ]

    @property
    def max_pc_table(self, text_columns: list) -> dash_table:
        return DashTable(
            data=self.dframe.to_dict("records"),
            columns=[
                {
                    "name": i,
                    "id": i,
                    "type": "numeric" if i not in text_columns else "text",
                    "format": {"specifier": ".4~r"} if i not in text_columns else {},
                }
                for i in self.dframe.columns
            ],
            height="48vh",
            sort_action="native",
            fixed_rows={"headers": True},
            style_cell={
                "minWidth": LayoutStyle.TABLE_CELL_WIDTH,
                "maxWidth": LayoutStyle.TABLE_CELL_WIDTH,
                "width": LayoutStyle.TABLE_CELL_WIDTH,
            },
            style_data_conditional=[
                {
                    "if": {
                        "filter_query": f"{{{self.datamodel.COLNAME_THRESHOLD}}} > 0",
                    },
                    **LayoutStyle.TABLE_HIGHLIGHT,
                },
            ],
        )


def pc_columns_description() -> str:
    return f"""
> **Column descriptions**
> - **PCOW_MAX**  - Maximum capillary pressure from the input SWOF/SWFN tables
> - **PC_SCALING**  - Maximum capillary pressure scaling applied
> - **PPCW**  - Maximum capillary pressure after scaling
> - **{SwatinitQcDataModel.COLNAME_THRESHOLD}**  - Column showing how many percent of the pc-scaled dataset that match the user-selected threshold
*PPCW = PCOW_MAX \* PC_SCALING*
A threshold for the maximum capillary scaling can be set in the menu.
The table will show how many percent of the dataset that exceeds this value, and cells above the threshold will be shown in the map ➡️
"""

from cgi import print_arguments
from typing import List

import pandas as pd
import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dash_table, dcc
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._swatint import SwatinitQcDataModel
from ..views.capilar_tab.settings import CapilarFilters
from ._dash_table import DashTable
from ._fullscreen import FullScreen
from ._layout_style import LayoutStyle
from ._map_figure import MapFigure

# This can be moved into a view_elements folder in views > capilar_tab


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
    ) -> None:
        super().__init__()
        self.datamodel = datamodel

        self.init_eqlnums = self.datamodel.eqlnums[:1]
        continous_filters = (
            [self.datamodel.dframe[col].min(), self.datamodel.dframe[col].max()]
            for col in self.datamodel.filters_continuous
        )

        continous_filters_ids = (
            [
                {
                    "id": CapilarFilters.IDs.RANGE_FILTERS,
                    "col": col,
                }
            ]
            for col in self.datamodel.filters_continuous
        )

        print({"EQLNUM": self.init_eqlnums})
        self.dframe = self.datamodel.get_dataframe(
            filters={"EQLNUM": self.init_eqlnums},
            range_filters=zip_filters(continous_filters, continous_filters_ids),
        )

        df_for_map = datamodel.resample_dataframe(self.dframe, max_points=10000)
        self.selectors = self.datamodel.SELECTORS

        self.map_figure = MapFigure(
            dframe=df_for_map,
            color_by="EQLNUM",
            faultlinedf=datamodel.faultlines_df,
            colormap=datamodel.create_colormap("EQLNUM"),
        ).figure

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
            self.max_pc_table,
        ]

    @property
    def max_pc_table(self) -> dash_table:
        return DashTable(
            id=self.register_component_unique_id(CapilarViewelement.IDs.TABLE),
            data=self.dframe.to_dict("records"),
            columns=[
                {
                    "name": i,
                    "id": i,
                    "type": "numeric" if i not in self.selectors else "text",
                    "format": {"specifier": ".4~r"} if i not in self.selectors else {},
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


# pylint: disable=anomalous-backslash-in-string
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


def zip_filters(filter_values: list, filter_ids: list) -> dict:
    for values, id_val in zip(filter_values, filter_ids):
        print("val: ", values)
        print("id: ", id_val)
    return {id_val["col"]: values for values, id_val in zip(filter_values, filter_ids)}

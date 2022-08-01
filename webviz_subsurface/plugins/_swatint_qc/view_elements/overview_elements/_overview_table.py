from dash import html
from webviz_config.webviz_plugin_subclasses import ViewElementABC

from .._dash_table import DashTable
from .._layout_style import LayoutStyle


class OverviewTable(ViewElementABC):
    class IDs:
        LABEL = "label"
        TABLE = "table"

    def __init__(self, datamodel) -> None:
        super().__init__()
        self.data, self.columns = datamodel.table_data_qc_vol_overview()
        self.label = (
            "Table showing volume changes from SWATINIT to SWAT at Reservoir conditions"
        )

    def inner_layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    html.Label(self.label, className="webviz-underlined-label"),
                    style={"margin-bottom": "20px"},
                ),
                DashTable(
                    data=self.data,
                    columns=self.columns,
                    style_data_conditional=[
                        {
                            "if": {"row_index": [0, len(self.data) - 1]},
                            **LayoutStyle.TABLE_HIGHLIGHT,
                        },
                    ],
                ),
            ],
        )

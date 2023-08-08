from dash import dash_table, html
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewElementABC


class TableViewElement(ViewElementABC):
    class Ids(StrEnum):
        TABLE = "table"

    def __init__(self) -> None:
        super().__init__()

    def inner_layout(self) -> html.Div:
        return html.Div(
            children=[
                html.Div(
                    children=dash_table.DataTable(
                        id=self.register_component_unique_id(self.Ids.TABLE),
                        sort_action="native",
                        sort_mode="multi",
                        filter_action="native",
                        style_as_list_view=True,
                        style_table={
                            "height": "84vh",
                            "overflowY": "auto",
                        },
                        style_cell={
                            "whiteSpace": "normal",
                            "height": "auto",
                            "textAlign": "left",
                            "width": "auto",
                        },
                    ),
                ),
            ]
        )

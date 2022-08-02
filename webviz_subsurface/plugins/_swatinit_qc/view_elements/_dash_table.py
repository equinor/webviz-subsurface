from typing import Any, List

from dash import dash_table

from ._layout_style import LayoutStyle


class DashTable(dash_table.DataTable):
    def __init__(
        self, data: List[dict], columns: List[dict], height: str = "none", **kwargs: Any
    ) -> None:
        super().__init__(
            data=data,
            columns=columns,
            style_table={"height": height, **LayoutStyle.TABLE_STYLE},
            style_as_list_view=True,
            css=LayoutStyle.TABLE_CSS,
            style_header=LayoutStyle.TABLE_HEADER,
            **kwargs,
        )

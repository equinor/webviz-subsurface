import warnings
from typing import Dict, List, Optional

import dash_daq
import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, State, dash_table, dcc, html
from dash.exceptions import PreventUpdate


class ColorPicker:
    """Component that can be added to a plugin to update colors interactively.
    The component is rendered as a table from a provided dataframe.
    'COLOR' is a required column and is rendered as a clickable row that displays
    a color picker for that row to change the color. The current colors can be
    retrieved as a list from a dcc.Store component"""

    def __init__(self, app: Dash, uuid: str, dframe: pd.DataFrame) -> None:
        """
        * **`app`:** The Dash app instance.
        * **`uuid`:** Unique id (use the plugin id).
        * **`dframe`:** Dataframe, where each row will be a row in a visualized table. \
            'COLOR' column with hexadecimal color strings is required. All other \
            colors must be validatable as categorical columns.
        """
        self._dframe = dframe
        self._check_colors()
        self._set_categorical()
        self._uuid = uuid
        self._set_callbacks(app)

    def _check_colors(self) -> None:
        """Check if color format is correct"""
        if "COLOR" not in self._dframe.columns:
            raise KeyError("Dataframe is missing 'COLOR' column")
        for hex_value in self._dframe["COLOR"].unique():
            if not hex_value.startswith("#"):
                raise ValueError(
                    "Incorrent color string found. "
                    f"{hex_value} is not a hex color string."
                )

    def _set_categorical(self) -> None:
        """Force all columns to be categorical"""
        for column in self._dframe.columns:
            try:
                self._dframe[column] = pd.Categorical(self._dframe[column])
            except ValueError as exc:
                raise ValueError(f"Cannot use {column} for ColorPicker") from exc

    @property
    def _columns(self) -> List[Dict[str, str]]:
        """Generate column attribute for the Dash Datatable"""
        columns = [
            {"id": col, "name": col, "selectable": False}
            for col in self._dframe.columns
            if col != "COLOR"
        ]
        columns.append({"id": "COLOR", "name": "Color", "selectable": True})
        return columns

    def get_color(self, color_list: List, filter_query: Dict[str, str]) -> str:
        """Helper function to use in a callback to get a single color.
        Give in the list of active colors, and a dictionary of {column:name:value}
        for each column in the color table"""
        filter_mask = [
            (self._dframe[column] == value) for column, value in filter_query.items()
        ]
        mask = np.array(filter_mask).all(axis=0)
        df = self._dframe.loc[mask]
        if len(df["COLOR"].unique()) < 1:
            warnings.warn("No color found for filter!")
            return "#ffffff"
        if len(df["COLOR"].unique()) > 1:
            warnings.warn("Multiple colors found for filter. " "Return first color.")
        return color_list[df.index[0]]

    @property
    def layout(self) -> html.Div:
        """Returns a table with dataframe columns and clickable color column
        Add this to the layout of the plugin"""
        return html.Div(
            style={
                "fontSize": "0.8em",
                "height": "600px",
                "fontColor": "black",
            },
            children=[
                dcc.Store(
                    id=self.color_store_id,
                    data=list(self._dframe["COLOR"].values),
                    storage_type="session",
                ),
                wcc.FlexBox(
                    style={"display": "flex"},
                    children=[
                        html.Div(
                            style={"flex": 2, "overflowY": "scroll", "height": "550px"},
                            children=dash_table.DataTable(
                                id={"id": self._uuid, "element": "table"},
                                fixed_rows={"headers": True},
                                columns=self._columns,
                                style_header={
                                    "opacity": 0.5,
                                },
                                data=self._dframe.to_dict("records"),
                                style_data_conditional=self.data_style_in_table,
                            ),
                        ),
                        html.Div(
                            id={"id": self._uuid, "element": "pickerwrapper"},
                            style={"flex": 1},
                            children=[
                                html.Label(
                                    "Click on a table row to get a color picker",
                                    style={"padding": "15px"},
                                )
                            ],
                        ),
                    ],
                ),
            ],
        )

    @property
    def data_style_in_table(self) -> List[Dict[str, str]]:
        style_data = [
            {
                "if": {"row_index": idx, "column_id": "COLOR"},
                "background-color": self._dframe.iloc[idx]["COLOR"],
                "color": self._dframe.iloc[idx]["COLOR"],
            }
            for idx in range(0, self._dframe.shape[0])
        ]
        style_data.extend(
            [
                {
                    "if": {"state": "active"},
                    "backgroundColor": "white",
                    "border": "white",
                },
            ]
        )
        return style_data

    @property
    def color_store_id(self) -> Input:
        """Dom id for the current colors. Use the 'data' attribute in a callback
        to get the list of current colors"""
        return {"id": self._uuid, "element": "store"}

    def _set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(
                {"id": self._uuid, "element": "pickerwrapper"},
                "children",
            ),
            Input(
                {"id": self._uuid, "element": "table"},
                "active_cell",
            ),
            State({"id": self._uuid, "element": "store"}, "data"),
        )
        def _show_color_picker(
            cell: Optional[Dict], current_color_store: List[str]
        ) -> dash_daq.ColorPicker:
            """Render the colorpicker"""
            if not cell:
                raise PreventUpdate
            row_no = cell["row"]
            return dash_daq.ColorPicker(  # pylint: disable=not-callable
                {"id": self._uuid, "element": "picker"},
                label=f"Color for {[col for col in self._dframe.iloc[row_no] if col != 'COLOR']}",
                value=dict(hex=current_color_store[row_no]),
            )

        @app.callback(
            Output(
                {"id": self._uuid, "element": "table"},
                "style_data_conditional",
            ),
            Input({"id": self._uuid, "element": "store"}, "data"),
        )
        def _set_visual_color_in_table(current_color_store: List[str]) -> List:
            """Update the table color cell style"""
            style_data = [
                {
                    "if": {"row_index": idx, "column_id": "COLOR"},
                    "background-color": color,
                    "color": color,
                }
                for idx, color in enumerate(current_color_store)
            ]
            style_data.extend(
                [
                    {
                        "if": {"state": "active"},
                        "backgroundColor": "white",
                    },
                ]
            )
            return style_data

        @app.callback(
            Output({"id": self._uuid, "element": "store"}, "data"),
            Input(
                {"id": self._uuid, "element": "picker"},
                "value",
            ),
            State(
                {"id": self._uuid, "element": "table"},
                "active_cell",
            ),
            State({"id": self._uuid, "element": "store"}, "data"),
        )
        def _set_color(
            color: Optional[Dict],
            cell: Optional[Dict],
            current_color_store: List[str],
        ) -> List[str]:
            """Update list of stored colors"""
            if not cell or not color:
                raise PreventUpdate
            row_no = cell["row"]
            current_color = current_color_store[row_no]
            if current_color == color["hex"]:
                raise PreventUpdate
            current_color_store[row_no] = color["hex"]
            return current_color_store

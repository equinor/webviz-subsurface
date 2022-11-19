from typing import Callable

import pandas as pd
from dash import ALL, Input, Output, State, callback, callback_context, dcc
from dash.exceptions import PreventUpdate


def export_data_controllers(get_uuid: Callable) -> None:
    @callback(
        Output(get_uuid("download-dataframe"), "data"),
        Input({"request": "table_data", "table_id": ALL}, "data_requested"),
        State({"table_id": ALL}, "data"),
        State({"table_id": ALL}, "columns"),
        State({"request": "table_data", "table_id": ALL}, "id"),
        State({"table_id": ALL}, "id"),
        prevent_initial_call=True,
    )
    def _export_table_data(
        _data_requested: list,
        table_data: list,
        table_columns: list,
        button_ids: list,
        table_ids: list,
    ) -> Callable:

        ctx = callback_context.triggered[0]
        export_clicks = {
            id_value["table_id"]: n_clicks
            for id_value, n_clicks in zip(button_ids, _data_requested)
        }
        table_to_extract = [x for x in export_clicks.keys() if x in ctx["prop_id"]]
        if not table_to_extract or export_clicks[table_to_extract[0]] is None:
            raise PreventUpdate

        index = [x["table_id"] for x in table_ids].index(table_to_extract[0])
        table_data = table_data[index]
        table_columns = [x["name"] for x in table_columns[index]]

        return dcc.send_data_frame(
            pd.DataFrame(data=table_data, columns=table_columns).to_excel,
            "VolumetricAnalysis.xlsx",
            index=False,
        )

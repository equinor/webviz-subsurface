import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Union

import pandas as pd
from dash import Input, Output, callback
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from webviz_subsurface._components.tornado._tornado_data import TornadoData
from webviz_subsurface._components.tornado._tornado_table import TornadoTable

from ...shared_settings import FilterOption, Scale
from .view_elements import TornadoTable as TornadoTableViewElement

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated


class TornadoTableView(ViewABC):
    class IDs(StrEnum):
        TORNADO_TABLE = "tornado-table"
        MAIN_COLUMN = "main-column"

    @dataclass
    class Slots:
        reference: Annotated[Input, str]
        scale: Annotated[Input, str]
        filter_options: Annotated[Input, List[str]]
        data: Annotated[Input, Union[str, bytes, bytearray]]
        sens_filter: Annotated[Input, Union[List[str], str]]

    def __init__(self, design_matrix_df: pd.DataFrame, slots: Slots) -> None:
        super().__init__("Table View")

        self._design_matrix_df = design_matrix_df
        self._slots = slots

        column = self.add_column(TornadoTableView.IDs.MAIN_COLUMN)
        first_row = column.make_row()
        first_row.add_view_element(
            TornadoTableViewElement(), TornadoTableView.IDs.TORNADO_TABLE
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(TornadoTableView.IDs.TORNADO_TABLE)
                .component_unique_id(TornadoTableViewElement.IDs.TABLE)
                .to_string(),
                "data",
            ),
            Output(
                self.view_element(TornadoTableView.IDs.TORNADO_TABLE)
                .component_unique_id(TornadoTableViewElement.IDs.TABLE)
                .to_string(),
                "columns",
            ),
            self._slots.reference,
            self._slots.scale,
            self._slots.filter_options,
            self._slots.data,
            self._slots.sens_filter,
        )
        @callback_typecheck
        def _calc_tornado_table(
            reference: str,
            scale: Scale,
            filter_options: List[FilterOption],
            data: Union[str, bytes, bytearray],
            sens_filter: Union[List[str], str],
        ) -> Tuple[List[Any], List[Dict[Any, Any]]]:
            if not data:
                raise PreventUpdate
            filter_options = filter_options if filter_options else []
            data = json.loads(data)
            if not isinstance(sens_filter, List):
                sens_filter = [sens_filter]
            if not isinstance(data, dict):
                raise PreventUpdate
            values = pd.DataFrame(data["data"], columns=["REAL", "VALUE"])
            realizations = self._design_matrix_df.loc[
                self._design_matrix_df["ENSEMBLE"] == data["ENSEMBLE"]
            ]

            design_and_responses = pd.merge(values, realizations, on="REAL")
            if sens_filter is not None:
                if reference not in sens_filter:
                    sens_filter.append(reference)
                design_and_responses = design_and_responses.loc[
                    design_and_responses["SENSNAME"].isin(sens_filter)
                ]
            tornado_data = TornadoData(
                dframe=design_and_responses,
                response_name=data.get("response_name"),
                reference=reference,
                scale="Percentage" if scale == Scale.REL_VALUE_PERC else "Absolute",
                cutbyref=FilterOption.REMOVE_SENS_WITH_NO_IMPACT in filter_options,
            )
            tornado_table = TornadoTable(tornado_data=tornado_data)
            return (
                tornado_table.as_plotly_table,
                tornado_table.columns,
            )

from typing import Any, Dict, List, Union

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ._table_view_element import TableViewElement
from ..._utils import RftPlotterDataModel
from ._settings import QCSettings


class QCView(ViewABC):
    class Ids(StrEnum):
        QC_SETTINGS = "qc-settings"
        QC_TABLE = "qc-table"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("QC")
        self._datamodel = datamodel

        self.add_settings_group(
            QCSettings(
                ensembles=self._datamodel.ensembles,
            ),
            self.Ids.QC_SETTINGS,
        )

        map_column = self.add_column()
        map_column.add_view_element(TableViewElement(), self.Ids.QC_TABLE)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(self.Ids.QC_TABLE)
                .component_unique_id(TableViewElement.Ids.TABLE)
                .to_string(),
                "data",
            ),
            Output(
                self.view_element(self.Ids.QC_TABLE)
                .component_unique_id(TableViewElement.Ids.TABLE)
                .to_string(),
                "columns",
            ),
            Input(
                self.settings_group(self.Ids.QC_SETTINGS)
                .component_unique_id(QCSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_table(
            ensemble: str,
        ) -> tuple:
            columns = [
                {
                    "name": col,
                    "id": col,
                    #"type": "numeric",
                    "format": {"specifier": ".1f"},
                }
                for col in [
                    "REAL",
                    "EAST",
                    "NORTH",
                    "TVD",
                    "ZONE",
                    "WELL",
                    "DATE",
                    "valid_zone",
                    "ACTIVE",
                    "inactive_info",
                ]
            ]
            df = pd.concat(
                [self._datamodel.ertdatadf, self._datamodel.ertdatadf_inactive]
            )
            df = df[df["ENSEMBLE"] == ensemble]
            return (
                df.sort_values(by="REAL", ascending=True).to_dict("records"),
                columns,
            )

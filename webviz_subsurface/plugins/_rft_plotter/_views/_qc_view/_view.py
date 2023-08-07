from typing import Dict, List, Tuple

import pandas as pd
from dash import Input, Output, callback
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._utils import RftPlotterDataModel
from ._settings import QCSettings
from ._table_view_element import TableViewElement

DATA_TYPES = {
    "REAL": "numeric",
    "EAST": "numeric",
    "NORTH": "numeric",
    "MD": "numeric",
    "TVD": "numeric",
    "SIMULATED": "numeric",
    "SWAT": "numeric",
    "SGAS": "numeric",
    "SOIL": "numeric",
    "OBSERVED": "numeric",
    "OBSERVED_ERR": "numeric",
    "DIFF": "numeric",
    "ABSDIFF": "numeric",
    "YEAR": "numeric",
    "STDDEV": "numeric",
    "ZONE": "text",
    "WELL": "text",
    "VALID_ZONE": "text",
    "ACTIVE": "text",
    "DATE": "datetime",
    "INACTIVE_INFO": "text",
}
FORMATS = {
    "REAL": ".0f",
    "EAST": ".2f",
    "NORTH": ".2f",
    "MD": ".2f",
    "TVD": ".2f",
    "SIMULATED": ".2f",
    "SWAT": ".3f",
    "SGAS": ".3f",
    "SOIL": ".3f",
    "OBSERVED": ".2f",
    "OBSERVED_ERR": ".1f",
    "DIFF": ".2f",
    "ABSDIFF": ".2f",
    "YEAR": ".0f",
    "STDDEV": ".2f",
}


class QCView(ViewABC):
    class Ids(StrEnum):
        QC_SETTINGS = "qc-settings"
        QC_TABLE = "qc-table"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("QC Data")
        self._datamodel = datamodel

        self.add_settings_group(
            QCSettings(
                ensembles=self._datamodel.ensembles,
                columns=self._datamodel.ertdatadf.columns,
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
            Input(
                self.settings_group(self.Ids.QC_SETTINGS)
                .component_unique_id(QCSettings.Ids.COLUMNS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.QC_SETTINGS)
                .component_unique_id(QCSettings.Ids.ONLY_INACTIVE)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_table(
            ensemble: str, selected_columns: List[str], only_inactive: List[str]
        ) -> Tuple[List[Dict], List[Dict]]:
            columns = [
                {
                    "name": col,
                    "id": col,
                    "type": DATA_TYPES[col] if col in DATA_TYPES else None,
                    "format": {"specifier": FORMATS[col] if col in FORMATS else None},
                }
                for col in selected_columns
            ]
            if only_inactive:
                df = self._datamodel.ertdatadf_inactive
            else:
                df = pd.concat(
                    [self._datamodel.ertdatadf, self._datamodel.ertdatadf_inactive]
                )
            df = df[df["ENSEMBLE"] == ensemble]
            return (
                df.sort_values(by="REAL", ascending=True).to_dict("records"),
                columns,
            )

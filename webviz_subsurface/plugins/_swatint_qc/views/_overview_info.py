from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
from pyparsing import DebugExceptionAction, col
import webviz_core_components as wcc
from dash import (
    Input,
    Output,
    State,
    callback,
    callback_context,
    clientside_callback,
    dcc,
    html,
)
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._plugin_ids import PlugInIDs
from ..view_elements import OverViewTable, InfoBox, InfoDialog, Describtion


class OverviewTabLayout(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        TABLE = "table"
        INFO_BOX = "info-box"
        INFO_DIALOG = "info-dialog"
        DESCRIBTION = "describtion"
        MAIN_CLOUMN = "main-column"

    def __init__(self, datamodel: SwatinitQcDataModel) -> None:
        super().__init__()
        self.datamodel = datamodel

    @property
    def main_layout(self) -> html.Div:  # burde det være noen IDs her?
        return html.Div(
            children=[
                html.Div(
                    style={"height": "40vh", "overflow-y": "auto"},
                    children=[
                        wcc.FlexBox(
                            children=[
                                wcc.FlexColumn(
                                    [
                                        OverViewTable(self.datamodel),
                                    ],
                                    flex=7,
                                    style={"margin-right": "20px"},
                                ),
                                wcc.FlexColumn(InfoBox(self.datamodel), flex=3),
                            ],
                        ),
                    ],
                ),
                Describtion(),
            ]
        )

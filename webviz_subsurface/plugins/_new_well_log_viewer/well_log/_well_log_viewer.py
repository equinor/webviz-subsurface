import json
from pathlib import Path
from typing import Callable, Dict, List, Tuple, Union

import webviz_core_components as wcc
from dash import Dash, html
from webviz_subsurface_components import WellLogViewer as WellLogViewerComponent
from webviz_config.webviz_plugin_subclasses import (
    ViewABC,
    ViewElementABC,
    SettingsGroupABC,
)

from webviz_subsurface._models.well_set_model import WellSetModel
from webviz_subsurface._utils.webvizstore_functions import find_files, get_path

from dash import callback, Input, Output
import pandas as pd
import plotly.colors

from .._plugin_ids import PluginIds
from ..shared_settings._filter import Filter

from ._validate_log_templates import load_and_validate_log_templates
from .utils.default_color_tables import default_color_tables
from .utils.xtgeo_well_log_to_json import xtgeo_well_logs_to_json_format
from typing import Any, Callable, Dict, Tuple

from dash import Dash, Input, Output


class WellLogViewer(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        WELL_LOG_VIEWER = "well-log-viewer"

    def __init__(
        self,
        app: Dash,
        wellfolder: Path,
        logtemplates: List[Path],
        colortables: Path = None,
        wellsuffix: str = ".w",
        mdlog: str = None,
        well_tvdmin: Union[int, float] = None,
        well_tvdmax: Union[int, float] = None,
        well_downsample_interval: int = None,
        initial_settings: Dict = None,
    ) -> None:

        super().__init__()
        self._wellfolder = wellfolder
        self._wellsuffix = wellsuffix
        self._logtemplatefiles = logtemplates
        self._wellfiles: List = json.load(
            find_files(folder=self._wellfolder, suffix=self._wellsuffix)
        )
        self._log_templates = load_and_validate_log_templates(
            [get_path(fn) for fn in self._logtemplatefiles]
        )
        self._well_set_model = WellSetModel(
            self._wellfiles,
            mdlog=mdlog,
            tvdmin=well_tvdmin,
            tvdmax=well_tvdmax,
            downsample_interval=well_downsample_interval,
        )
        self.colortable_file = colortables
        if self.colortable_file:
            self.colortables = json.loads(get_path(self.colortable_file).read_text())
        else:
            self.colortables = default_color_tables()

        initial_settings = initial_settings if initial_settings else {}
        self.initial_well_name = initial_settings.get(
            "well_name", self._well_set_model.well_names[0]
        )
        self.initial_log_template = initial_settings.get(
            "logtemplate", list(self._log_templates.keys())[0]
        )

    @property
    def layout(self) -> html.Div:
        return wcc.FlexBox(
            [
                wcc.Frame(
                    style={"height": "90vh", "flex": 1},
                    children=[
                        wcc.Dropdown(
                            label="Well",
                            id=self.uuid("well"),
                            options=[
                                {"label": name, "value": name}
                                for name in self._well_set_model.well_names
                            ],
                            value=self.initial_well_name,
                            clearable=False,
                        ),
                        wcc.Dropdown(
                            label="Log template",
                            id=self.uuid("template"),
                            options=[
                                {"label": name, "value": name}
                                for name in list(self._log_templates.keys())
                            ],
                            value=self.initial_log_template,
                            clearable=False,
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 6, "height": "90vh"},
                    children=[
                        WellLogViewerComponent(
                            id=self.uuid("well-log-viewer"),
                            template=self._log_templates.get(self.initial_log_template),
                            welllog=xtgeo_well_logs_to_json_format(
                                well=self._well_set_model.get_well(
                                    self.initial_well_name
                                )
                            ),
                            colorTables=self.colortables,
                        )
                    ],
                ),
            ]
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.WELL), "data"),
            Output(self.get_store_unique_id(PluginIds.Stores.LOG_TEMPLATE), "data"),
            Input(self.get_store_unique_id(Filter.Ids.WELL_SELECT), "data"),
            Input(self.get_store_unique_id(Filter.Ids.LOG_SELECT), "data"),
        )
        def _update_log_data(well_name: str, template: str) -> Tuple[Any, Any]:
            well = WellSetModel.get_well(well_name)
            return xtgeo_well_logs_to_json_format(well), Dict.get(template)

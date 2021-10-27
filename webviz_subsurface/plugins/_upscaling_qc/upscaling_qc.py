from pathlib import Path

from dash import html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_core_components import FlexBox, Frame
from .models import UpscalingQCModel
from .layout import sidebar, main
from .callbacks.update_plot import update_plot

class UpscalingQC(WebvizPluginABC):
    def __init__(self, webviz_settings: WebvizSettings, model_folder: Path):
        super().__init__()
        self.qc_model = UpscalingQCModel(model_folder=model_folder)
        self.set_callbacks()
    @property
    def layout(self) -> FlexBox:
        return FlexBox(
            [
                Frame(
                    style={"height": "90vh", "flex": 1},
                    children=sidebar(get_uuid=self.uuid, qc_model=self.qc_model),
                ),
                Frame(style={"flex": 5}, children=main(get_uuid=self.uuid)),
            ]
        )
    def set_callbacks(self):
        update_plot(get_uuid=self.uuid, qc_model=self.qc_model)
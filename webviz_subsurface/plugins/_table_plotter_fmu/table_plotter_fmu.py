from typing import Dict
from pathlib import Path

import dash
import dash_html_components as html
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings

from webviz_subsurface._models import table_model_factory, ObservationModel
from .views import main_view
from .controllers import main_controller


class TablePlotterFMU(WebvizPluginABC):
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        csvfile: str = None,
        ensembles: list = None,
        aggregated_csvfile: Path = None,
        observation_file: Path = None,
    ):
        super().__init__()
        if ensembles is not None and csvfile is not None:
            ensembles_dict: Dict[str, Path] = {
                ens_name: webviz_settings.shared_settings["scratch_ensembles"][ens_name]
                for ens_name in ensembles
            }
            self._tablemodel = (
                table_model_factory.create_model_set_from_ensembles_layout(
                    ensembles_dict, csvfile
                )
            )
        elif aggregated_csvfile is not None:
            self._tablemodel = (
                table_model_factory.create_model_set_from_aggregated_csv_file(
                    aggregated_csvfile
                )
            )
        else:
            raise ValueError(
                "Specify either ensemble and csvfile or aggregated_csvfile"
            )
        self.observationmodel = (
            ObservationModel(observation_file) if observation_file is not None else None
        )
        self.set_callbacks(app)

    @property
    def layout(self) -> html.Div:
        return main_view(get_uuid=self.uuid, tablemodel=self._tablemodel)

    def set_callbacks(self, app: dash.Dash) -> None:
        return main_controller(app, get_uuid=self.uuid, tablemodel=self._tablemodel)

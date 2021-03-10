from typing import Dict
from pathlib import Path

import dash
import dash_html_components as html

from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_store import WEBVIZ_STORAGE
from webviz_subsurface._models import ObservationModel
from webviz_subsurface._models.table_model_factory import EnsembleTableModelFactory
from webviz_subsurface._models.table_model_factory import (
    EnsembleTableModelFactorySimpleInMemory,
)

import webviz_subsurface
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

        # For now, use the storage folder from WEBVIZ_STORAGE
        # AND also deduce if we're running a portable version of the app
        is_running_portable = WEBVIZ_STORAGE.use_storage
        model_factory = EnsembleTableModelFactory(
            root_storage_folder=WEBVIZ_STORAGE.storage_folder,
            allow_storage_writes=not is_running_portable,
        )
        model_factory = EnsembleTableModelFactorySimpleInMemory()

        if ensembles is not None and csvfile is not None:
            ensembles_dict: Dict[str, str] = {
                ens_name: webviz_settings.shared_settings["scratch_ensembles"][ens_name]
                for ens_name in ensembles
            }
            self._tablemodelset = (
                model_factory.create_model_set_from_per_realization_csv_file(
                    ensembles_dict, csvfile
                )
            )
        elif aggregated_csvfile is not None:
            self._tablemodelset = (
                model_factory.create_model_set_from_aggregated_csv_file(
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
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "plugins"
            / "_table_plotter_fmu"
            / "assets"
            / "update_axis.js"
        )
        self.set_callbacks(app)

    @property
    def layout(self) -> html.Div:
        return main_view(get_uuid=self.uuid, tablemodel=self._tablemodelset)

    def set_callbacks(self, app: dash.Dash) -> None:
        return main_controller(app, get_uuid=self.uuid, tablemodel=self._tablemodelset)

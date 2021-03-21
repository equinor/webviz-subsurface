from typing import Dict, List, Tuple, Callable
from pathlib import Path

import dash
import dash_html_components as html

from webviz_config.webviz_store import webvizstore
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


class LinePlotterFMU(WebvizPluginABC):
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        csvfile: str = None,
        ensembles: list = None,
        aggregated_csvfile: Path = None,
        aggregated_parameterfile: Path = None,
        observation_file: Path = None,
        initial_data: Dict = None,
        initial_layout: Dict = None,
    ):
        super().__init__()

        # For now, use the storage folder from WEBVIZ_STORAGE
        # AND also deduce if we're running a portable version of the app
        is_running_portable = WEBVIZ_STORAGE.use_storage
        model_factory = EnsembleTableModelFactory(
            root_storage_folder=WEBVIZ_STORAGE.storage_folder,
            allow_storage_writes=not is_running_portable,
        )
        # model_factory = EnsembleTableModelFactorySimpleInMemory()
        self._initial_data = initial_data if initial_data else {}
        self._initial_layout = initial_layout if initial_layout else {}
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
        if aggregated_parameterfile is not None:
            self._parametermodelset = (
                model_factory.create_model_set_from_aggregated_csv_file(
                    aggregated_parameterfile
                )
            )
            self._ensemble_names = list(
                set().union(
                    *[
                        ens
                        for ens in [
                            self._tablemodelset.ensemble_names(),
                            self._parametermodelset.ensemble_names(),
                        ]
                    ]
                )
            )
            self._parameter_names = list(
                set().union(
                    *[
                        self._parametermodelset.ensemble(ens).column_names()
                        for ens in self._ensemble_names
                    ]
                )
            )
            self._data_column_names = list(
                set().union(
                    *[
                        self._tablemodelset.ensemble(ens).column_names()
                        for ens in self._ensemble_names
                    ]
                )
            )
        self._observationfile = get_path(observation_file)
        self._observationmodel = ObservationModel(self._observationfile)
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "js"
            / "update_plotly_figure.js"
        )
        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [(get_path, [{"path": self._observationfile}])]

    @property
    def layout(self) -> html.Div:
        return main_view(
            get_uuid=self.uuid,
            ensemble_names=self._ensemble_names,
            data_column_names=self._data_column_names,
            parameter_names=self._parameter_names,
            initial_data=self._initial_data,
            initial_layout=self._initial_layout,
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        return main_controller(
            app,
            get_uuid=self.uuid,
            tablemodel=self._tablemodelset,
            observationmodel=self._observationmodel,
            parametermodel=self._parametermodelset,
        )


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)
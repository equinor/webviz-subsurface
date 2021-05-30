from typing import List, Tuple, Callable, Optional
from pathlib import Path
import pandas as pd
import dash
import dash_html_components as html
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

import webviz_subsurface

from webviz_subsurface._models import EnsembleSetModel, InplaceVolumesModel
from webviz_subsurface._models import caching_ensemble_set_model_factory
from webviz_subsurface._models.inplace_volumes_model import extract_volumes

from .views import clientside_stores, main_view
from .controllers import (
    distribution_controllers,
    selections_controllers,
    layout_controllers,
)


class VolumetricAnalysis(WebvizPluginABC):
    """Dashboard to analyze volumetrics results from FMU runs."""

    # pylint: disable=too-many-arguments, too-many-instance-attributes, too-many-locals
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        csvfile_vol: Path = None,
        csvfile_parameters: Path = None,
        ensembles: list = None,
        volfiles: dict = None,
        volfolder: str = "share/results/volumes",
        drop_constants: bool = True,
    ):

        super().__init__()

        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "container.css"
        )
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "css"
            / "inplace_volumes.css"
        )
        self.csvfile_vol = csvfile_vol
        self.csvfile_parameters = csvfile_parameters
        self.volfiles = volfiles
        self.volfolder = volfolder

        if csvfile_vol and ensembles:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )
        if csvfile_vol:
            volume_table = read_csv(csvfile_vol)
            parameters: Optional[pd.DataFrame] = (
                read_csv(csvfile_parameters) if csvfile_parameters else None
            )

        elif ensembles and volfiles:
            ensemble_paths = {
                ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                for ens in ensembles
            }
            self.emodel: EnsembleSetModel = (
                caching_ensemble_set_model_factory.get_or_create_model(
                    ensemble_paths=ensemble_paths,
                )
            )
            parameters = self.emodel.load_parameters()

            volume_table = extract_volumes(self.emodel, volfolder, volfiles)

        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles" and "volfiles"'
            )

        self.volmodel = InplaceVolumesModel(volume_table, parameters, drop_constants)
        self.theme = webviz_settings.theme
        self.set_callbacks(app)

    #    @property
    #    def tour_steps(self) -> List[Dict]:
    #        return generate_tour_steps(get_uuid=self.uuid)

    @property
    def layout(self) -> html.Div:
        return html.Div(
            id=self.uuid("layout"),
            children=[
                clientside_stores(get_uuid=self.uuid),
                main_view(
                    get_uuid=self.uuid,
                    volumemodel=self.volmodel,
                    theme=self.theme,
                ),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        selections_controllers(app=app, get_uuid=self.uuid, volumemodel=self.volmodel)
        distribution_controllers(app=app, get_uuid=self.uuid, volumemodel=self.volmodel)
        layout_controllers(app=app, get_uuid=self.uuid)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        if self.csvfile_vol is not None:
            store_functions = [(read_csv, [{"csv_file": self.csvfile_vol}])]
            if self.csvfile_parameters is not None:
                store_functions.append(
                    (read_csv, [{"csv_file": self.csvfile_parameters}])
                )
        else:
            function_args: dict = {
                "ensemble_set_model": self.emodel,
                "volfolder": self.volfolder,
                "volfiles": self.volfiles,
            }
            store_functions = [(extract_volumes, [function_args])]
            store_functions.extend(self.emodel.webvizstore)
        return store_functions


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_csv(csv_file: Path) -> pd.DataFrame:
    return pd.read_csv(csv_file)

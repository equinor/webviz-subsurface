from pathlib import Path
from typing import Callable, Dict, List, Tuple

import pandas as pd
import webviz_core_components as wcc
from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_config.webviz_store import webvizstore

import webviz_subsurface
from webviz_subsurface._components.parameter_filter import ParameterFilter
from webviz_subsurface._models import ObservationModel
from webviz_subsurface._providers import EnsembleTableProviderFactory
from webviz_subsurface._utils.unique_theming import unique_colors

from .controllers import build_figure, update_figure_clientside
from .views import main_view


class LinePlotterFMU(WebvizPluginABC):
    """General line plotter for FMU data

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`csvfile`:** Relative path to Csv file stored per realization
     * **`observation_file`:** Yaml file with observations
    * **`observation_group`:** Top-level key in observation file.
    * **`remap_observation_keys`:** Remap observation keys to columns in csv file
    * **`remap_observation_values`:** Remap observation values to columns in csv file
    * **`colors`:** Set colors for each ensemble
    * **`initial_data`:** Initialize data selectors (x,y,ensemble, parameter)
    * **`initial_layout`:** Initialize plot layout (x and y axis direction and type)"""

    # pylint: disable=too-many-locals, too-many-arguments
    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        csvfile: str = None,
        ensembles: list = None,
        aggregated_csvfile: Path = None,
        aggregated_parameterfile: Path = None,
        observation_file: Path = None,
        observation_group: str = "general",
        remap_observation_keys: Dict[str, str] = None,
        remap_observation_values: Dict[str, str] = None,
        colors: Dict = None,
        initial_data: Dict = None,
        initial_layout: Dict = None,
    ):
        super().__init__()

        provider = EnsembleTableProviderFactory.instance()
        self._initial_data = initial_data if initial_data else {}
        self._initial_layout = initial_layout if initial_layout else {}
        if ensembles is not None and csvfile is not None:
            ensembles_dict: Dict[str, str] = {
                ens_name: webviz_settings.shared_settings["scratch_ensembles"][ens_name]
                for ens_name in ensembles
            }
            self._parameterproviderset = (
                provider.create_provider_set_from_per_realization_parameter_file(
                    ensembles_dict
                )
            )
            self._tableproviderset = (
                provider.create_provider_set_from_per_realization_csv_file(
                    ensembles_dict, csvfile
                )
            )
            self._ensemble_names = ensembles
        elif aggregated_csvfile and aggregated_parameterfile is not None:
            self._tableproviderset = (
                provider.create_provider_set_from_aggregated_csv_file(
                    aggregated_csvfile
                )
            )
            self._parameterproviderset = (
                provider.create_provider_set_from_aggregated_csv_file(
                    aggregated_parameterfile
                )
            )
            self._ensemble_names = self._tableproviderset.ensemble_names()
        else:
            raise ValueError(
                "Specify either ensembles and csvfile or aggregated_csvfile "
                "and aggregated_parameterfile"
            )
        all_parameters: list = [
            self._parameterproviderset.ensemble_provider(ens).column_names()
            for ens in self._ensemble_names
        ]
        self._parameter_names: list = list(set().union(*all_parameters))
        all_data_columns: list = [
            self._tableproviderset.ensemble_provider(ens).column_names()
            for ens in self._ensemble_names
        ]
        self._data_column_names: list = list(set().union(*all_data_columns))
        dfs = []
        for ens in self._ensemble_names:
            df = self._parameterproviderset.ensemble_provider(ens).get_column_data(
                column_names=self._parameterproviderset.ensemble_provider(
                    ens
                ).column_names()
            )
            df["ENSEMBLE"] = ens
            dfs.append(df)
        parameterdf = pd.concat(dfs)
        self._realizations = sorted(list(parameterdf["REAL"].unique()))
        self._parameter_filter = ParameterFilter(
            self.uuid("parameter-filter"), parameterdf
        )
        self._observationfile = observation_file
        self._observationmodel = (
            ObservationModel(
                get_path(self._observationfile),
                observation_group,
                remap_observation_keys,
                remap_observation_values,
            )
            if self._observationfile
            else None
        )
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent
            / "_assets"
            / "js"
            / "clientside_functions.js"
        )

        self._colors: Dict = unique_colors(self._ensemble_names, webviz_settings.theme)
        if colors is not None:
            self._colors.update(colors)

        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return (
            [(get_path, [{"path": self._observationfile}])]
            if self._observationfile is not None
            else []
        )

    @property
    def layout(self) -> html.Div:
        return wcc.FlexBox(
            children=[
                html.Div(
                    style={"flex": 5},
                    children=main_view(
                        get_uuid=self.uuid,
                        ensemble_names=self._ensemble_names,
                        data_column_names=self._data_column_names,
                        parameter_names=self._parameter_names,
                        realizations=self._realizations,
                        initial_data=self._initial_data,
                        initial_layout=self._initial_layout,
                    ),
                ),
                wcc.Frame(
                    style={"flex": 1, "height": "90vh"},
                    children=self._parameter_filter.layout,
                ),
            ]
        )

    def set_callbacks(self, app: Dash) -> None:
        build_figure(
            app,
            get_uuid=self.uuid,
            tableproviders=self._tableproviderset,
            observationmodel=self._observationmodel,
            parameterproviders=self._parameterproviderset,
            colors=self._colors,
        )
        update_figure_clientside(app, get_uuid=self.uuid)


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)

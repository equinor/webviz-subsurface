from typing import Dict, List, Tuple, Callable
from pathlib import Path

import pandas as pd
import dash
import dash_html_components as html

from webviz_config.webviz_store import webvizstore
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
from webviz_config.webviz_assets import WEBVIZ_ASSETS
from webviz_subsurface._models import ObservationModel
from webviz_subsurface._providers import EnsembleTableProviderFactory
import webviz_core_components as wcc
from webviz_subsurface._components.parameter_filter import ParameterFilter
import webviz_subsurface
from .views import main_view
from .controllers import build_figure, update_figure_clientside, set_single_real_mode


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
        observation_group: str = "general",
        remap_observation_keys: Dict[str, str] = None,
        remap_observation_values: Dict[str, str] = None,
        initial_data: Dict = None,
        initial_layout: Dict = None,
    ):
        super().__init__()

        provider_factory = EnsembleTableProviderFactory.instance()

        self._initial_data = initial_data if initial_data else {}
        self._initial_layout = initial_layout if initial_layout else {}
        if ensembles is not None and csvfile is not None:
            ensembles_dict: Dict[str, str] = {
                ens_name: webviz_settings.shared_settings["scratch_ensembles"][ens_name]
                for ens_name in ensembles
            }
            self._parameterproviderset = provider_factory.create_provider_set_from_per_realization_parameter_file(
                ensembles_dict
            )
            self._tableproviderset = (
                provider_factory.create_provider_set_from_per_realization_csv_file(
                    ensembles_dict, csvfile
                )
            )
        elif aggregated_csvfile and aggregated_parameterfile is not None:
            self._tableproviderset = (
                provider_factory.create_provider_set_from_aggregated_csv_file(
                    aggregated_csvfile
                )
            )
            self._parameterproviderset = (
                provider_factory.create_provider_set_from_aggregated_csv_file(
                    aggregated_parameterfile
                )
            )
        else:
            raise ValueError(
                "Specify either ensemble and csvfile or aggregated_csvfile and aggregated_parameterfile"
            )

        self._ensemble_names = list(
            set().union(
                *[
                    ens
                    for ens in [
                        self._tableproviderset.ensemble_names(),
                        self._parameterproviderset.ensemble_names(),
                    ]
                ]
            )
        )
        self._parameter_names = list(
            set().union(
                *[
                    self._parameterproviderset.ensemble_provider(ens).column_names()
                    for ens in self._ensemble_names
                ]
            )
        )
        self._data_column_names = list(
            set().union(
                *[
                    self._tableproviderset.ensemble_provider(ens).column_names()
                    for ens in self._ensemble_names
                ]
            )
        )
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
        self._parameter_filter = ParameterFilter(
            app, self.uuid("parameter-filter"), parameterdf
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
            / "update_plotly_figure.js"
        )
        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        return [(get_path, [{"path": self._observationfile}])] if self._observationfile is not None else []

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
                        initial_data=self._initial_data,
                        initial_layout=self._initial_layout,
                    ),
                ),
                html.Div(
                    className="framed",
                    style={"flex": 2, "height": "89vh"},
                    children=self._parameter_filter.layout,
                ),
            ]
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        build_figure(
            app,
            get_uuid=self.uuid,
            tableproviders=self._tableproviderset,
            observationmodel=self._observationmodel,
            parameterproviders=self._parameterproviderset,
        )
        update_figure_clientside(app, get_uuid=self.uuid)
        set_single_real_mode(
            app,
            get_uuid=self.uuid,
        )


@webvizstore
def get_path(path: Path) -> Path:
    return Path(path)

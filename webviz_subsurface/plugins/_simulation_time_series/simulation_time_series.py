from typing import List, Optional, Dict
from pathlib import Path

import dash
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
import webviz_core_components as wcc

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector


from .main_view import main_view
from .types import VisualizationOptions
from .models.ensemble_set_model import EnsembleSetModel

from .controller import controller_callbacks
from ..._abbreviations.reservoir_simulation import simulation_vector_description
from ..._utils.vector_selector import add_vector_to_vector_selector_data
from ..._utils.simulation_timeseries import set_simulation_line_shape_fallback


class SimulationTimeSeries(WebvizPluginABC):
    # pylint: disable=too-many-locals
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: Optional[list] = None,
        csvfile_path: Optional[Path] = None,
        options: dict = None,
        sampling: str = "monthly",
        line_shape_fallback: str = "linear",
    ) -> None:
        super().__init__()

        self._webviz_settings = webviz_settings
        self._csvfile_path = csvfile_path
        self._sampling = sampling

        self._line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )

        self._ensemble_set_model: EnsembleSetModel = None
        if ensembles is not None:
            ensemble_paths: Dict[str, Path] = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }

            self._ensemble_set_model = EnsembleSetModel(ensemble_paths, sampling)
        elif self._csvfile_path is not None:
            raise NotImplementedError()
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )

        self._theme = webviz_settings.theme

        # NOTE: Initially keep set of all vector names - can make dynamic if wanted?
        vector_names = self._ensemble_set_model.vector_names()
        non_historical_vector_names = [
            vector
            for vector in vector_names
            if historical_vector(vector, None, False) not in vector_names
        ]

        # NOTE: Initially: With set of vector names, the vector selector data is static
        # If made dynamic, the vector selector data must be dynamic
        self._vector_selector_data: list = []
        for vector in non_historical_vector_names:
            split = vector.split(":")
            add_vector_to_vector_selector_data(
                self._vector_selector_data,
                vector,
                simulation_vector_description(split[0]),
            )
            # TODO: Add avgrate_vec and interval_vec

        plot_options = options if options else {}
        self._visualization_type = VisualizationOptions(
            plot_options.get("visualization", "statistics")
        )
        self._initial_vectors: List[str] = []
        if "vectors" not in plot_options:
            self._initial_vectors = []
        for vector in [
            vector
            for vector in ["vector1", "vector2", "vector3"]
            if vector in plot_options
        ]:
            self._initial_vectors.append(plot_options[vector])
        self._initial_vectors = self._initial_vectors[:3]

        # Set callbacks
        self.set_callbacks(app)

    @property
    def layout(self) -> wcc.FlexBox:
        return main_view(
            get_uuid=self.uuid,
            ensemble_names=self._ensemble_set_model.ensemble_names(),
            vector_selector_data=self._vector_selector_data,
            initial_visualization_type=self._visualization_type,
            selected_vectors=self._initial_vectors,
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        controller_callbacks(
            app=app,
            get_uuid=self.uuid,
            ensemble_set_model=self._ensemble_set_model,
            theme=self._theme,
            sampling=self._sampling,
            initial_selected_vectors=self._initial_vectors,
            line_shape_fallback=self._line_shape_fallback,
        )

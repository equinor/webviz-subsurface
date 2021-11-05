from typing import List, Optional, Dict
from pathlib import Path

import dash
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
import webviz_core_components as wcc

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._providers import Frequency

from .main_view import main_view
from .types import VisualizationOptions
from .provider_set import create_provider_set_from_paths

from .controller import controller_callbacks
from ..._abbreviations.reservoir_simulation import simulation_vector_description
from ..._datainput.from_timeseries_cumulatives import rename_vec_from_cum
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

        self._resampling_frequency = Frequency.from_string_value(sampling)
        if ensembles is not None:
            ensemble_paths: Dict[str, Path] = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }

            self._input_provider_set = create_provider_set_from_paths(ensemble_paths)
        elif self._csvfile_path is not None:
            raise NotImplementedError()
        else:
            raise ValueError(
                'Incorrect arguments. Either provide a "csvfile" or "ensembles"'
            )

        if not self._input_provider_set:
            raise ValueError(
                "Initial provider set is undefined, and ensemble summary providers"
                " are not instanciated for plugin"
            )

        self._theme = webviz_settings.theme

        # NOTE: Initially keep set of all vector names - can make dynamic if wanted?
        vector_names = self._input_provider_set.all_vector_names()
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

            metadata = (
                self._input_provider_set.vector_metadata(vector)
                if self._input_provider_set
                else None
            )
            if metadata and metadata.get("is_total"):
                # Get the likely name for equivalent rate vector and make dropdown options.
                # Requires that the time_index was either defined or possible to infer.
                avgrate_vec = rename_vec_from_cum(vector=vector, as_rate=True)
                interval_vec = rename_vec_from_cum(vector=vector, as_rate=False)

                avgrate_split = avgrate_vec.split(":")
                interval_split = interval_vec.split(":")

                add_vector_to_vector_selector_data(
                    self._vector_selector_data,
                    avgrate_vec,
                    f"{simulation_vector_description(avgrate_split[0])} ({avgrate_vec})",
                )
                add_vector_to_vector_selector_data(
                    self._vector_selector_data,
                    interval_vec,
                    f"{simulation_vector_description(interval_split[0])} ({interval_vec})",
                )

        plot_options = options if options else {}
        self._initial_visualization_selection = VisualizationOptions(
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
            ensemble_names=self._input_provider_set.names(),
            vector_selector_data=self._vector_selector_data,
            selected_visualization=self._initial_visualization_selection,
            selected_vectors=self._initial_vectors,
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        controller_callbacks(
            app=app,
            get_uuid=self.uuid,
            input_provider_set=self._input_provider_set,
            theme=self._theme,
            sampling=self._sampling,
            initial_selected_vectors=self._initial_vectors,
            resampling_frequency=self._resampling_frequency,
            line_shape_fallback=self._line_shape_fallback,
        )

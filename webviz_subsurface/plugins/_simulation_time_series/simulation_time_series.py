from typing import Callable, Dict, List, Optional, Tuple
from pathlib import Path

import dash
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
import webviz_core_components as wcc

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._utils.webvizstore_functions import get_path
from webviz_subsurface._providers import Frequency

from .main_view import main_view
from .types import VisualizationOptions
from .provider_set import (
    create_lazy_provider_set_from_paths,
    create_presampled_provider_set_from_paths,
)
from .utils.from_timeseries_cumulatives import rename_vector_from_cumulative

from ..._providers import Frequency

from .controller import controller_callbacks
from ..._abbreviations.reservoir_simulation import simulation_vector_description
from ..._utils.vector_selector import add_vector_to_vector_selector_data
from ..._utils.simulation_timeseries import (
    set_simulation_line_shape_fallback,
    check_and_format_observations,
)


class SimulationTimeSeries(WebvizPluginABC):
    # pylint: disable=too-many-locals,too-many-arguments
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: Optional[list] = None,
        csvfile_path: Optional[Path] = None,
        perform_presampling: bool = False,
        obsfile: Path = None,
        options: dict = None,
        sampling: str = Frequency.MONTHLY.value,  # TODO: Rename to initial sampling?
        line_shape_fallback: str = "linear",
    ) -> None:
        super().__init__()

        self._webviz_settings = webviz_settings
        self._csvfile_path = csvfile_path
        self._obsfile = obsfile

        self._line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )

        # Must defined valid freqency
        self._sampling = Frequency(sampling)
        self._presampled_frequency = None
        # TODO: Update functionality when allowing raw data and csv file input
        # Add config param "presampled" and create providers from factory with
        # presampled/lazy accordingly
        if ensembles is not None:
            ensemble_paths: Dict[str, Path] = {
                ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble_name
                ]
                for ensemble_name in ensembles
            }
            if perform_presampling:
                self._presampled_frequency = self._sampling
                self._input_provider_set = create_presampled_provider_set_from_paths(
                    ensemble_paths, self._presampled_frequency
                )
            else:
                self._input_provider_set = create_lazy_provider_set_from_paths(
                    ensemble_paths
                )
            self._input_provider_set.verify_consistent_vector_metadata()
        elif self._csvfile_path is not None:
            # NOTE: If csv is implemented-> handle/disable statistics, INTVL_, AVG_, delta
            # ensemble, etc.
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

        self._observations = {}
        if self._obsfile:
            self._observations = check_and_format_observations(get_path(self._obsfile))

        # NOTE: Initially keep set of all vector names - can make dynamic if wanted?
        vector_names = self._input_provider_set.all_vector_names()
        non_historical_vector_names = [
            vector
            for vector in vector_names
            if historical_vector(vector, None, False) not in vector_names
        ]

        # NOTE: Initially: With set of vector names, the vector selector data is static
        # Can be made dynamic based on selected ensembles - i.e. vectors present among
        # selected providers?
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
            if metadata and metadata.is_total:
                # Get the likely name for equivalent rate vector and make dropdown options.
                # Requires that the time_index was either defined or possible to infer.
                avgrate_vec = rename_vector_from_cumulative(vector=vector, as_rate=True)
                interval_vec = rename_vector_from_cumulative(
                    vector=vector, as_rate=False
                )

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
            disable_resampling_dropdown=self._presampled_frequency is not None,
            selected_resampling_frequency=self._sampling,
            selected_visualization=self._initial_visualization_selection,
            selected_vectors=self._initial_vectors,
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        controller_callbacks(
            app=app,
            get_uuid=self.uuid,
            input_provider_set=self._input_provider_set,
            theme=self._theme,
            initial_selected_vectors=self._initial_vectors,
            observations=self._observations,
            line_shape_fallback=self._line_shape_fallback,
        )

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        functions: List[Tuple[Callable, list]] = []
        if self._obsfile:
            functions.append((get_path, [{"path": self._obsfile}]))
        return functions
from typing import List, Optional, Dict
from pathlib import Path

import dash
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
import webviz_core_components as wcc

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._providers import (
    EnsembleSummaryProviderFactory,
    EnsembleSummaryProvider,
    Frequency,
)

from .main_view import main_view
from .types import VisualizationOptions

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

        self._resampling_freq: Optional[Frequency] = None
        self._provider_set: Dict[str, EnsembleSummaryProvider] = {}

        if ensembles is not None:
            provider_factory = EnsembleSummaryProviderFactory.instance()

            self._resampling_freq = Frequency.from_string_value(sampling)
            for ens_name in ensembles:
                ens_path = webviz_settings.shared_settings["scratch_ensembles"][
                    ens_name
                ]
                self._provider_set[
                    ens_name
                ] = provider_factory.create_from_arrow_unsmry_lazy(str(ens_path))
        elif self._csvfile_path is not None:
            raise NotImplementedError()
        else:
            raise ValueError(
                'Incorrent arguments. Either provide a "csvfile" or "ensembles"'
            )

        self._theme = webviz_settings.theme
        self._ensemble_names = list(self._provider_set.keys())

        # NOTE: Initially keep set of all vector names - can make dynamic if wanted?
        vector_names: List[str] = []
        for provider in self._provider_set.values():
            vector_names.extend(provider.vector_names())
        vector_names = list(sorted(set(vector_names)))  # Remove duplicates
        self._vector_names = [
            vec
            for vec in vector_names
            if historical_vector(vec, None, False) not in vector_names
        ]

        # NOTE: Initially: With set of vector names, the vector selector data is static
        # If made dynamic, the vector selector data must be dynamic
        self._vector_selector_data: list = []
        for vector in self._vector_names:
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
            ensemble_names=self._ensemble_names,
            vector_selector_data=self._vector_selector_data,
            visualization_type=self._visualization_type,
            selected_vectors=self._initial_vectors,
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        controller_callbacks(
            app=app,
            get_uuid=self.uuid,
            provider_set=self._provider_set,
            theme=self._theme,
            sampling=self._sampling,
            resampling_frequency=self._resampling_freq,
            selected_vectors=self._initial_vectors,
            line_shape_fallback=self._line_shape_fallback,
        )

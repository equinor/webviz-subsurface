import copy
import warnings
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import dash
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.deprecation_decorators import deprecated_plugin_arguments
from webviz_config.webviz_assets import WEBVIZ_ASSETS

import webviz_subsurface
from webviz_subsurface._abbreviations.reservoir_simulation import (
    historical_vector,
    simulation_vector_description,
)
from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.simulation_timeseries import (
    check_and_format_observations,
    set_simulation_line_shape_fallback,
)
from webviz_subsurface._utils.user_defined_vector_definitions import (
    create_user_defined_vector_descriptions_from_config,
)
from webviz_subsurface._utils.vector_calculator import (
    add_expressions_to_vector_selector_data,
    expressions_from_config,
    get_vector_definitions_from_expressions,
    validate_predefined_expression,
)
from webviz_subsurface._utils.vector_selector import (
    add_vector_to_vector_selector_data,
    is_vector_name_in_vector_selector_data,
)
from webviz_subsurface._utils.webvizstore_functions import get_path

from ._callbacks import plugin_callbacks
from ._layout import LayoutElements, main_layout
from .types import VisualizationOptions
from .types.provider_set import (
    create_lazy_provider_set_from_paths,
    create_presampled_provider_set_from_paths,
)
from .utils.from_timeseries_cumulatives import (
    create_per_day_vector_name,
    create_per_interval_vector_name,
)


def check_deprecation_argument(options: Optional[dict]) -> Optional[Tuple[str, str]]:
    if options is None:
        return None
    if any(elm in options for elm in ["vector1", "vector2", "vector3"]):
        return (
            'The usage of "vector1", "vector2" and "vector3" as user input options are deprecated. '
            'Please replace options with list named "vectors"',
            'The usage of "vector1", "vector2" and "vector3" as user input in options for '
            "initially selected vectors are deprecated. Please replace user input options with "
            'list named "vectors", where each element represent the corresponding initially '
            "selected vector.",
        )
    return None


# pylint: disable=too-many-instance-attributes
class SimulationTimeSeries(WebvizPluginABC):
    # pylint: disable=too-many-arguments,too-many-branches,too-many-locals,too-many-statements
    @deprecated_plugin_arguments(check_deprecation_argument)
    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: Optional[list] = None,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        perform_presampling: bool = False,
        obsfile: Path = None,
        options: dict = None,
        sampling: str = Frequency.MONTHLY.value,
        predefined_expressions: str = None,
        user_defined_vector_definitions: str = None,
        line_shape_fallback: str = "linear",
    ) -> None:
        super().__init__()

        # NOTE: Temporary css, pending on new wcc modal component.
        # See: https://github.com/equinor/webviz-core-components/issues/163
        WEBVIZ_ASSETS.add(
            Path(webviz_subsurface.__file__).parent / "_assets" / "css" / "modal.css"
        )

        self._webviz_settings = webviz_settings
        self._obsfile = obsfile

        # Retrieve user defined vector descriptions from configuration and validate
        self._user_defined_vector_descriptions_path = (
            None
            if user_defined_vector_definitions is None
            else webviz_settings.shared_settings["user_defined_vector_definitions"][
                user_defined_vector_definitions
            ]
        )
        self._user_defined_vector_definitions: Dict[
            str, wsc.VectorDefinition
        ] = create_user_defined_vector_descriptions_from_config(
            get_path(self._user_defined_vector_descriptions_path)
            if self._user_defined_vector_descriptions_path
            else None
        )
        self._custom_vector_definitions = copy.deepcopy(
            self._user_defined_vector_definitions
        )

        self._line_shape_fallback = set_simulation_line_shape_fallback(
            line_shape_fallback
        )

        # Must define valid freqency!
        if Frequency.from_string_value(sampling) is None:
            raise ValueError(
                'Sampling frequency conversion is "None", i.e. Raw sampling, and '
                "is not supported by plugin yet!"
            )
        self._sampling = Frequency(sampling)
        self._presampled_frequency = None

        # TODO: Update functionality when allowing raw data and csv file input
        # NOTE: If csv is implemented-> handle/disable statistics, PER_INTVL_, PER_DAY_, delta
        # ensemble, etc.
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
                    ensemble_paths, rel_file_pattern, self._presampled_frequency
                )
            else:
                self._input_provider_set = create_lazy_provider_set_from_paths(
                    ensemble_paths, rel_file_pattern
                )
        else:
            raise ValueError('Incorrect argument, must provide "ensembles"')

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
        self._vector_selector_base_data: list = []
        self._vector_calculator_data: list = []
        for vector in non_historical_vector_names:
            add_vector_to_vector_selector_data(
                self._vector_selector_base_data,
                vector,
            )

            # Only vectors from providers are provided to vector calculator
            add_vector_to_vector_selector_data(
                self._vector_calculator_data,
                vector,
            )

            metadata = (
                self._input_provider_set.vector_metadata(vector)
                if self._input_provider_set
                else None
            )
            if metadata and metadata.is_total:
                # Get the likely name for equivalent rate vector and make dropdown options.
                # Requires that the time_index was either defined or possible to infer.
                per_day_vec = create_per_day_vector_name(vector)
                per_intvl_vec = create_per_interval_vector_name(vector)

                add_vector_to_vector_selector_data(
                    self._vector_selector_base_data,
                    per_day_vec,
                )
                add_vector_to_vector_selector_data(
                    self._vector_selector_base_data,
                    per_intvl_vec,
                )

                # Add vector base to custom vector definition if not existing
                vector_base = vector.split(":")[0]
                _definition = wsc.VectorDefinitions.get(vector_base, None)
                _type = _definition["type"] if _definition else "others"

                per_day_vec_base = per_day_vec.split(":")[0]
                per_intvl_vec_base = per_intvl_vec.split(":")[0]
                if per_day_vec_base not in self._custom_vector_definitions:
                    self._custom_vector_definitions[
                        per_day_vec_base
                    ] = wsc.VectorDefinition(
                        type=_type,
                        description=simulation_vector_description(
                            per_day_vec_base, self._user_defined_vector_definitions
                        ),
                    )
                if per_intvl_vec_base not in self._custom_vector_definitions:
                    self._custom_vector_definitions[
                        per_intvl_vec_base
                    ] = wsc.VectorDefinition(
                        type=_type,
                        description=simulation_vector_description(
                            per_intvl_vec_base, self._user_defined_vector_definitions
                        ),
                    )

        # Retreive predefined expressions from configuration and validate
        self._predefined_expressions_path = (
            None
            if predefined_expressions is None
            else webviz_settings.shared_settings["predefined_expressions"][
                predefined_expressions
            ]
        )
        self._predefined_expressions = expressions_from_config(
            get_path(self._predefined_expressions_path)
            if self._predefined_expressions_path
            else None
        )
        for expression in self._predefined_expressions:
            valid, message = validate_predefined_expression(
                expression, self._vector_selector_base_data
            )
            if not valid:
                warnings.warn(message)
            expression["isValid"] = valid

        # Add expressions to custom vector definitions
        self._custom_vector_definitions_base = copy.deepcopy(
            self._custom_vector_definitions
        )
        _custom_vector_definitions_from_expressions = (
            get_vector_definitions_from_expressions(self._predefined_expressions)
        )
        for key, value in _custom_vector_definitions_from_expressions.items():
            if key not in self._custom_vector_definitions:
                self._custom_vector_definitions[key] = value

        # Create initial vector selector data with predefined expressions
        self._initial_vector_selector_data = copy.deepcopy(
            self._vector_selector_base_data
        )
        add_expressions_to_vector_selector_data(
            self._initial_vector_selector_data, self._predefined_expressions
        )

        plot_options = options if options else {}
        self._initial_visualization_selection = VisualizationOptions(
            plot_options.get("visualization", "statistics")
        )

        # Initial selected vectors - NB: {vector1, vector2, vector3} is deprecated!
        initial_vectors: List[str] = plot_options.get("vectors", [])

        # TODO: Remove when depretaced code is not utilized anymore
        if "vectors" in plot_options and any(
            elm in plot_options for elm in ["vector1", "vector2", "vector3"]
        ):
            warnings.warn(
                'Providing new user input option "vectors" and deprecated user input options '
                '"vector1", "vector2" and "vector3" simultaneously. Initially selected vectors '
                'for plugin are set equal to new user input option "vectors".'
            )
        if not initial_vectors:
            initial_vectors = [
                plot_options[elm]
                for elm in ["vector1", "vector2", "vector3"]
                if elm in plot_options
            ][:3]

        # Check if initially selected vectors exist in data, raise ValueError if not
        missing_vectors = [
            elm
            for elm in initial_vectors
            if not is_vector_name_in_vector_selector_data(
                elm, self._initial_vector_selector_data
            )
        ]
        if missing_vectors:
            raise ValueError(
                f"Cannot find: {', '.join(missing_vectors)} to plot initially in "
                "SimulationTimeSeries. Check that the vector(s) exist in your data."
            )

        if len(initial_vectors) > 3:
            warnings.warn(
                'User input option "vectors" contains more than 3 vectors. Only the first 3 listed '
                "vectors are kept for initially selected vectors - the remaining are neglected."
            )
        self._initial_vectors = initial_vectors[:3]

        # Set callbacks
        self.set_callbacks(app)

    @property
    def layout(self) -> wcc.FlexBox:
        return main_layout(
            get_uuid=self.uuid,
            ensemble_names=self._input_provider_set.names(),
            vector_selector_data=self._initial_vector_selector_data,
            vector_calculator_data=self._vector_calculator_data,
            predefined_expressions=self._predefined_expressions,
            custom_vector_definitions=self._custom_vector_definitions,
            realizations=self._input_provider_set.all_realizations(),
            disable_resampling_dropdown=self._presampled_frequency is not None,
            selected_resampling_frequency=self._sampling,
            selected_visualization=self._initial_visualization_selection,
            selected_vectors=self._initial_vectors,
            ensembles_dates=self._input_provider_set.all_dates(self._sampling),
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        plugin_callbacks(
            app=app,
            get_uuid=self.uuid,
            get_data_output=self.plugin_data_output,
            get_data_requested=self.plugin_data_requested,
            input_provider_set=self._input_provider_set,
            theme=self._theme,
            initial_selected_vectors=self._initial_vectors,
            vector_selector_base_data=self._vector_selector_base_data,
            custom_vector_definitions_base=self._custom_vector_definitions_base,
            observations=self._observations,
            user_defined_vector_definitions=self._user_defined_vector_definitions,
            line_shape_fallback=self._line_shape_fallback,
        )

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid(LayoutElements.TOUR_STEP_MAIN_LAYOUT),
                "content": "Dashboard displaying reservoir simulation time series.",
            },
            {
                "id": self.uuid(LayoutElements.GRAPH),
                "content": (
                    "Visualization of selected time series. "
                    "Different options can be set in the menu to the left."
                ),
            },
            {
                "id": self.uuid(LayoutElements.TOUR_STEP_SETTINGS_LAYOUT),
                "content": (
                    "Settings to configure data and layout of the time series visualization."
                ),
            },
            {
                "id": self.uuid(LayoutElements.TOUR_STEP_GROUP_BY),
                "content": (
                    "Setting to group visualization data according to selection. "
                    "Subplot per selected vector or per selected ensemble."
                ),
            },
            {
                "id": self.uuid(LayoutElements.RESAMPLING_FREQUENCY_DROPDOWN),
                "content": (
                    "Select resampling frequency for the time series data. "
                    "With presampled data, the dropdown is disabled and the presampling "
                    "frequency shown."
                ),
            },
            {
                "id": self.uuid(LayoutElements.ENSEMBLES_DROPDOWN),
                "content": (
                    "Display time series from one or several ensembles. "
                    "Ensembles will be overlain in subplot or represented per subplot, "
                    'based on selection in "Group By".'
                ),
            },
            {
                "id": self.uuid(LayoutElements.TOUR_STEP_DELTA_ENSEMBLE),
                "content": (
                    "Create delta ensembles (A-B). "
                    "Define delta between two ensembles and make available among "
                    "selectable ensembles."
                ),
            },
            {
                "id": self.uuid(LayoutElements.VECTOR_SELECTOR),
                "content": (
                    "Display up to three different time series. "
                    "Each time series will be visualized in a separate plot. "
                    "Vectors prefixed with PER_DAY_ and PER_INTVL_ are calculated in the fly "
                    "from cumulative vectors, providing average rates and interval cumulatives "
                    "over a time interval from the selected resampling frequency. Vectors "
                    "categorized as calculated are created using the Vector Calculator below."
                ),
            },
            {
                "id": self.uuid(LayoutElements.VECTOR_CALCULATOR_OPEN_BUTTON),
                "content": (
                    "Create mathematical expressions with provided vector time series. "
                    "Parsing of the mathematical expression is handled and will give feedback "
                    "when entering invalid expressions. "
                    "The expressions are calculated on the fly and can be selected among the time "
                    "series to be shown in the visualization."
                ),
            },
            {
                "id": self.uuid(LayoutElements.VISUALIZATION_RADIO_ITEMS),
                "content": (
                    "Choose between different visualizations. 1. Show time series as "
                    "individual lines per realization. 2. Show statistical lines per "
                    "ensemble. 3. Show statistical fanchart per ensemble."
                ),
            },
            {
                "id": self.uuid(LayoutElements.TOUR_STEP_OPTIONS),
                "content": (
                    "Various plot options: Whether to include history trace or vector observations "
                    "and which statistics to show if statistical lines or fanchart is chosen as "
                    "visualization."
                ),
            },
            {
                "id": self.uuid(LayoutElements.REALIZATIONS_FILTER_SELECTOR),
                "content": (
                    "Filter realizations. Select realization numbers to include in visualization, "
                    "and utilize in statistics calculation when calculating from selected subset."
                ),
            },
            {
                "id": self.uuid(LayoutElements.STATISTICS_FROM_RADIO_ITEMS),
                "content": (
                    "Select whether to calculate statistics from all realizations, or to calculate "
                    "statistics from the selected subset of realizations "
                ),
            },
        ]

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        functions: List[Tuple[Callable, list]] = []
        if self._obsfile:
            functions.append((get_path, [{"path": self._obsfile}]))
        if self._predefined_expressions_path:
            functions.append((get_path, [{"path": self._predefined_expressions_path}]))
        if self._user_defined_vector_descriptions_path:
            functions.append(
                (get_path, [{"path": self._user_defined_vector_descriptions_path}])
            )
        return functions

import copy
from typing import Dict, List, Optional

import dash
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import Input, Output, State, callback, dcc, html
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
from webviz_subsurface_components import ExpressionInfo, ExternalParseData

from webviz_subsurface._utils.vector_calculator import (
    VectorDefinition,
    add_expressions_to_vector_selector_data,
    get_selected_expressions,
    get_vector_definitions_from_expressions,
)
from webviz_subsurface._utils.vector_selector import (
    is_vector_name_in_vector_selector_data,
)


def _create_new_selected_vectors(
    existing_selected_vectors: List[str],
    existing_expressions: List[ExpressionInfo],
    new_expressions: List[ExpressionInfo],
    new_vector_selector_data: list,
) -> List[str]:
    valid_selections: List[str] = []
    for vector in existing_selected_vectors:
        new_vector: Optional[str] = vector

        # Get id if vector is among existing expressions
        dropdown_id = next(
            (elm["id"] for elm in existing_expressions if elm["name"] == vector),
            None,
        )
        # Find id among new expressions to get new/edited name
        if dropdown_id:
            new_vector = next(
                (elm["name"] for elm in new_expressions if elm["id"] == dropdown_id),
                None,
            )

        # Append if vector name exist among data
        if new_vector is not None and is_vector_name_in_vector_selector_data(
            new_vector, new_vector_selector_data
        ):
            valid_selections.append(new_vector)
    return valid_selections


class TimeSeriesSettings(SettingsGroupABC):
    class Ids(StrEnum):
        VECTOR_SELECTOR = "vector-selector"
        VECTOR_CALCULATOR_OPEN_BUTTON = "vector-calculator-open-button"
        VECTOR_CALCULATOR_DIALOG = "vector-calculator-dialog"
        VECTOR_CALCULATOR = "vector-calculator"
        VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG = (
            "vector-calculator-expression-open-dialog"
        )
        VECTOR_CALCULATOR_EXPRESSIONS = "vector-calculator-expression"
        GRAPH_DATA_HAS_CHANGED_TRIGGER = "graph-data-has-changed-trigger"

    def __init__(
        self,
        initial_vector_selector_data: List,
        custom_vector_definitions: Dict,
        vector_calculator_data: List,
        predefined_expressions: List[ExpressionInfo],
        vector_selector_base_data: List,
        custom_vector_definitions_base: Dict,
        initial_selected_vectors: Optional[List[str]] = None,
    ) -> None:
        super().__init__("Time series")
        self._vector_selector_data = initial_vector_selector_data
        self._selected_vectors = initial_selected_vectors
        self._custom_vector_definitions = custom_vector_definitions
        self._vector_calculator_data = vector_calculator_data
        self._predefined_expressions = predefined_expressions
        self._vector_selector_base_data = vector_selector_base_data
        self._custom_vector_definitions_base = custom_vector_definitions_base

    def layout(self) -> List[Component]:
        return [
            wsc.VectorSelector(
                id=self.register_component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_SELECTOR
                ),
                maxNumSelectedNodes=100,
                data=self._vector_selector_data,
                persistence=True,
                persistence_type="session",
                selectedTags=[]
                if self._selected_vectors is None
                else self._selected_vectors,
                numSecondsUntilSuggestionsAreShown=0.5,
                lineBreakAfterTag=True,
                customVectorDefinitions=self._custom_vector_definitions,
            ),
            html.Button(
                "Vector Calculator",
                id=self.register_component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_OPEN_BUTTON
                ),
                style={
                    "margin-top": "5px",
                    "margin-bottom": "5px",
                },
            ),
            wcc.Dialog(
                title="Vector Calculator",
                id=self.register_component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_DIALOG
                ),
                draggable=True,
                open=False,
                max_width="lg",
                children=[
                    html.Div(
                        style={"height": "60vh"},
                        children=[
                            wsc.VectorCalculator(
                                id=self.register_component_unique_id(
                                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR
                                ),
                                vectors=self._vector_calculator_data,
                                expressions=self._predefined_expressions,
                            )
                        ],
                    )
                ],
            ),
            dcc.Store(
                id=self.register_component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_EXPRESSIONS
                ),
                data=self._predefined_expressions,
            ),
            dcc.Store(
                id=self.register_component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG
                ),
                data=self._predefined_expressions,
            ),
            dcc.Store(
                # NOTE:Used to trigger graph update callback if data has
                # changed, i.e. no change of regular INPUT html-elements
                id=self.register_component_unique_id(
                    TimeSeriesSettings.Ids.GRAPH_DATA_HAS_CHANGED_TRIGGER
                ),
                data=0,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_DIALOG
                ).to_string(),
                "open",
            ),
            Input(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_OPEN_BUTTON
                ).to_string(),
                "n_clicks",
            ),
            State(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_DIALOG
                ).to_string(),
                "open",
            ),
        )
        @callback_typecheck
        def _toggle_vector_calculator_dialog_open(
            n_open_clicks: Optional[int], is_open: bool
        ) -> bool:
            if n_open_clicks:
                return not is_open
            raise PreventUpdate

        @callback(
            Output(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR
                ).to_string(),
                "externalParseData",
            ),
            Input(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR
                ).to_string(),
                "externalParseExpression",
            ),
        )
        @callback_typecheck
        def _parse_vector_calculator_expression(
            expression: Optional[ExpressionInfo],
        ) -> ExternalParseData:
            if expression is None:
                raise PreventUpdate
            return wsc.VectorCalculator.external_parse_data(expression)

        @callback(
            Output(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_EXPRESSIONS
                ).to_string(),
                "data",
            ),
            Output(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_SELECTOR
                ).to_string(),
                "data",
            ),
            Output(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_SELECTOR
                ).to_string(),
                "selectedTags",
            ),
            Output(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_SELECTOR
                ).to_string(),
                "customVectorDefinitions",
            ),
            Output(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.GRAPH_DATA_HAS_CHANGED_TRIGGER
                ).to_string(),
                "data",
            ),
            Input(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_DIALOG
                ).to_string(),
                "open",
            ),
            State(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG
                ).to_string(),
                "data",
            ),
            State(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_EXPRESSIONS
                ).to_string(),
                "data",
            ),
            State(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_SELECTOR
                ).to_string(),
                "selectedNodes",
            ),
            State(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_SELECTOR
                ).to_string(),
                "customVectorDefinitions",
            ),
            State(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.GRAPH_DATA_HAS_CHANGED_TRIGGER
                ).to_string(),
                "data",
            ),
        )
        @callback_typecheck
        def _update_vector_calculator_expressions_on_dialog_close(
            is_dialog_open: bool,
            new_expressions: List[ExpressionInfo],
            current_expressions: List[ExpressionInfo],
            current_selected_vectors: List[str],
            current_custom_vector_definitions: Dict[str, VectorDefinition],
            graph_data_has_changed_counter: int,
        ) -> list:
            """Update vector calculator expressions, propagate expressions to VectorSelectors,
            update current selections and trigger re-rendering of graphing if necessary
            """

            if is_dialog_open or (new_expressions == current_expressions):
                raise PreventUpdate

            # Create current selected expressions for comparison - Deep copy!
            current_selected_expressions = get_selected_expressions(
                current_expressions, current_selected_vectors
            )

            # Create new vector selector data - Deep copy!
            new_vector_selector_data = copy.deepcopy(self._vector_selector_base_data)
            add_expressions_to_vector_selector_data(
                new_vector_selector_data, new_expressions
            )

            # Create new selected vectors - from new expressions
            new_selected_vectors = _create_new_selected_vectors(
                current_selected_vectors,
                current_expressions,
                new_expressions,
                new_vector_selector_data,
            )

            # Get new selected expressions
            new_selected_expressions = get_selected_expressions(
                new_expressions, new_selected_vectors
            )

            # Get new custom vector definitions
            new_custom_vector_definitions = get_vector_definitions_from_expressions(
                new_expressions
            )
            for key, value in self._custom_vector_definitions_base.items():
                if key not in new_custom_vector_definitions:
                    new_custom_vector_definitions[key] = value

            # Prevent updates if unchanged
            if new_custom_vector_definitions == current_custom_vector_definitions:
                new_custom_vector_definitions = dash.no_update

            if new_selected_vectors == current_selected_vectors:
                new_selected_vectors = dash.no_update

            # If selected expressions are edited
            # - Only trigger graph data update property when needed,
            # i.e. names are unchanged and selectedNodes for VectorSelector remains unchanged.
            new_graph_data_has_changed_counter = dash.no_update
            if (
                new_selected_expressions != current_selected_expressions
                and new_selected_vectors == dash.no_update
            ):
                new_graph_data_has_changed_counter = graph_data_has_changed_counter + 1

            return [
                new_expressions,
                new_vector_selector_data,
                new_selected_vectors,
                new_custom_vector_definitions,
                new_graph_data_has_changed_counter,
            ]

        @callback(
            Output(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR_EXPRESSIONS_OPEN_DIALOG
                ).to_string(),
                "data",
            ),
            Input(
                self.component_unique_id(
                    TimeSeriesSettings.Ids.VECTOR_CALCULATOR
                ).to_string(),
                "expressions",
            ),
        )
        @callback_typecheck
        def _update_vector_calculator_expressions_when_dialog_open(
            expressions: List[ExpressionInfo],
        ) -> list:
            new_expressions: List[ExpressionInfo] = [
                elm for elm in expressions if elm["isValid"]
            ]
            return new_expressions

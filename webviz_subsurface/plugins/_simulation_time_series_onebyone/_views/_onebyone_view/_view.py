import datetime
from typing import Dict, List, Optional, Tuple, Union

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, State, callback, ctx, html, no_update
from dash.exceptions import PreventUpdate
from webviz_config import EncodedFile, WebvizPluginABC
from webviz_config._theme_class import WebvizConfigTheme
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from ..._types import LabelOptions, LineType
from ..._utils import SimulationTimeSeriesOneByOneDataModel, date_from_str, date_to_str
from ._settings import GeneralSettings, Selections, SensitivityFilter, Visualization
from ._view_elements import BottomVisualizationViewElement, GeneralViewElement


class OneByOneView(ViewABC):
    class Ids(StrEnum):
        TIMESERIES_PLOT = "time-series-plot"
        TORNADO_PLOT = "tornado-plot"
        BOTTOM_VISUALIZATION = "bottom-visualization"

        SELECTIONS = "selections"
        VIZUALISATION = "vizualisation"
        SENSITIVITY_FILTER = "sensitivity-filter"
        SETTINGS = "settings"

    def __init__(self, data_model: SimulationTimeSeriesOneByOneDataModel) -> None:
        super().__init__("OneByOne View")
        self._data_model = data_model

        self.add_settings_groups(
            {
                self.Ids.SELECTIONS: Selections(
                    ensembles=self._data_model.ensembles,
                    vectors=self._data_model.vectors,
                    vector_selector_data=self._data_model.initial_vector_selector_data,
                    dates=self._data_model.dates,
                    initial_vector=self._data_model.initial_vector,
                ),
                self.Ids.VIZUALISATION: Visualization(),
                self.Ids.SENSITIVITY_FILTER: SensitivityFilter(
                    sensitivities=self._data_model.sensitivities
                ),
                self.Ids.SETTINGS: GeneralSettings(
                    sensitivities=self._data_model.sensitivities,
                    initial_date=self._data_model.dates[-1],
                ),
            }
        )

        first_row = self.add_row()
        first_row.add_view_element(GeneralViewElement(), self.Ids.TIMESERIES_PLOT)
        first_row.add_view_element(GeneralViewElement(), self.Ids.TORNADO_PLOT)
        second_row = self.add_row()
        second_row.add_view_element(
            BottomVisualizationViewElement(), self.Ids.BOTTOM_VISUALIZATION
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.CHECKBOX_SETTINGS
                ),
                "value",
            ),
        )
        def _update_options(selected_options: list) -> dict:
            """Update graph with line coloring, vertical line and title"""
            all_options = [
                "color-by-sens",
                "real-scatter",
                "show-tornado-ref",
                "remove-no-impact",
            ]
            return {option: option in selected_options for option in all_options}

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.REAL_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SENSITIVITY_FILTER,
                    SensitivityFilter.Ids.SENSITIVITY_FILTER,
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
                ),
                "value",
            ),
        )
        def _update_realization_store(sensitivites: list, ensemble: str) -> List[int]:
            """Update graph with line coloring, vertical line and title"""
            df = self._data_model.get_sensitivity_dataframe_for_ensemble(ensemble)
            return list(df[df["SENSNAME"].isin(sensitivites)]["REAL"].unique())

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SENSITIVITY_FILTER,
                    SensitivityFilter.Ids.SENSITIVITY_FILTER,
                ),
                "value",
            ),
            Input(
                self.view_element(self.Ids.TORNADO_PLOT)
                .component_unique_id(GeneralViewElement.Ids.GRAPH)
                .to_string(),
                "clickData",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.REFERENCE
                ),
                "value",
            ),
            prevent_initial_call=True,
        )
        @callback_typecheck
        def _update_sensitivity_filter(
            tornado_click_data: dict, reference: str
        ) -> List[str]:
            """Update graph with line coloring, vertical line and title"""
            clicked_data = tornado_click_data["points"][0]
            return [clicked_data["y"], reference]

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SENSITIVITY_FILTER,
                    SensitivityFilter.Ids.SENSITIVITY_FILTER,
                ),
                "options",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.REFERENCE
                ),
                "options",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.REFERENCE
                ),
                "value",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.VECTOR_SELECTOR
                ),
                "data",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.VECTOR_SELECTOR
                ),
                "selectedTags",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.VECTOR_SELECTOR
                ),
                "selectedNodes",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.REFERENCE
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_sensitivity_filter_and_reference(
            ensemble: str, vector: list, reference: str
        ) -> tuple:
            """Update graph with line coloring, vertical line and title"""
            sensitivities = self._data_model.get_unique_sensitivities_for_ensemble(
                ensemble
            )
            available_vectors = self._data_model._vmodel._provider_set[
                ensemble
            ].vector_names_filtered_by_value(
                exclude_all_values_zero=True, exclude_constant_values=True
            )
            vector_selector_data = self._data_model.vmodel.create_vector_selector_data(
                available_vectors
            )

            vector = (
                vector if vector[0] in available_vectors else [available_vectors[0]]
            )
            return (
                [{"label": elm, "value": elm} for elm in sensitivities],
                [{"label": elm, "value": elm} for elm in sensitivities],
                self._data_model.get_tornado_reference(sensitivities, reference),
                vector_selector_data,
                vector,
            )

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.VECTOR_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.VECTOR_SELECTOR
                ),
                "selectedNodes",
            ),
        )
        @callback_typecheck
        def _update_vector_store(vector: list) -> str:
            """Unpack selected vector in vector selector"""
            if not vector:
                raise PreventUpdate
            return vector[0]

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.DATE_STORE
                ),
                "data",
            ),
            Output(get_uuid("date_selector_wrapper"), "children"),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
                ),
                "value",
            ),
            Input(
                self.view_element(self.Ids.TIMESERIES_PLOT)
                .component_unique_id(GeneralViewElement.Ids.GRAPH)
                .to_string(),
                "clickData",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.DATE_SLIDER
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.DATE_STORE
                ),
                "data",
            ),
        )
        def _render_date_selector(
            ensemble: str,
            timeseries_clickdata: Union[None, dict],
            dateidx: List[int],
            date: str,
        ) -> Tuple[str, html.Div]:
            """Store selected date and tornado input. Write statistics
            to table"""

            dates = self._data_model.vmodel.dates_for_ensemble(ensemble)
            dateslider_drag = get_uuid("date-slider") in str(ctx.triggered_id)

            if timeseries_clickdata is not None and ctx.triggered_id == get_uuid(
                "graph"
            ):
                date = timeseries_clickdata.get("points", [{}])[0]["x"]
            elif dateslider_drag:
                date = date_to_str(dates[dateidx[0]])

            date_selected = (
                date_from_str(date)
                if date_from_str(date) in dates
                else self._data_model.vmodel.get_last_date(ensemble)
            )

            return (
                date_to_str(date_selected),
                date_selector(get_uuid, date_selected=date_selected, dates=dates)
                if not dateslider_drag
                else no_update,
            )

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.SELECTED_DATE
                ),
                "children",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.DATE_SLIDER
                ),
                "drag_value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
                ),
                "value",
            ),
            prevent_initial_call=True,
        )
        @callback_typecheck
        def _update_date_text(dateidx: List[int], ensemble: str) -> List[str]:
            """Update selected date text on date-slider drag"""
            if ctx.triggered_id == self.settings_group_unique_id(
                self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
            ):
                date = self._data_model.vmodel.get_last_date(ensemble)
            else:
                dates = self._data_model.vmodel.dates_for_ensemble(ensemble)
                date = dates[dateidx[0]]
            return [date_to_str(date)]

        @callback(
            Output(
                self.view_element(self.Ids.TIMESERIES_PLOT)
                .component_unique_id(GeneralViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.DATE_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION, Visualization.Ids.REALIZATION_OR_MEAN
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.VECTOR_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.REAL_STORE
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_timeseries_figure(
            date: str,
            linetype: LineType,
            vector: str,
            realizations: list,
            ensemble: str,
        ) -> go.Figure:
            # Get dataframe with vectors and dataframe with parameters and merge
            vector_df = self._data_model.vmodel.get_vector_df(
                ensemble=ensemble, vectors=[vector], realizations=realizations
            )
            data = merge_dataframes_on_realization(
                dframe1=vector_df,
                dframe2=self._data_model.get_sensitivity_dataframe_for_ensemble(
                    ensemble
                ),
            )
            if linetype == LineType.MEAN:
                data = self._data_model.create_vectors_statistics_df(data)

            return self._data_model.create_timeseries_figure(
                data, vector, ensemble, date, linetype
            )

        @callback(
            Output(
                self.view_element(self.Ids.BOTTOM_VISUALIZATION).component_unique_id(
                    BottomVisualizationViewElement.Ids.TABLE
                ),
                "data",
            ),
            Output(
                self.view_element(self.Ids.BOTTOM_VISUALIZATION).component_unique_id(
                    BottomVisualizationViewElement.Ids.TABLE
                ),
                "columns",
            ),
            Output(
                self.view_element(self.Ids.TORNADO_PLOT).component_unique_id(
                    GeneralViewElement.Ids.GRAPH
                ),
                "figure",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.DATE_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.VECTOR_STORE
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_tornadoplot(
            date: str, selections: dict, vector: str, ensemble: str
        ) -> tuple:
            if selections is None or selections[
                "Reference"
            ] not in self._data_model.get_unique_sensitivities_for_ensemble(ensemble):
                raise PreventUpdate

            # Get dataframe with vectors and dataframe with parameters and merge
            vector_df = self._data_model.vmodel.get_vector_df(
                ensemble=ensemble, vectors=[vector], date=date_from_str(date)
            )
            data = merge_dataframes_on_realization(
                dframe1=vector_df,
                dframe2=self._data_model.get_sensitivity_dataframe_for_ensemble(
                    ensemble
                ),
            )

            tornado_data = self._data_model.get_tornado_data(data, vector, selections)
            use_si_format = tornado_data.reference_average > 1000
            tornadofig = self._data_model.create_tornado_figure(
                tornado_data, selections, use_si_format
            )
            table, columns = self._data_model.create_tornado_table(
                tornado_data, use_si_format
            )
            return table, columns, tornadofig

        @callback(
            Output(
                self.view_element(self.Ids.BOTTOM_VISUALIZATION).component_unique_id(
                    BottomVisualizationViewElement.Ids.REAL_GRAPH
                ),
                "figure",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.DATE_STORE
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.VECTOR_STORE
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION, Visualization.Ids.BOTTOM_VISUALIZATION
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_realplot(
            date: str,
            selections: dict,
            vector: str,
            ensemble: str,
            selected_vizualisation: str,
        ) -> go.Figure:
            if selections is None or selected_vizualisation == "table":
                raise PreventUpdate

            # Get dataframe with vectors and dataframe with parameters and merge
            vector_df = self._data_model.vmodel.get_vector_df(
                ensemble=ensemble, vectors=[vector], date=date_from_str(date)
            )
            data = merge_dataframes_on_realization(
                dframe1=vector_df,
                dframe2=self._data_model.get_sensitivity_dataframe_for_ensemble(
                    ensemble
                ),
            )
            tornado_data = self._data_model.get_tornado_data(data, vector, selections)

            return self.data_model.create_realplot(tornado_data)

        @callback(
            Output(
                self.view_element(
                    self.Ids.BOTTOM_VISUALIZATION,
                    BottomVisualizationViewElement.Ids.REAL_GRAPH_WRAPPER,
                ),
                "style",
            ),
            Output(
                self.view_element(
                    self.Ids.BOTTOM_VISUALIZATION,
                    BottomVisualizationViewElement.Ids.TABLE_WRAPPER,
                ),
                "style",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION, Visualization.Ids.BOTTOM_VISUALIZATION
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _display_table_or_realplot(selected_vizualisation: str) -> tuple:
            return {
                "display": "none" if selected_vizualisation == "table" else "block"
            }, {"display": "block" if selected_vizualisation == "table" else "none"}

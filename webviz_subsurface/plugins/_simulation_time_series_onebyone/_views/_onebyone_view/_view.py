import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, ctx
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from webviz_subsurface._utils.dataframe_utils import merge_dataframes_on_realization

from ..._types import LineType
from ..._utils import (
    SimulationTimeSeriesOneByOneDataModel,
    create_tornado_table,
    create_vector_selector_data,
    date_from_str,
    date_to_str,
    get_tornado_data,
)
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
                    dates=self._data_model.all_dates,
                    initial_vector=self._data_model.initial_vector,
                ),
                self.Ids.VIZUALISATION: Visualization(),
                self.Ids.SENSITIVITY_FILTER: SensitivityFilter(
                    sensitivities=self._data_model.sensitivities
                ),
                self.Ids.SETTINGS: GeneralSettings(
                    sensitivities=self._data_model.sensitivities,
                    initial_date=self._data_model.all_dates[-1],
                ),
            }
        )

        main_column = self.add_column()
        first_row = main_column.make_row()
        first_row.add_view_element(GeneralViewElement(), self.Ids.TIMESERIES_PLOT)
        first_row.add_view_element(GeneralViewElement(), self.Ids.TORNADO_PLOT)
        second_row = main_column.make_row()
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
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS
                    ),
                    "selector": ALL,
                },
                "value",
            ),
            State(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS
                    ),
                    "selector": ALL,
                },
                "id",
            ),
        )
        def _update_options(option_values: list, options_id: List[dict]) -> dict:
            """Update graph with line coloring, vertical line and title"""
            return {
                opt["selector"]: value for opt, value in zip(options_id, option_values)
            }

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
            if not sensitivites:
                raise PreventUpdate
            df = self._data_model.get_sensitivity_dataframe_for_ensemble(ensemble)
            return self._data_model.get_realizations_for_sensitivies(df, sensitivites)

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SENSITIVITY_FILTER,
                    SensitivityFilter.Ids.SENSITIVITY_FILTER,
                ),
                "value",
                allow_duplicate=True,
            ),
            Input(
                self.view_element(self.Ids.TORNADO_PLOT)
                .component_unique_id(GeneralViewElement.Ids.GRAPH)
                .to_string(),
                "clickData",
            ),
            State(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS
                    ),
                    "selector": "Reference",
                },
                "value",
            ),
            prevent_initial_call=True,
        )
        @callback_typecheck
        def _update_sensitivity_filter(
            tornado_click_data: Optional[Dict], reference: str
        ) -> List[str]:
            """Update graph with line coloring, vertical line and title"""
            if tornado_click_data is None:
                raise PreventUpdate

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
                    self.Ids.SENSITIVITY_FILTER,
                    SensitivityFilter.Ids.SENSITIVITY_FILTER,
                ),
                "value",
                allow_duplicate=True,
            ),
            Output(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS
                    ),
                    "selector": "Reference",
                },
                "options",
            ),
            Output(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS
                    ),
                    "selector": "Reference",
                },
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
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.SETTINGS, GeneralSettings.Ids.OPTIONS
                    ),
                    "selector": "Reference",
                },
                "value",
            ),
            prevent_initial_call="initial_duplicate",
        )
        @callback_typecheck
        def _update_sensitivity_filter_reference_and_vector_selector(
            ensemble: str, vector: list, reference: str
        ) -> tuple:
            """Update graph with line coloring, vertical line and title"""
            sensitivities = self._data_model.get_unique_sensitivities_for_ensemble(
                ensemble
            )
            available_vectors = self._data_model.provider(
                ensemble
            ).vector_names_filtered_by_value(
                exclude_all_values_zero=True, exclude_constant_values=True
            )
            vector_selector_data = create_vector_selector_data(available_vectors)

            vector = (
                vector if vector[0] in available_vectors else [available_vectors[0]]
            )
            return (
                [{"label": elm, "value": elm} for elm in sensitivities],
                sensitivities,
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
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.SELECTED_DATE
                ),
                "children",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.DATE_SLIDER
                ),
                "value",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.DATE_SLIDER
                ),
                "max",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, Selections.Ids.DATE_SLIDER
                ),
                "marks",
            ),
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
        )
        def _update_date(
            ensemble: str,
            timeseries_clickdata: Union[None, dict],
            dateidx: int,
        ) -> Tuple[str, str, int, int, Dict[int, Dict[str, Any]]]:
            """Store selected date and tornado input. Write statistics
            to table"""

            new_ensemble = self.settings_group_unique_id(
                self.Ids.SELECTIONS, Selections.Ids.ENSEMBLE
            ) in str(ctx.triggered_id)
            dateslider_drag = self.settings_group_unique_id(
                self.Ids.SELECTIONS, Selections.Ids.DATE_SLIDER
            ) in str(ctx.triggered_id)
            timeseriesgraph_click = (
                timeseries_clickdata is not None
                and self.view_element(self.Ids.TIMESERIES_PLOT)
                .component_unique_id(GeneralViewElement.Ids.GRAPH)
                .to_string()
                in ctx.triggered_id
            )
            dates = self._data_model.ensemble_dates(ensemble)

            if new_ensemble:
                date_selected = dates[-1]
            elif timeseriesgraph_click and timeseries_clickdata is not None:
                date_selected = date_from_str(
                    timeseries_clickdata.get("points", [{}])[0]["x"]
                )
                if date_selected not in dates:
                    date_selected = get_closest_date(dates, date_selected)

            elif dateslider_drag:
                date_selected = dates[dateidx]
            else:
                date_selected = dates[-1]

            return (
                date_to_str(date_selected),
                date_to_str(date_selected),
                dates.index(date_selected),
                len(dates) - 1,
                {
                    idx: {
                        "label": date_to_str(dates[idx]),
                        "style": {"white-space": "nowrap"},
                    }
                    for idx in [0, len(dates) - 1]
                },
            )

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
            vector_df = self._data_model.get_vectors_df(
                ensemble=ensemble, vector_names=[vector], realizations=realizations
            )
            data = merge_dataframes_on_realization(
                dframe1=vector_df,
                dframe2=self._data_model.get_sensitivity_dataframe_for_ensemble(
                    ensemble
                ),
            )
            if linetype == LineType.STATISTICS:
                data = self._data_model.create_vectors_statistics_df(data)

            return self._data_model.create_timeseries_figure(
                data, vector, ensemble, date, linetype
            )

        @callback(
            Output(
                self.view_element(self.Ids.BOTTOM_VISUALIZATION)
                .component_unique_id(BottomVisualizationViewElement.Ids.TABLE)
                .to_string(),
                "data",
            ),
            Output(
                self.view_element(self.Ids.BOTTOM_VISUALIZATION)
                .component_unique_id(BottomVisualizationViewElement.Ids.TABLE)
                .to_string(),
                "columns",
            ),
            Output(
                self.view_element(self.Ids.TORNADO_PLOT)
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
            Input(
                self.settings_group_unique_id(
                    self.Ids.SETTINGS, GeneralSettings.Ids.REAL_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SENSITIVITY_FILTER,
                    SensitivityFilter.Ids.SENSITIVITY_FILTER_LINK,
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
        @callback_typecheck
        def _update_tornadoplot(
            date: str,
            selections: dict,
            vector: str,
            realizations: List[int],
            sensfilter_only_timeseries: list,
            ensemble: str,
        ) -> tuple:
            if selections is None or selections[
                "Reference"
            ] not in self._data_model.get_unique_sensitivities_for_ensemble(ensemble):
                raise PreventUpdate

            sens_df = self._data_model.get_sensitivity_dataframe_for_ensemble(ensemble)

            # make sure the tornado reference is included if sensitivity filter is used
            if not sensfilter_only_timeseries:
                reference_realizations = (
                    self._data_model.get_realizations_for_sensitivies(
                        sens_df, sensitivities=[selections["Reference"]]
                    )
                )
                realizations = list(set(reference_realizations + realizations))

            # Get dataframe with vectors and dataframe with parameters and merge
            vector_df = self._data_model.get_vectors_df(
                ensemble=ensemble,
                date=date_from_str(date),
                vector_names=[vector],
                realizations=realizations if not sensfilter_only_timeseries else None,
            )
            data = merge_dataframes_on_realization(
                dframe1=vector_df,
                dframe2=self._data_model.get_sensitivity_dataframe_for_ensemble(
                    ensemble
                ),
            )

            tornado_data = get_tornado_data(data, vector, selections)
            use_si_format = tornado_data.reference_average > 1000
            tornadofig = self._data_model.create_tornado_figure(
                tornado_data=tornado_data,
                selections=selections,
                use_si_format=use_si_format,
                title=f"Tornadoplot for {tornado_data.response_name} at {date} <br>",
            )
            table, columns = create_tornado_table(tornado_data, use_si_format)
            return table, columns, tornadofig

        @callback(
            Output(
                self.view_element(self.Ids.BOTTOM_VISUALIZATION)
                .component_unique_id(BottomVisualizationViewElement.Ids.REAL_GRAPH)
                .to_string(),
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
            selections: Optional[Dict],
            vector: str,
            ensemble: str,
            selected_vizualisation: str,
        ) -> go.Figure:
            if selections is None or selected_vizualisation == "table":
                raise PreventUpdate

            # Get dataframe with vectors and dataframe with parameters and merge
            vector_df = self._data_model.get_vectors_df(
                ensemble=ensemble,
                date=date_from_str(date),
                vector_names=[vector],
            )
            data = merge_dataframes_on_realization(
                dframe1=vector_df,
                dframe2=self._data_model.get_sensitivity_dataframe_for_ensemble(
                    ensemble
                ),
            )
            tornado_data = get_tornado_data(data, vector, selections)

            return self._data_model.create_realplot(tornado_data)

        @callback(
            Output(
                self.view_element(self.Ids.BOTTOM_VISUALIZATION)
                .component_unique_id(
                    BottomVisualizationViewElement.Ids.REAL_GRAPH_WRAPPER
                )
                .to_string(),
                "style",
            ),
            Output(
                self.view_element(self.Ids.BOTTOM_VISUALIZATION)
                .component_unique_id(BottomVisualizationViewElement.Ids.TABLE_WRAPPER)
                .to_string(),
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


def get_closest_date(
    dates: List[datetime.datetime], date: datetime.datetime
) -> datetime.datetime:
    # Returns the closest date to the input date in the dates list.
    return min(dates, key=lambda dte: abs(dte - date))

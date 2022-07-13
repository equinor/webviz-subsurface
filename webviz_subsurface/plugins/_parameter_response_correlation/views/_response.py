from typing import List

import pandas as pd
from dash import Input, Output, callback
from webviz_config import WebvizSettings
from webviz_config.webviz_plugin_subclasses import ViewABC

import webviz_subsurface._utils.parameter_response as parresp

from .._plugin_ids import PluginIds
from ..view_elements import Graph
from ._filter import Filter
from ._view_functions import correlate, make_correlation_plot, make_distribution_plot


class ResponseView(ViewABC):
    # pylint: disable=too-many-arguments
    class Ids:
        # pylint: disable=too-few-public-methods
        CORRELATIONS = "correlations-chart"
        DISTRIBUTIONS = "distributions-chart"
        CONTROLS_SETTINGS = "controls-settings"
        FILTERS_SETTINGS = "filter-settings"
        # INITIAL_PARAMETER = "initial-parameter"

    def __init__(
        self,
        response_df: pd.DataFrame,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        response_filters: dict,
        parameter_columns: list,
        response_columns: List[str],
        aggregation: str,
        corr_method: str,
        parameterdf: pd.DataFrame,
    ) -> None:
        super().__init__("Response chart")

        self.responsedf = response_df
        self.ensembles = ensembles
        self.response_filters = response_filters
        self.parameter_columns = parameter_columns
        self.response_columns = response_columns
        self.aggregation = aggregation
        self.corr_method = corr_method
        self.parameterdf = parameterdf

        self.add_settings_group(
            Filter(
                self.responsedf,
                self.ensembles,
                self.response_filters,
                self.parameter_columns,
                self.response_columns,
                self.aggregation,
                self.corr_method,
                "Controls",
            ),
            ResponseView.Ids.CONTROLS_SETTINGS,
        )
        self.add_settings_group(
            Filter(
                self.responsedf,
                self.ensembles,
                self.response_filters,
                self.parameter_columns,
                self.response_columns,
                self.aggregation,
                self.corr_method,
                "Filters",
            ),
            ResponseView.Ids.FILTERS_SETTINGS,
        )

        column = self.add_column()
        first_row = column.make_row()
        first_row.add_view_element(Graph("80vh"), ResponseView.Ids.CORRELATIONS)
        first_row.add_view_element(Graph("80vh"), ResponseView.Ids.DISTRIBUTIONS)
        self.theme = webviz_settings.theme

    @property
    def correlation_input_callbacks(self) -> List[Input]:
        """List of Inputs for correlation callback"""
        callbacks = [
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.RESPONSE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.CORRELATION_METHOD)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.RESPONSE_AGGREGATION)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.CORRELATION_CUTOFF)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.MAX_NUMBER_PARAMETERS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ResponseView.Ids.FILTERS_SETTINGS)
                .component_unique_id(Filter.Ids.PARAMETERS)
                .to_string(),
                "value",
            ),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(
                    Input(
                        self.settings_group(ResponseView.Ids.FILTERS_SETTINGS)
                        .component_unique_id(f"filter-{col_name}")
                        .to_string(),
                        "value",
                    )
                )
        return callbacks

    @property
    def distribution_input_callbacks(self) -> List[Input]:
        """List of Inputs for distribution callback"""
        callbacks = [
            Input(
                self.view_element(ResponseView.Ids.CORRELATIONS)
                .component_unique_id(Graph.Ids.GRAPH)
                .to_string(),
                "clickData",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.INITIAL_PARAMETER), "data"),
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.RESPONSE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ResponseView.Ids.CONTROLS_SETTINGS)
                .component_unique_id(Filter.Ids.RESPONSE_AGGREGATION)
                .to_string(),
                "value",
            ),
        ]
        if self.response_filters:
            for col_name in self.response_filters:
                callbacks.append(
                    Input(
                        self.settings_group(ResponseView.Ids.FILTERS_SETTINGS)
                        .component_unique_id(f"filter-{col_name}")
                        .to_string(),
                        "value",
                    )
                )
        return callbacks

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(ResponseView.Ids.CORRELATIONS)
                .component_unique_id(Graph.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Output(
                self.get_store_unique_id(PluginIds.Stores.INITIAL_PARAMETER), "data"
            ),
            self.correlation_input_callbacks,
        )
        def _update_correlation_plot(
            ensemble: str,
            response: str,
            correlation_method: str,
            aggregation: str,
            correlation_cutoff: float,
            max_parameters: int,
            selected_parameters: List[str],
            *filters,
        ):
            filteroptions = parresp.make_response_filters(
                response_filters=self.response_filters,
                response_filter_values=filters,
            )
            responsedf = parresp.filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=aggregation,
            )
            parameterdf = self.parameterdf[
                ["ENSEMBLE", "REAL"] + selected_parameters
            ].loc[self.parameterdf["ENSEMBLE"] == ensemble]

            df = pd.merge(responsedf, parameterdf, on=["REAL"])
            corrdf = correlate(df, response=response, method=correlation_method)
            try:
                corr_response = (
                    corrdf[response]
                    .dropna()
                    .drop(["REAL", response], axis=0)
                    .tail(n=max_parameters)
                )
                corr_response = corr_response[corr_response.abs() >= correlation_cutoff]
                return (
                    make_correlation_plot(
                        corr_response,
                        response,
                        self.theme,
                        correlation_method,
                        correlation_cutoff,
                        max_parameters,
                    ),
                    corr_response.index[-1],
                )
            except (KeyError, ValueError):
                return (
                    {
                        "layout": {
                            "title": "<b>Cannot calculate correlation for given selection</b><br>"
                            "Select a different response or filter setting."
                        }
                    },
                    None,
                )

        @callback(
            Output(
                self.view_element(ResponseView.Ids.DISTRIBUTIONS)
                .component_unique_id(Graph.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            self.distribution_input_callbacks,
        )
        def _update_distribution_graph(
            clickdata, initial_parameter, ensemble, response, aggregation, *filters
        ):
        
            if clickdata:
                parameter = clickdata["points"][0]["y"]
            elif initial_parameter:
                parameter = initial_parameter
            else:
                return {}
            filteroptions = parresp.make_response_filters(
                response_filters=self.response_filters,
                response_filter_values=filters,
            )
            responsedf = parresp.filter_and_sum_responses(
                self.responsedf,
                ensemble,
                response,
                filteroptions=filteroptions,
                aggregation=aggregation,
            )
            parameterdf = self.parameterdf.loc[self.parameterdf["ENSEMBLE"] == ensemble]
            df = pd.merge(responsedf, parameterdf, on=["REAL"])[
                ["REAL", parameter, response]
            ]
            return make_distribution_plot(df, parameter, response, self.theme)

import datetime
from typing import Any, Dict, List, Tuple, Union

import plotly.graph_objects as go
from dash import Input, Output, State, callback, callback_context, no_update
from dash.exceptions import PreventUpdate
from webviz_config import WebvizConfigTheme
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ....._figures import BarChart, ScatterPlot, TimeSeriesFigure
from ....._providers import Frequency
from ....._utils.colors import hex_to_rgba_str, rgba_to_hex
from ....._utils.dataframe_utils import (
    correlate_response_with_dataframe,
    merge_dataframes_on_realization,
)
from ..._utils import ParametersModel, ProviderTimeSeriesDataModel
from ..._utils import _datetime_utils as datetime_utils
from ._settings import (
    ParamRespOptions,
    ParamRespParameterFilter,
    ParamRespSelections,
    ParamRespVizualisation,
)
from ._view_element import ParamRespViewElement


class ParameterResponseView(ViewABC):
    class Ids(StrEnum):
        SELECTIONS = "selections"
        VIZUALISATION = "vizualisation"
        OPTIONS = "options"
        PARAMETER_FILTER = "parameter-filter"
        TIME_SERIES_CHART = "time-series-chart"
        VECTOR_VS_PARAM_SCATTER = "vector-vs-param-scatter"
        VECTOR_CORR_GRAPH = "vector-corr-graph"
        PARAM_CORR_GRAPH = "param-corr-graph"

    def __init__(
        self,
        parametermodel: ParametersModel,
        vectormodel: ProviderTimeSeriesDataModel,
        observations: Dict,
        selected_resampling_frequency: Frequency,
        disable_resampling_dropdown: bool,
        theme: WebvizConfigTheme,
    ) -> None:
        super().__init__("Parameter Response Analysis")

        self._parametermodel = parametermodel
        self._vectormodel = vectormodel
        self._observations = observations
        self._disable_resampling_dropdown = disable_resampling_dropdown
        self._theme = theme

        self.add_settings_groups(
            {
                self.Ids.SELECTIONS: ParamRespSelections(
                    parametermodel=self._parametermodel,
                    vectormodel=self._vectormodel,
                    selected_resampling_frequency=selected_resampling_frequency,
                    disable_resampling_dropdown=disable_resampling_dropdown,
                ),
                self.Ids.OPTIONS: ParamRespOptions(),
                self.Ids.VIZUALISATION: ParamRespVizualisation(self._theme),
                self.Ids.PARAMETER_FILTER: ParamRespParameterFilter(
                    self._parametermodel.dataframe, self._parametermodel.ensembles
                ),
            }
        )

        first_column = self.add_column()
        first_column.add_view_element(
            ParamRespViewElement(), self.Ids.TIME_SERIES_CHART
        )
        first_column.add_view_element(
            ParamRespViewElement(), self.Ids.VECTOR_VS_PARAM_SCATTER
        )
        second_column = self.add_column()
        second_column.add_view_element(
            ParamRespViewElement(), self.Ids.VECTOR_CORR_GRAPH
        )
        second_column.add_view_element(
            ParamRespViewElement(), self.Ids.PARAM_CORR_GRAPH
        )

    def set_callbacks(self) -> None:
        # pylint: disable=too-many-statements
        @callback(
            Output(
                self.view_element(self.Ids.TIME_SERIES_CHART)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Output(
                self.view_element(self.Ids.VECTOR_VS_PARAM_SCATTER)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Output(
                self.view_element(self.Ids.VECTOR_CORR_GRAPH)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Output(
                self.view_element(self.Ids.PARAM_CORR_GRAPH)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.ENSEMBLE
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.VECTOR_SELECTOR
                ),
                "selectedNodes",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.PARAMETER_SELECT
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SELECTED
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.OPTIONS, ParamRespOptions.Ids.VECTOR_FILTER_STORE
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION, ParamRespVizualisation.Ids.LINE_OPTION
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION,
                    ParamRespVizualisation.Ids.CHECKBOX_OPTIONS_STORE,
                ),
                "data",
            ),
            Input(
                {
                    "id": self.settings_group(self.Ids.PARAMETER_FILTER)
                    .component_unique_id(ParamRespParameterFilter.Ids.PARAM_FILTER)
                    .to_string(),
                    "type": "data-store",
                },
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS,
                    ParamRespSelections.Ids.RESAMPLING_FREQUENCY_DROPDOWN,
                ),
                "value",
            ),
            State(
                self.view_element(self.Ids.PARAM_CORR_GRAPH)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            State(
                self.view_element(self.Ids.VECTOR_CORR_GRAPH)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
        )
        @callback_typecheck
        # pylint: disable=too-many-locals, too-many-arguments, too-many-branches
        def _update_graphs(
            ensemble: str,
            vector: List[str],
            param: Union[None, str],
            datestr: str,
            column_keys: Union[None, str],
            visualization: str,
            options: Union[None, Dict[str, Any]],
            real_filter: Dict[str, List[int]],
            resampling_frequency: Frequency,
            corr_p_fig: Union[None, dict],
            corr_v_fig: Union[None, dict],
        ) -> List[Any]:
            """
            Main callback to update plots. Initially all plots are generated,
            while only relevant plots are updated in subsequent callbacks
            """
            ctx = callback_context.triggered[0]["prop_id"].split(".")[0]
            if not ctx or not vector:
                raise PreventUpdate
            selected_vector = vector[0]

            date = datetime_utils.from_str(datestr)
            realizations = real_filter[ensemble]

            color = (
                options["color"]
                if options is not None and options["color"] is not None
                else "#007079"
            )

            if len(realizations) <= 1:
                return [empty_figure()] * 4

            vectors_for_param_corr = (
                self._vectormodel.filter_vectors(column_keys, ensemble=ensemble)
                if column_keys is not None
                else []
            )

            try:
                # Get dataframe with vectors and dataframe with parameters and merge
                # If the resampling dropdown is disable it means the data is presampled,
                # in which case we pass None as resampling frequency
                vector_df = self._vectormodel.get_vector_df(
                    ensemble=ensemble,
                    realizations=realizations,
                    vectors=list(set(vectors_for_param_corr + [selected_vector])),
                    resampling_frequency=resampling_frequency
                    if not self._disable_resampling_dropdown
                    else None,
                )
            except ValueError:
                # It could be that the selected vector does not exist in the
                # selected ensemble, f.ex if the ensembles have different well names
                return [
                    empty_figure(
                        "Selected vector probably does not exist in selected ensemble"
                    )
                ] * 4

            if date not in vector_df["DATE"].values:
                return [empty_figure("Selected date does not exist for ensemble")] * 4
            if selected_vector not in vector_df:
                return [empty_figure("Selected vector does not exist for ensemble")] * 4

            param_df = self._parametermodel.get_parameter_df_for_ensemble(
                ensemble, realizations
            )
            merged_df = merge_dataframes_on_realization(
                dframe1=vector_df[vector_df["DATE"] == date], dframe2=param_df
            )

            # Make correlation figure for vector (upper right plot)
            if options is not None and not options["autocompute_corr"]:
                corr_v_fig = empty_figure(
                    "'Calculate Correlations' option not selected"
                )
            else:
                corrseries = correlate_response_with_dataframe(
                    merged_df, selected_vector, self._parametermodel.parameters
                )
                if corrseries.isnull().values.any():
                    # If all response values are equal, correlations will be Nan
                    corr_v_fig = empty_figure("Not able to calculate correlations")
                else:
                    corr_v_fig = BarChart(
                        corrseries,
                        n_rows=15,
                        title=f"Correlations with {selected_vector}",
                        orientation="h",
                    ).figure
                    param = param if param is not None else corrseries.abs().idxmax()
                    corr_v_fig = color_corr_bars(
                        corr_v_fig,
                        param,
                        color,
                        options["opacity"] if options is not None else 0.5,
                    )

            # Make correlation figure for parameter (lower right plot)
            if options is not None and not options["autocompute_corr"]:
                corr_p_fig = empty_figure(
                    "'Calculate Correlations' option not selected"
                )
            elif not vectors_for_param_corr:
                text = (
                    "Select vectors to correlate with parameter"
                    if not bool(column_keys)
                    else "No vectors match selected filter"
                )
                corr_p_fig = empty_figure(text)
            else:
                # Make correlation figure for parameter
                if options is not None and options["autocompute_corr"]:
                    if param is None:
                        # This can happen if vector correlations failed
                        corr_p_fig = empty_figure("Not able to calculate correlations")
                    else:
                        corrseries = correlate_response_with_dataframe(
                            merged_df,
                            param,
                            list(set(vectors_for_param_corr + [selected_vector])),
                        )
                        if corrseries.isnull().values.any():
                            corr_p_fig = empty_figure(
                                "Not able to calculate correlations"
                            )
                        else:
                            corr_p_fig = BarChart(
                                corrseries,
                                n_rows=15,
                                title=f"Correlations with {param}",
                                orientation="h",
                            ).figure
                            corr_p_fig = color_corr_bars(
                                corr_p_fig, selected_vector, color, options["opacity"]
                            )

            # Make scatter plot (lower left plot)
            if param is None:
                scatter_fig = empty_figure("No parameter selected.")
            else:
                # Create scatter plot of vector vs parameter
                scatterplot = ScatterPlot(
                    merged_df,
                    response=selected_vector,
                    param=param,
                    color=color,
                    title=f"{selected_vector} vs {param}",
                    plot_trendline=True,
                )
                scatterplot.update_color(
                    color, options["opacity"] if options is not None else 0.5
                )
                scatter_fig = scatterplot.figure

            # Make timeseries graph
            df_value_norm = self._parametermodel.get_real_and_value_df(
                ensemble, parameter=param, normalize=True
            )
            timeseries_fig = TimeSeriesFigure(
                dframe=merge_dataframes_on_realization(
                    vector_df[["DATE", "REAL", selected_vector]], df_value_norm
                ),
                visualization=visualization,
                vector=selected_vector,
                ensemble=ensemble,
                dateline=date
                if options is not None and options["show_dateline"]
                else None,
                historical_vector_df=self._vectormodel.get_historical_vector_df(
                    selected_vector, ensemble
                ),
                observations=self._observations[selected_vector]
                if options
                and options["show_observations"]
                and selected_vector in self._observations
                else {},
                color_col=param,
                line_shape_fallback=self._vectormodel.line_shape_fallback,
            ).figure

            return [timeseries_fig, scatter_fig, corr_v_fig, corr_p_fig]

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SLIDER
                ),
                "value",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SLIDER
                ),
                "max",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SLIDER
                ),
                "marks",
            ),
            Input(
                self.view_element(self.Ids.TIME_SERIES_CHART)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "clickData",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS,
                    ParamRespSelections.Ids.RESAMPLING_FREQUENCY_DROPDOWN,
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SELECTED
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SLIDER
                ),
                "max",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SLIDER
                ),
                "marks",
            ),
        )
        @callback_typecheck
        def _update_date_from_clickdata_or_resampling_freq(
            timeseries_clickdata: Union[None, dict],
            resampling_frequency: Frequency,
            datestr: str,
            state_maxvalue: int,
            state_marks: Dict,
        ) -> Tuple[int, int, Dict]:
            """Update date-slider from clickdata"""
            ctx = callback_context.triggered[0]["prop_id"]
            if self.Ids.TIME_SERIES_CHART.value in ctx:
                # The event is a click in the time series chart
                date = datetime_utils.from_str(
                    timeseries_clickdata.get("points", [{}])[0]["x"]
                    if timeseries_clickdata is not None
                    else datestr
                )
                if date not in self._vectormodel.dates:
                    date = self._vectormodel.get_closest_date(date)
                return self._vectormodel.dates.index(date), state_maxvalue, state_marks

            if ParamRespSelections.Ids.RESAMPLING_FREQUENCY_DROPDOWN.value in ctx:
                # The event is a change of resampling frequency
                date = datetime_utils.from_str(datestr)
                dates = self._vectormodel.get_dates(
                    resampling_frequency=resampling_frequency
                )
                self._vectormodel.set_dates(dates)
                if date not in dates:
                    date = self._vectormodel.get_closest_date(date)
                return (
                    self._vectormodel.dates.index(date),
                    len(dates) - 1,
                    get_slider_marks(dates),
                )

            raise PreventUpdate("Event not recognized.")

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.OPTIONS, ParamRespOptions.Ids.VECTOR_FILTER_STORE
                ),
                "data",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.OPTIONS, ParamRespOptions.Ids.SUBMIT_VECTOR_FILTER
                ),
                "style",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.OPTIONS, ParamRespOptions.Ids.SUBMIT_VECTOR_FILTER
                ),
                "n_clicks",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.OPTIONS, ParamRespOptions.Ids.VECTOR_FILTER
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.OPTIONS, ParamRespOptions.Ids.VECTOR_FILTER_STORE
                ),
                "data",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.OPTIONS, ParamRespOptions.Ids.SUBMIT_VECTOR_FILTER
                ),
                "style",
            ),
        )
        @callback_typecheck
        def _update_vector_filter_store_and_button_style(
            _n_click: Union[None, int],
            vector_filter: Union[None, str],
            stored: Union[None, str],
            style: Dict,
        ) -> Tuple[str, Dict]:
            """Update vector-filter-store if submit button is clicked and
            style of submit button"""
            ctx = callback_context.triggered[0]["prop_id"]
            button_click = "submit" in ctx
            insync = stored == vector_filter
            style["background-color"] = (
                "#E8E8E8" if insync or button_click else "#7393B3"
            )
            style["color"] = "#555" if insync or button_click else "#fff"
            return vector_filter if button_click else no_update, style

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SELECTED
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SLIDER
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_date(dateidx: int) -> str:
            """Update selected date from date-slider"""
            return datetime_utils.to_str(self._vectormodel.dates[dateidx])

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SELECTED_TEXT
                ),
                "children",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.DATE_SLIDER
                ),
                "drag_value",
            ),
            prevent_initial_call=True,
        )
        @callback_typecheck
        def _update_date_drag_value(dateidx: int) -> str:
            """Update selected date text on date-slider drag"""
            if dateidx >= len(self._vectormodel.dates):
                # This is not supposed to happen if callbacks are triggered
                # in the right order
                return datetime_utils.to_str(self._vectormodel.dates[-1])
            return datetime_utils.to_str(self._vectormodel.dates[dateidx])

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION,
                    ParamRespVizualisation.Ids.CHECKBOX_OPTIONS_STORE,
                ),
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION, ParamRespVizualisation.Ids.CHECKBOX_OPTIONS
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.OPTIONS, ParamRespOptions.Ids.AUTO_COMPUTE_CORRELATIONS
                ),
                "value",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION, ParamRespVizualisation.Ids.COLOR_SELECTOR
                ),
                "clickData",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION, ParamRespVizualisation.Ids.OPACITY_SELECTOR
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.VIZUALISATION,
                    ParamRespVizualisation.Ids.CHECKBOX_OPTIONS_STORE,
                ),
                "data",
            ),
        )
        @callback_typecheck
        def _update_plot_options(
            checkbox_options: List[str],
            autocompute_options: List[str],
            color_clickdata: Union[None, Dict[str, List[Dict[str, Any]]]],
            opacity: float,
            plot_options: Union[None, Dict[str, Any]],
        ) -> Union[None, Dict[str, Any]]:
            """Combine plot options in one dictionary"""
            ctx = callback_context.triggered[0]["prop_id"].split(".")[0]
            if plot_options is not None and not ctx:
                raise PreventUpdate
            if color_clickdata is not None:
                color = color_clickdata["points"][0]["marker.color"]
                if "rgb" in color:
                    color = rgba_to_hex(color)

            return {
                "show_dateline": "DateLine" in checkbox_options,
                "autocompute_corr": "AutoCompute" in autocompute_options,
                "color": None if color_clickdata is None else color,
                "opacity": opacity,
                "ctx": ctx,
                "show_observations": "Observations" in checkbox_options,
            }

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.VECTOR_SELECTOR
                ),
                "selectedTags",
            ),
            Input(
                self.view_element(self.Ids.PARAM_CORR_GRAPH)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        @callback_typecheck
        def _update_vectorlist(corr_param_clickdata: Union[None, dict]) -> List[str]:
            """Update the selected vector value from clickdata"""
            if corr_param_clickdata is None:
                raise PreventUpdate
            vector_selected = corr_param_clickdata.get("points", [{}])[0].get("y")
            return [vector_selected]

        @callback(
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.PARAMETER_SELECT
                ),
                "options",
            ),
            Output(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.PARAMETER_SELECT
                ),
                "value",
            ),
            Input(
                self.view_element(self.Ids.VECTOR_CORR_GRAPH)
                .component_unique_id(ParamRespViewElement.Ids.GRAPH)
                .to_string(),
                "clickData",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.ENSEMBLE
                ),
                "value",
            ),
            State(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.PARAMETER_SELECT
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_parameter_selected(
            corr_vector_clickdata: Union[None, dict],
            ensemble: str,
            selected_parameter: Union[None, str],
        ) -> tuple:
            """Update the selected parameter from clickdata, or when ensemble is changed"""
            ctx = callback_context.triggered[0]["prop_id"]
            if ctx == "." or corr_vector_clickdata is None:
                raise PreventUpdate
            parameters = self._parametermodel.pmodel.parameters_per_ensemble[ensemble]
            options = [{"label": i, "value": i} for i in parameters]
            if "vector-corr-graph" in ctx:
                return options, corr_vector_clickdata.get("points", [{}])[0].get("y")
            return (
                options,
                selected_parameter if selected_parameter in parameters else None,
            )

        @callback(
            Output(
                {
                    "id": self.settings_group_unique_id(
                        self.Ids.PARAMETER_FILTER,
                        ParamRespParameterFilter.Ids.PARAM_FILTER,
                    ),
                    "type": "ensemble-update",
                },
                "data",
            ),
            Input(
                self.settings_group_unique_id(
                    self.Ids.SELECTIONS, ParamRespSelections.Ids.ENSEMBLE
                ),
                "value",
            ),
        )
        @callback_typecheck
        def _update_parameter_filter_selection(ensemble: str) -> List[str]:
            """Update ensemble in parameter filter"""
            return [ensemble]


def color_corr_bars(
    figure: dict,
    selected_bar: str,
    color: str,
    opacity: float,
    color_selected: str = "#FF1243",
) -> Dict[str, Any]:
    """
    Set colors to the correlation plot bar,
    with separate color for the selected bar
    """
    if "data" in figure:
        figure["data"][0]["marker"] = {
            "color": [
                hex_to_rgba_str(color, opacity)
                if _bar != selected_bar
                else hex_to_rgba_str(color_selected, 0.8)
                for _bar in figure["data"][0]["y"]
            ],
            "line": {
                "color": [
                    color if _bar != selected_bar else color_selected
                    for _bar in figure["data"][0]["y"]
                ],
                "width": 1.2,
            },
        }
    return figure


def empty_figure(text: str = "No data available for figure") -> go.Figure:
    return go.Figure(
        layout={
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "plot_bgcolor": "white",
            "annotations": [
                {
                    "text": text,
                    "xref": "paper",
                    "yref": "paper",
                    "showarrow": False,
                    "font": {"size": 16},
                }
            ],
        }
    )


def get_slider_marks(dates: List[datetime.datetime]) -> Dict[int, Dict[str, Any]]:
    """Formats the marks parameter to the date slider"""
    return {
        idx: {
            "label": datetime_utils.to_str(dates[idx]),
            "style": {"white-space": "nowrap"},
        }
        for idx in [0, len(dates) - 1]
    }

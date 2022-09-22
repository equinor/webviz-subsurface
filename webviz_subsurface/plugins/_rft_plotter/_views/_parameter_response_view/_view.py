from typing import Any, Dict, List, Optional, Union

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ....._figures import BarChart, ScatterPlot
from ..._shared_view_element import GeneralViewElement
from ..._types import DepthType, LineType
from ..._utils import FormationFigure, RftPlotterDataModel, correlate
from ._settings import ParameterResponseSettings


class ParameterResponseView(ViewABC):
    class Ids(StrEnum):
        SETTINGS = "settings"
        FORMATION_PLOT = "formation-plot"
        CORR_BARCHART = "corr-barchart"
        CORR_BARCHART_FIGURE = "corr-barchart-figure"
        SCATTERPLOT = "scatterplot"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Parameter Response")
        self.datamodel = datamodel
        self.parameter_df = datamodel.param_model.dataframe

        self.add_settings_group(
            ParameterResponseSettings(self.datamodel), self.Ids.SETTINGS
        )

        first_column = self.add_column()
        first_column.add_view_element(GeneralViewElement(), self.Ids.CORR_BARCHART)
        first_column.add_view_element(GeneralViewElement(), self.Ids.SCATTERPLOT)
        second_column = self.add_column()
        second_column.add_view_element(GeneralViewElement(), self.Ids.FORMATION_PLOT)

        self._corr_barchart_figure_id = self.view_element(
            self.Ids.CORR_BARCHART
        ).register_component_unique_id(self.Ids.CORR_BARCHART_FIGURE)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.PARAM)
                .to_string(),
                "value",
            ),
            Input(self._corr_barchart_figure_id, "clickData"),
            State(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.CORRTYPE)
                .to_string(),
                "value",
            ),
            prevent_initial_call=True,
        )
        def _update_param_from_clickdata(
            corr_vector_clickdata: Union[None, dict],
            corrtype: str,
        ) -> str:
            """Update the selected parameter from clickdata"""
            if corr_vector_clickdata is None or corrtype == "param_vs_sim":
                raise PreventUpdate
            return corr_vector_clickdata.get("points", [{}])[0].get("y")

        @callback(
            Output(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.WELL)
                .to_string(),
                "value",
            ),
            Input(self._corr_barchart_figure_id, "clickData"),
            State(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.CORRTYPE)
                .to_string(),
                "value",
            ),
            prevent_initial_call=True,
        )
        def _update_selections_from_clickdata(
            corr_vector_clickdata: Union[None, dict],
            corrtype: str,
        ) -> str:
            """Update well, date and zone from clickdata"""
            if corr_vector_clickdata is None or corrtype == "sim_vs_param":
                raise PreventUpdate

            clickdata = corr_vector_clickdata.get("points", [{}])[0].get("y")
            ls_clickdata = clickdata.split()
            print("click dat ais: ", ls_clickdata)
            return ls_clickdata[0]

        @callback(
            Output(
                self.view_element(self.Ids.CORR_BARCHART)
                .component_unique_id(GeneralViewElement.Ids.CHART)
                .to_string(),
                "children",
            ),
            Output(
                self.view_element(self.Ids.SCATTERPLOT)
                .component_unique_id(GeneralViewElement.Ids.CHART)
                .to_string(),
                "children",
            ),
            Output(
                self.view_element(self.Ids.FORMATION_PLOT)
                .component_unique_id(GeneralViewElement.Ids.CHART)
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.WELL)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.DATE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.ZONE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.PARAM)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.CORRTYPE)
                .to_string(),
                "value",
            ),
            Input(
                {
                    "id": ParameterResponseSettings.Ids.PARAM_FILTER,
                    "type": "data-store",
                },
                "data",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(ParameterResponseSettings.Ids.DEPTHOPTION)
                .to_string(),
                "value",
            ),
        )
        # pylint: disable=too-many-locals
        @callback_typecheck
        def _update_paramresp_graphs(
            ensemble: str,
            well: str,
            date: str,
            zone: str,
            param: Optional[str],
            corrtype: str,
            real_filter: Dict[str, List[int]],
            depthtype: DepthType,
        ) -> List[Optional[Any]]:
            """Main callback to update the graphs:
            * ranked correlations bar chart
            * response vs param scatter plot
            * formations chart RFT pressure vs depth, colored by parameter value
            """
            (
                df,
                obs,
                obs_err,
                ens_params,
                ens_rfts,
            ) = self.datamodel.create_rft_and_param_pivot_table(
                ensemble=ensemble,
                well=well,
                date=date,
                zone=zone,
                reals=real_filter[ensemble],
                keep_all_rfts=(corrtype == "param_vs_sim"),
            )
            current_key = f"{well} {date} {zone}"

            if df is None:
                # This happens if the filtering criterias returns no data
                # Could f.ex happen when there are ensembles with different well names
                return ["No data matching the given filter criterias."] * 3
            if param is not None and param not in ens_params:
                # This happens if the selected parameter does not exist in the
                # selected ensemble
                return ["The selected parameter not valid for selected ensemble."] * 3
            if not ens_params:
                # This happens if there are multiple ensembles and one of the ensembles
                # doesn't have non-constant parameters.
                return ["The selected ensemble has no non-constant parameters."] * 3

            if corrtype == "sim_vs_param" or param is None:
                corrseries = correlate(df[ens_params + [current_key]], current_key)
                param = param if param is not None else corrseries.abs().idxmax()
                corr_title = f"{current_key} vs parameters"
                scatter_x, scatter_y, highlight_bar = param, current_key, param

            if corrtype == "param_vs_sim":
                corrseries = correlate(df[ens_rfts + [param]], param)
                corr_title = f"{param} vs simulated RFTs"
                scatter_x, scatter_y, highlight_bar = param, current_key, current_key

            # Correlation bar chart
            corrfig = BarChart(corrseries, n_rows=15, title=corr_title, orientation="h")
            corrfig.color_bars(highlight_bar, "#007079", 0.5)
            corr_graph = wcc.Graph(
                style={"height": "40vh"},
                config={"displayModeBar": False},
                figure=corrfig.figure,
                id=self._corr_barchart_figure_id,
            )

            # Scatter plot
            scatterplot = ScatterPlot(
                df, scatter_y, scatter_x, "#007079", f"{current_key} vs {param}"
            )
            scatterplot.add_vertical_line_with_error(
                obs,
                obs_err,
                df[param].min(),
                df[param].max(),
            )
            scatter_graph = (
                wcc.Graph(
                    style={"height": "40vh"},
                    config={"displayModeBar": False},
                    figure=scatterplot.figure,
                ),
            )

            # Formations plot
            formations_figure = FormationFigure(
                well=well,
                ertdf=self.datamodel.ertdatadf,
                enscolors=self.datamodel.enscolors,
                depthtype=depthtype,
                date=date,
                ensembles=[ensemble],
                reals=real_filter[ensemble],
                simdf=self.datamodel.simdf,
                obsdf=self.datamodel.obsdatadf,
            )

            if formations_figure.use_ertdf:
                return [
                    corr_graph,
                    scatter_graph,
                    f"Realization lines not available for depth option {depthtype}",
                ]

            if self.datamodel.formations is not None:
                formations_figure.add_formation(
                    self.datamodel.formationdf, fill_color=False
                )

            formations_figure.add_simulated_lines(LineType.REALIZATION)
            formations_figure.add_additional_observations()
            formations_figure.add_ert_observed()

            df_value_norm = self.datamodel.get_param_real_and_value_df(
                ensemble, parameter=param, normalize=True
            )
            formations_figure.color_by_param_value(df_value_norm, param)

            return [
                corr_graph,
                scatter_graph,
                wcc.Graph(
                    style={"height": "87vh"},
                    figure=formations_figure.figure,
                ),
            ]

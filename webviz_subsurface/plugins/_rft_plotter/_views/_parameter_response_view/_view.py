from typing import Any, Dict, List, Optional, Union

import webviz_core_components as wcc
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ....._figures import BarChart, ScatterPlot
from ..._reusable_view_element import GeneralViewElement
from ..._types import CorrType, DepthType, LineType
from ..._utils import FormationFigure, RftPlotterDataModel, correlate
from ._settings import Options, ParameterFilterSettings, Selections


class ParameterResponseView(ViewABC):
    class Ids(StrEnum):
        SELECTIONS = "selections"
        OPTIONS = "options"
        PARAMETER_FILTER = "parameter-filter"
        FORMATION_PLOT = "formation-plot"
        CORR_BARCHART = "corr-barchart"
        CORR_BARCHART_FIGURE = "corr-barchart-figure"
        SCATTERPLOT = "scatterplot"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Parameter Response")
        self._datamodel = datamodel
        self._parameter_df = datamodel.param_model.dataframe

        self.add_settings_group(Selections(self._datamodel), self.Ids.SELECTIONS)
        self.add_settings_group(Options(), self.Ids.OPTIONS)
        self.add_settings_group(
            ParameterFilterSettings(
                parameter_df=self._datamodel.param_model.dataframe,
                mc_ensembles=self._datamodel.param_model.mc_ensembles,
            ),
            self.Ids.PARAMETER_FILTER,
        )

        first_column = self.add_column()
        first_column.add_view_element(GeneralViewElement(), self.Ids.CORR_BARCHART)
        first_column.add_view_element(GeneralViewElement(), self.Ids.SCATTERPLOT)
        second_column = self.add_column()
        second_column.add_view_element(GeneralViewElement(), self.Ids.FORMATION_PLOT)

    def set_callbacks(self) -> None:

        corr_barchart_figure_id = self.view_element(
            self.Ids.CORR_BARCHART
        ).register_component_unique_id(self.Ids.CORR_BARCHART_FIGURE)

        @callback(
            Output(
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.PARAM)
                .to_string(),
                "value",
            ),
            Input(corr_barchart_figure_id, "clickData"),
            State(
                self.settings_group(self.Ids.OPTIONS)
                .component_unique_id(Options.Ids.CORRTYPE)
                .to_string(),
                "value",
            ),
            prevent_initial_call=True,
        )
        @callback_typecheck
        def _update_param_from_clickdata(
            corr_vector_clickdata: Union[None, dict],
            corrtype: CorrType,
        ) -> str:
            """Update the selected parameter from clickdata"""
            if corr_vector_clickdata is None or corrtype == CorrType.PARAM_VS_SIM:
                raise PreventUpdate
            return corr_vector_clickdata.get("points", [{}])[0].get("y")

        @callback(
            Output(
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.WELL)
                .to_string(),
                "value",
            ),
            Input(corr_barchart_figure_id, "clickData"),
            State(
                self.settings_group(self.Ids.OPTIONS)
                .component_unique_id(Options.Ids.CORRTYPE)
                .to_string(),
                "value",
            ),
            prevent_initial_call=True,
        )
        @callback_typecheck
        def _update_selections_from_clickdata(
            corr_vector_clickdata: Union[None, dict],
            corrtype: CorrType,
        ) -> str:
            """Update well, date and zone from clickdata"""
            if corr_vector_clickdata is None or corrtype == CorrType.SIM_VS_PARAM:
                raise PreventUpdate

            clickdata = corr_vector_clickdata.get("points", [{}])[0].get("y")
            ls_clickdata = clickdata.split()
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
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.WELL)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.DATE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.ZONE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.PARAM)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.OPTIONS)
                .component_unique_id(Options.Ids.CORRTYPE)
                .to_string(),
                "value",
            ),
            Input(
                {
                    "id": self.settings_group(self.Ids.PARAMETER_FILTER)
                    .component_unique_id(ParameterFilterSettings.Ids.PARAM_FILTER)
                    .to_string(),
                    "type": "data-store",
                },
                "data",
            ),
            Input(
                self.settings_group(self.Ids.OPTIONS)
                .component_unique_id(Options.Ids.DEPTHTYPE)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        # pylint: disable=too-many-locals
        def _update_paramresp_graphs(
            ensemble: str,
            well: str,
            date: str,
            zone: str,
            param: Optional[str],
            corrtype: CorrType,
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
            ) = self._datamodel.create_rft_and_param_pivot_table(
                ensemble=ensemble,
                well=well,
                date=date,
                zone=zone,
                reals=real_filter[ensemble],
                keep_all_rfts=(corrtype == CorrType.PARAM_VS_SIM),
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

            if corrtype == CorrType.SIM_VS_PARAM or param is None:
                corrseries = correlate(df[ens_params + [current_key]], current_key)
                param = param if param is not None else corrseries.abs().idxmax()
                corr_title = f"{current_key} vs parameters"
                scatter_x, scatter_y, highlight_bar = param, current_key, param

            if corrtype == CorrType.PARAM_VS_SIM:
                corrseries = correlate(df[ens_rfts + [param]], param)
                corr_title = f"{param} vs simulated RFTs"
                scatter_x, scatter_y, highlight_bar = param, current_key, current_key

            # Correlation bar chart
            corrfig = BarChart(corrseries, n_rows=15, title=corr_title, orientation="h")
            corrfig.color_bars(highlight_bar, "#007079", 0.5)
            corr_graph = wcc.Graph(
                style={"height": "40vh"},
                figure=corrfig.figure,
                id=corr_barchart_figure_id,
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
                    figure=scatterplot.figure,
                ),
            )

            # Formations plot
            formations_figure = FormationFigure(
                well=well,
                ertdf=self._datamodel.ertdatadf,
                enscolors=self._datamodel.enscolors,
                depthtype=depthtype,
                date=date,
                ensembles=[ensemble],
                reals=real_filter[ensemble],
                simdf=self._datamodel.simdf,
                obsdf=self._datamodel.obsdatadf,
            )

            if formations_figure.use_ertdf:
                return [
                    corr_graph,
                    scatter_graph,
                    f"Realization lines not available for depth option {depthtype}",
                ]

            if self._datamodel.formations is not None:
                formations_figure.add_formation(
                    self._datamodel.formationdf, fill_color=False
                )

            formations_figure.add_simulated_lines(LineType.REALIZATION)
            formations_figure.add_additional_observations()
            formations_figure.add_ert_observed()

            df_value_norm = self._datamodel.get_param_real_and_value_df(
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

        @callback(
            Output(
                {
                    "id": ParameterFilterSettings.Ids.PARAM_FILTER,
                    "type": "ensemble-update",
                },
                "data",
            ),
            Input(
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
        )
        def _update_parameter_filter_selection(ensemble: str) -> List[str]:
            """Update ensemble in parameter filter"""
            return [ensemble]

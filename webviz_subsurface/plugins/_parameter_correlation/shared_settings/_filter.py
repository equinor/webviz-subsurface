from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback, callback_context
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PlugInIDs
from ..view_elements import Graph
from ..views import ParameterPlot


class BothPlots(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        ENSEMBLE = "ensemble"

    def __init__(self, ensembles: dict) -> None:
        super().__init__("Ensemble in both plots")
        self.ensembles = ensembles

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(BothPlots.IDs.ENSEMBLE),
                label="",
                options=[{"label": k, "value": v} for k, v in self.ensembles.items()],
                value=list(self.ensembles.values())[0],
                multi=False,
                clearable=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.BothPlots.ENSEMBLE), "data"
            ),
            Input(
                self.component_unique_id(BothPlots.IDs.ENSEMBLE).to_string(), "value"
            ),
        )
        def _set_both_ensemble(ensemble: str) -> str:
            return ensemble


class Horizontal(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        PARAMETER = "parameter-horizontal"
        ENSEMBLE = "ensemble-horizontal"

    def __init__(self, ensembles: dict, p_cols: List, plot: ParameterPlot) -> None:
        super().__init__("Distribution plot on horizontal axis")
        self.ensembles = ensembles
        self.p_cols = p_cols
        self.plot = plot

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Horizontal.IDs.PARAMETER),
                label="Parameter",
                options=[{"label": p, "value": p} for p in self.p_cols],
                value=self.p_cols[0],
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Horizontal.IDs.ENSEMBLE),
                label="Ensemble",
                options=[{"label": k, "value": v} for k, v in self.ensembles.items()],
                value=list(self.ensembles.values())[0],
                multi=False,
                clearable=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Horizontal.PARAMETER), "data"
            ),
            Output(
                self.component_unique_id(Horizontal.IDs.PARAMETER).to_string(), "value"
            ),
            Input(
                self.component_unique_id(Horizontal.IDs.PARAMETER).to_string(), "value"
            ),
            Input(
                self.plot.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        def _set_horizontal_parameter(parameter: str, cell_data: dict) -> str:
            if (
                callback_context.triggered_id
                == self.component_unique_id(Horizontal.IDs.PARAMETER).to_string()
                or cell_data is None
            ):
                return parameter, parameter
            else:
                return cell_data["points"][0]["x"], cell_data["points"][0]["x"]

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Horizontal.ENSEMBLE), "data"
            ),
            Input(
                self.component_unique_id(Horizontal.IDs.ENSEMBLE).to_string(), "value"
            ),
        )
        def _set_horizontal_ensemble(ensemble: str) -> str:
            return ensemble


class Vertical(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        PARAMETER = "parameter-vertical"
        ENSEMBLE = "ensemble-vertical"

    def __init__(self, ensembles: dict, p_cols: List, plot: ParameterPlot) -> None:
        super().__init__("Distribution plot on vertical axis")
        self.ensembles = ensembles
        self.p_cols = p_cols
        self.plot = plot

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Vertical.IDs.PARAMETER),
                label="Parameter",
                options=[{"label": p, "value": p} for p in self.p_cols],
                value=self.p_cols[0],
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Vertical.IDs.ENSEMBLE),
                label="Ensemble",
                options=[{"label": k, "value": v} for k, v in self.ensembles.items()],
                value=list(self.ensembles.values())[0],
                multi=False,
                clearable=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Vertical.PARAMETER), "data"
            ),
            Output(
                self.component_unique_id(Vertical.IDs.PARAMETER).to_string(), "value"
            ),
            Input(
                self.component_unique_id(Vertical.IDs.PARAMETER).to_string(), "value"
            ),
            Input(
                self.plot.view_element(ParameterPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "clickData",
            ),
        )
        def _set_vertical_parameter(parameter: str, cell_data: dict) -> str:
            if (
                callback_context.triggered_id
                == self.component_unique_id(Vertical.IDs.PARAMETER).to_string()
                or cell_data is None
            ):
                return parameter, parameter
            else:
                return cell_data["points"][0]["y"], cell_data["points"][0]["y"]

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Vertical.ENSEMBLE), "data"
            ),
            Input(self.component_unique_id(Vertical.IDs.ENSEMBLE).to_string(), "value"),
        )
        def _set_vertical_ensemble(ensemble: str) -> str:
            return ensemble


class Options(SettingsGroupABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        COLOR_BY = "color-by"
        SHOW_SCATTER = "show-scatter"

    def __init__(self, p_cols: List) -> None:
        super().__init__("Distribution plot optrions")
        self.p_cols = p_cols

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Options.IDs.COLOR_BY),
                label="Color by",
                options=[{"label": p, "value": p} for p in self.p_cols],
                value=self.p_cols[0],
                multi=False,
                clearable=True,
            ),
            wcc.Checklist(
                id=self.register_component_unique_id(Options.IDs.SHOW_SCATTER),
                style={"padding": "5px"},
                options=[
                    {
                        "label": "Show scatterplot density",
                        "value": "density",
                    }
                ],
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Options.COLOR_BY), "data"),
            Input(self.component_unique_id(Options.IDs.COLOR_BY).to_string(), "value"),
        )
        def _set_option_color_by(parameter: str) -> str:
            return parameter

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Options.SHOW_SCATTER), "data"
            ),
            Input(
                self.component_unique_id(Options.IDs.SHOW_SCATTER).to_string(), "value"
            ),
        )
        def _set_optrion_scatter(scatter: str) -> str:
            return scatter

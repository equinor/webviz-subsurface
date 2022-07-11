from typing import List, Tuple, Dict

from dash import callback, Input, Output
from dash.development.base_component import Component
import pandas as pd
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from .._plugin_ids import PlugInIDs


class Selectors(SettingsGroupABC):
    """Settings group for Selectors"""

    class IDs:
        # pylint: disable=too-few-public-methods
        SATURATION_AXIS = "saturation-axis"
        COLOR_BY = "color-by"
        ENSEMBLES = "ensembles"
        CURVES = "curves"
        SATNUM = "satnum"

    def __init__(self, relperm_df: pd.DataFrame, sat_axes_maps) -> None:
        super().__init__("Selectors")
        self.satfunc = relperm_df
        self.sat_axes_maps = sat_axes_maps

    @property
    def sat_axes(self) -> List[str]:
        """List of all possible saturation axes in dataframe"""
        return [sat for sat in self.sat_axes_maps if sat in self.satfunc.columns]

    @property
    def ensembles(self) -> List[str]:
        """List of all possible ensembles in dataframe"""
        return list(self.satfunc["ENSEMBLE"].unique())

    @property
    def satnums(self) -> List[str]:
        """List of all possible satnums in dataframe"""
        return list(self.satfunc["SATNUM"].unique())

    @property
    def color_options(self) -> List[str]:
        """Options to color by"""
        return ["ENSEMBLE", "CURVE", "SATNUM"]

    # Defining all setting elements in Selectors-section
    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(Selectors.IDs.SATURATION_AXIS),
                label="Saturation axis",
                options=[{"label": i, "value": i} for i in (self.sat_axes)],
                value=self.sat_axes[0],
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Selectors.IDs.COLOR_BY),
                label="Color by",
                options=[
                    {"label": i.lower().capitalize(), "value": i}
                    for i in (self.color_options)
                ],
                value=self.color_options[0],
                multi=False,
                clearable=False,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Selectors.IDs.ENSEMBLES),
                label="Ensembles",
                options=[{"label": i, "value": i} for i in (self.ensembles)],
                value=self.ensembles[0],
                multi=True,
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Selectors.IDs.CURVES),
                label="Curves",
                clearable=False,
                multi=True,
                value=self.sat_axes_maps[self.sat_axes[0]],
            ),
            wcc.Dropdown(
                id=self.register_component_unique_id(Selectors.IDs.SATNUM),
                label="Satnum",
                options=[{"label": i, "value": i} for i in (self.satnums)],
                value=self.ensembles[0],
                multi=False,
                clearable=False,
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATURATION_AXIS),
                "data",
            ),
            Input(
                self.component_unique_id(Selectors.IDs.SATURATION_AXIS).to_string(),
                "value",
            ),
        )
        def _set_saturation_axis(saturation_axis: List[str]) -> List[str]:
            return saturation_axis

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.COLOR_BY), "data"
            ),
            Input(
                self.component_unique_id(Selectors.IDs.COLOR_BY).to_string(),
                "value",
            ),
        )
        def _set_color_by(color_by: List[str]) -> List[str]:
            return color_by

        @callback(
            Output(
                self.component_unique_id(Selectors.IDs.ENSEMBLES).to_string(), "multi"
            ),
            Output(
                self.component_unique_id(Selectors.IDs.ENSEMBLES).to_string(), "value"
            ),
            Input(
                self.component_unique_id(Selectors.IDs.COLOR_BY).to_string(),
                "value",
            ),
        )
        def _set_ensembles_interaction(color_by: str) -> Tuple[bool, List[str]]:
            """If ensemble is selected as color by, set the ensemble
            selector to allow multiple selections, else use stored_ensemble
            """
            if color_by == "ENSEMBLE":
                return [True, self.ensembles]
            return [False, self.ensembles[0]]

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.ENSAMBLES), "data"
            ),
            Input(
                self.component_unique_id(Selectors.IDs.ENSEMBLES).to_string(),
                "value",
            ),
        )
        def _set_ensembles(stored_ensemble: List[str]) -> List[str]:
            return stored_ensemble

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Selectors.CURVES), "data"),
            Input(
                self.component_unique_id(Selectors.IDs.CURVES).to_string(),
                "value",
            ),
        )
        def _set_curves(curves: str) -> List[str]:
            return curves

        @callback(
            Output(self.component_unique_id(Selectors.IDs.CURVES).to_string(), "value"),
            Output(
                self.component_unique_id(Selectors.IDs.CURVES).to_string(), "options"
            ),
            Input(
                self.component_unique_id(Selectors.IDs.SATURATION_AXIS).to_string(),
                "value",
            ),
        )
        def _set_curves_interactions(sataxis: str) -> Tuple[List[str], List[Dict]]:
            return (
                self.sat_axes_maps[sataxis],
                [
                    {
                        "label": i,
                        "value": i,
                    }
                    for i in self.sat_axes_maps[sataxis]
                ],
            )

        @callback(
            Output(self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATNUM), "data"),
            Input(
                self.component_unique_id(Selectors.IDs.SATNUM).to_string(),
                "value",
            ),
        )
        def _set_saturation_axis(stored_satnum: List[str]) -> List[str]:
            return stored_satnum

        @callback(
            Output(self.component_unique_id(Selectors.IDs.SATNUM).to_string(), "multi"),
            Output(self.component_unique_id(Selectors.IDs.SATNUM).to_string(), "value"),
            Input(
                self.component_unique_id(Selectors.IDs.COLOR_BY).to_string(),
                "value",
            ),
        )
        def _set_saturation_axis_interactions(color_by: str) -> Tuple[bool, List[str]]:
            """If satnum is selected as color by, set the satnum
            selector to allow multiple selections, else use stored_satnum
            """
            if color_by == "SATNUM":
                return [True, self.satnums]

            return [
                False,
                self.satnums[0],
            ]


class Visualization(SettingsGroupABC):
    """Settings group for Visualizations"""

    class IDs:
        # pylint: disable=too-few-public-methods
        LINE_TRACES = "line-traces"
        Y_AXIS = "y-axis"

    def __init__(self) -> None:
        super().__init__("Visualization")

    # Defining all setting elements in Visualization-section
    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(Visualization.IDs.LINE_TRACES),
                label="Line traces",
                options=[
                    {
                        "label": "Individual realizations",
                        "value": "individual-realizations",
                    },
                    {"label": "Satatistical fanchart", "value": "statistical-fanchart"},
                ],
                value="individual-realizations",
            ),
            wcc.RadioItems(
                id=self.register_component_unique_id(Visualization.IDs.Y_AXIS),
                label="Y-axis",
                options=[
                    {"label": "Linear", "value": "linear"},
                    {"label": "Log", "value": "log"},
                ],
                value="linear",
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Visualization.LINE_TRACES),
                "data",
            ),
            Input(
                self.component_unique_id(Visualization.IDs.LINE_TRACES).to_string(),
                "value",
            ),
        )
        def _set_line_traces(line_traces: List[str]) -> List[str]:
            return line_traces

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Visualization.Y_AXIS),
                "data",
            ),
            Input(
                self.component_unique_id(Visualization.IDs.Y_AXIS).to_string(),
                "value",
            ),
        )
        def _set_y_axis(y_axis: List[str]) -> List[str]:
            return y_axis


class SCALRecommendation(SettingsGroupABC):
    """Settings group for SCAL Recomendations"""

    class IDs:
        # pylint: disable=too-few-public-methods
        SHOW_SCAL = "show-scal"

    def __init__(self) -> None:
        super().__init__("SCAL Recommendation")

    # Defining SCAL recomendation setting element
    def layout(self) -> List[Component]:
        return [
            wcc.Checklist(
                id=self.register_component_unique_id(SCALRecommendation.IDs.SHOW_SCAL),
                label="",
                options=[
                    {
                        "label": "Show SCAL",
                        "value": "show_scal",
                    },
                ],
                value="",
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.SCALRecomendation.SHOW_SCAL),
                "data",
            ),
            Input(
                self.component_unique_id(SCALRecommendation.IDs.SHOW_SCAL).to_string(),
                "value",
            ),
        )
        def _set_scal_recommendation(scal_recommendation: List[str]) -> str:
            return scal_recommendation

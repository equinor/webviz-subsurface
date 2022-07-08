from typing import List, Tuple, Dict

from dash import callback, Input, Output, State
from dash.development.base_component import Component
import pandas as pd
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from .._plugin_ids import PlugInIDs

class Filter(SettingsGroupABC):
    """
    Added by MoNezhadali 06.22
    """
    def __init__(self, relperm_df: pd.DataFrame) -> None:
            super().__init__("Filter")
    class Ids:
        class Selectors:
            SATURATION_AXIS="saturation-axis"
            COLOR_BY="color-by"
            ENSEMBLES="ensembles"
            CURVES="curves"
            SATNUM="satnum"
        class Visualization:
            LINE_TRACES="line-traces"
            Y_AXIS="y-axis"
        class SCALRecommendation:
            SHOW_SCAL="show-scal"

        ## todo: the selectors will be defined here after getting to know the data

class Selectors(SettingsGroupABC):
    def __init__(self, relperm_df: pd.DataFrame,plotly_theme,sat_axes_maps) -> None:
        super().__init__("Selectors")
        self.satfunc=relperm_df
        self.plotly_theme = plotly_theme
        self.sat_axes_maps=sat_axes_maps

    @property
    def sat_axes(self):
        """List of all possible saturation axes in dataframe"""
        return [sat for sat in self.sat_axes_maps if sat in self.satfunc.columns]

    @property
    def ensembles(self):
        return list(self.satfunc["ENSEMBLE"].unique())

    @property
    def satnums(self):
        return list(self.satfunc["SATNUM"].unique())

    @property
    def color_options(self):
        """Options to color by"""
        return ["ENSEMBLE", "CURVE", "SATNUM"]

    @property
    def ens_colors(self):
        return {
            ens: self.plotly_theme["layout"]["colorway"][self.ensembles.index(ens)]
            for ens in self.ensembles
        }

    @property
    def satnum_colors(self):
        return {
            satnum: self.plotly_theme["layout"]["colorway"][self.satnums.index(satnum)]
            for satnum in self.satnums
        }

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filter.Ids.Selectors.SATURATION_AXIS),
                label="Saturation axis",
                options=[{"label":i, "value":i} for i in (self.sat_axes)],
                value=self.sat_axes[0],
                multi=False,
                size=1,
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filter.Ids.Selectors.COLOR_BY),
                label="Color by",
                options=[{"label":i, "value":i} for i in (self.color_options)],
                value=self.color_options[0],
                multi=False,
                size=1,
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filter.Ids.Selectors.ENSEMBLES),
                label="Ensembles",
                options=[{"label":i, "value":i} for i in (self.ensembles)],
                value=self.ensembles[0],
                multi=True,
                size=min(5,len(self.ensembles)),
            ),
            # This needs to be checked
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filter.Ids.Selectors.CURVES),
                label="Curves",
                options=[{"label":i, "value":i} for i in (self.sat_axes_maps["SW"])],
                value=self.color_options[0],
                multi=False,
                size=1,
            ),
            wcc.SelectWithLabel(
                id=self.register_component_unique_id(Filter.Ids.Selectors.SATNUM),
                label="Satnum",
                options=[{"label":i, "value":i} for i in (self.satnums)],
                value=self.ensembles[0],
                multi=True,
                size=min(5,len(self.ensembles)),
            ),
        ]
    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATURATION_AXIS),"data"
            ),
            Input(
                self.component_unique_id(Filter.Ids.Selectors.SATURATION_AXIS).to_string(), "value",
            ),
        )
        def _set_saturation_axis(saturation_axis: List[str]) -> List[str]:
            return saturation_axis
        
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.COLOR_BY),"data"
            ),
            Input(
                self.component_unique_id(Filter.Ids.Selectors.COLOR_BY).to_string(), "value",
            ),
        )
        def _set_color_by(color_by: List[str]) -> List[str]:
            return color_by
        
        @callback(
            Output(
                self.component_unique_id(Filter.Ids.Selectors.ENSEMBLES).to_string(),"multi"
            ),
            Output(
                self.component_unique_id(Filter.Ids.Selectors.ENSEMBLES).to_string(),"value"
            ),
            Input(
                self.component_unique_id(Filter.Ids.Selectors.COLOR_BY).to_string(), "value",
            ),
        )
        def _set_ensembles_interaction(color_by:str) -> Tuple[bool, List[str]]:
            if color_by=="ENSEMBLE":
                return [True, self.ensembles]
            return [False, self.ensembles[0]]
        
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.ENSAMBLES),"data"
            ),
            Input(
                self.component_unique_id(Filter.Ids.Selectors.ENSEMBLES).to_string(), "value",
            ), 
        )
        def _set_ensembles(stored_ensemble: List[str]) -> List[str]:
            return stored_ensemble

        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.CURVES),"data"
            ),
            Input(
                self.component_unique_id(Filter.Ids.Selectors.CURVES).to_string(), "value",
            ),
        )
        def _set_curves(curves: str) -> List[str]:
            return curves

        @callback(
            Output(
                self.component_unique_id(Filter.Ids.Selectors.CURVES).to_string(),"value"
            ),
            Output(
                self.component_unique_id(Filter.Ids.Selectors.CURVES).to_string(),"options"
            ),
            Input(
                self.component_unique_id(Filter.Ids.Selectors.SATURATION_AXIS).to_string(), "value",
            ),
        )
        def _set_curves_interactions(sataxis: str) -> Tuple[List[str],List[Dict]]:
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
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATNUM),"data"
            ),
            Input(
                self.component_unique_id(Filter.Ids.Selectors.SATNUM).to_string(), "value",
            ),
        )
        def _set_saturation_axis(stored_satnum: List[str]) -> List[str]:
            return stored_satnum
        
        @callback(
            Output(
                self.component_unique_id(Filter.Ids.Selectors.SATNUM).to_string(),"multi"
            ),
            Output(
                self.component_unique_id(Filter.Ids.Selectors.SATNUM).to_string(),"value"
            ),
            Input(
                self.component_unique_id(Filter.Ids.Selectors.COLOR_BY).to_string(), "value",
            ),
        )
        def _set_saturation_axis_interactions(color_by: str) -> Tuple[bool, List[str]]:
            if color_by == "SATNUM":
                return [True, self.satnums]

            return [
                False, self.satnums[0],
            ]
            
        
class Visualization(SettingsGroupABC):
    def __init__(self, relperm_df: pd.DataFrame) -> None:
        super().__init__("Visualization")
    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(Filter.Ids.Visualization.LINE_TRACES),
                label="Line traces",
                options=[
                    {"label":"Individual realization","value":"individual-realization"},
                    {"label":"Satatistical fanchart", "value":"statistical-fanchart"},
                    ],
                value="statistical-fanchart",
            ),
            wcc.RadioItems(
                id=self.register_component_unique_id(Filter.Ids.Visualization.Y_AXIS),
                label="Y-axis",
                options=[
                    {"label":"Linear","value":"linear"},
                    {"label":"Log", "value":"log"},
                    ],
                value="linear",
            ),
        ]
    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Visualization.LINE_TRACES), "data" # Check here might be value
            ),
            Input(
                self.component_unique_id(Filter.Ids.Visualization.LINE_TRACES).to_string(), "value",
            ),
        )
        def _set_line_traces(line_traces: List[str]) -> List[str]:
            return line_traces
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.Visualization.Y_AXIS), "data" # Check here might be value
            ),
            Input(
                self.component_unique_id(Filter.Ids.Visualization.Y_AXIS).to_string(), "value",
            ),
        )
        def _set_y_axis(y_axis: List[str]) -> List[str]:
            return y_axis

class Scal_recommendation(SettingsGroupABC):
    def __init__(self, relperm_df: pd.DataFrame) -> None:
        super().__init__("SCAL Recommendation")
    '''
    def __init__(self, rel_perm_df: pd.DataFrame) -> None:
        self.super().__init__("SCAL recommendation")
    '''
    def layout(self) -> List[Component]:
        return [
            wcc.Checklist(
                id=self.register_component_unique_id(Filter.Ids.SCALRecommendation.SHOW_SCAL),
                label="",
                options=[
                    {
                        "label": "Show SCAL",
                        "value": "show_scal",
                    },
                ]
            ),
        ]
    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PlugInIDs.Stores.SCALRecomendation.SHOW_SCAL), "data" # Check here might be value
            ),
            Input(
                self.component_unique_id(Filter.Ids.SCALRecommendation.SHOW_SCAL).to_string(), "value",
            ),
        )
        def _set_scal_recommendation(scal_recommendation: List[str]) -> List[str]:
            return scal_recommendation
    
    
    
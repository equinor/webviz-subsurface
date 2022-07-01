from typing import List

from dash import callback, Input, Output
from dash.development.base_component import Component
import pandas as pd
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from .._plugin_ids import PlugInIDs

class Filter(SettingsGroupABC):
    """
    Added by MoNezhadali 06.22
    """
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

    class Selectors:
        def __init__(self, rel_perm_df: pd.DataFrame) -> None:
            self.super().__init__("Selectors")

        def layout(self) -> List(Component):
            return [
                wcc.SelectWithLabel(
                    id=self.register_component_unique_id(Filter.Ids.Selectors.SATURATION_AXIS),
                    label="Saturation axis",
                    options=[{"label":i, "value":i} for i in range(self.sat_axes)],
                    value=self.sat_axes[0],
                    multi=False,
                    size=1,
                ),
                wcc.SelectWithLabel(
                    id=self.register_component_unique_id(Filter.Ids.Selectors.COLOR_BY),
                    label="Color by",
                    options=[{"label":i, "value":i} for i in range(self.color_options)],
                    value=self.color_options[0],
                    multi=False,
                    size=1,
                ),
                wcc.SelectWithLabel(
                    id=self.register_component_unique_id(Filter.Ids.Selectors.ENSEMBLES),
                    label="Ensembles",
                    options=[{"label":i, "value":i} for i in range(self.ensembles)],
                    value=self.ensembles[0],
                    multi=True,
                    size=min(5,len(self.ensembles)),
                ),
                # This needs to be checked
                wcc.SelectWithLabel(
                    id=self.register_component_unique_id(Filter.Ids.Selectors.CURVES),
                    label="Curves",
                    options=[{"label":i, "value":i} for i in range(self.curves)],
                    value=self.color_options[0],
                    multi=False,
                    size=1,
                ),
                wcc.SelectWithLabel(
                    id=self.register_component_unique_id(Filter.Ids.Selectors.SATNUM),
                    label="Satnum",
                    options=[{"label":i, "value":i} for i in range(self.satnums)],
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
                    self.get_store_unique_id(PlugInIDs.Stores.Selectors.ENSAMBLES),"data"
                ),
                Input(
                    self.component_unique_id(Filter.Ids.Selectors.ENSEMBLES).to_string(), "value",
                ),
            )
            def _set_ensembles(ensembles: List[str]) -> List[str]:
                return ensembles

            @callback(
                Output(
                    self.get_store_unique_id(PlugInIDs.Stores.Selectors.CURVES),"data"
                ),
                Input(
                    self.component_unique_id(Filter.Ids.Selectors.CURVES).to_string(), "value",
                ),
            )
            def _set_curves(curves: List[str]) -> List[str]:
                return curves
            
            @callback(
                Output(
                    self.get_store_unique_id(PlugInIDs.Stores.Selectors.SATNUM),"data"
                ),
                Input(
                    self.component_unique_id(Filter.Ids.Selectors.SATNUM).to_string(), "value",
                ),
            )
            def _set_saturation_axis(satnum: List[str]) -> List[str]:
                return satnum
            
        
    class Visualization:
        def __init__(self, rel_perm_df: pd.DataFrame) -> None:
            self.super().__init__("Visualization")
        def layout(self) -> List(Component):
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
            

    class Scal_recommendation:
        def __init__(self, rel_perm_df: pd.DataFrame) -> None:
            self.super().__init__("SCAL recommendation")
        def layout(self) -> List(Component):
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
            def _set_line_traces(line_traces: List[str]) -> List[str]:
                return line_traces
        
    
    
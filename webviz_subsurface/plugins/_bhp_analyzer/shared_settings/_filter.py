from typing import List, Dict
from dash.development.base_component import Component
from dash import callback, Input, Output

import pandas as pd
from typing import List
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from .._plugin_ids import PluginIds


class Filter(SettingsGroupABC):


    class Ids:
        
        ENSEMBLE = "ensemble"
        WELLS = "wells"
        MAX_NUMBER_OF_WELLS_SLIDER = "max-number-of-wells-slider"
        SORT_BY = "sort-by"
        ASCENDING_DESCENDING = "ascending-descending"
        PLOT_TYPE = "plot-type"


    def __init__(self, bhp_df: pd.DataFrame) -> None:
        super().__init__("Filter")

        self.bhp_df = bhp_df



    
    @property
    def ensembles(self) -> List[str]:
        return list(self.bhp_df["ENSEMBLE"].unique())

    @property
    def wells(self) -> List[set]:
        return sorted(
            list(set(col[5:] for col in self.bhp_df.columns if col.startswith("WBHP:")))
        )

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                            label="Ensemble",
                            id=self.register_component_unique_id(Filter.Ids.ENSEMBLE),
                            options=[{"label": i, "value": i} for i in self.ensembles],
                            value=self.ensembles[0],
                            clearable=False,
                            multi=False,
                        ),
            wcc.Dropdown(
                            label="Plot type",
                            id=self.register_component_unique_id(Filter.Ids.PLOT_TYPE),
                            options=[
                                {"label": i, "value": i}
                                for i in [
                                    "Fan chart",
                                    "Bar chart",
                                    "Line chart",
                                ]
                            ],
                            clearable=False,
                            value="Fan chart",
                        ),
            wcc.RadioItems(
                            vertical=False,
                            id=self.register_component_unique_id(Filter.Ids.ASCENDING_DESCENDING),
                            options=[
                                {"label": "Ascending", "value": True},
                                {"label": "Descending", "value": False},
                            ],
                            value=True,
                            labelStyle={"display": "inline-block"},
                        ),
            wcc.Slider(
                            label="Max number of wells in plot",
                            id=self.register_component_unique_id(Filter.Ids.MAX_NUMBER_OF_WELLS_SLIDER),
                            min=1,
                            max=len(self.wells),
                            step=1,
                            value=min(10, len(self.wells)),
                            marks={1: 1, len(self.wells): len(self.wells)},
                        ),
            wcc.SelectWithLabel(
                            label="Wells",
                            id=self.register_component_unique_id(Filter.Ids.WELLS),
                            options=[{"label": i, "value": i} for i in self.wells],
                            size=min([len(self.wells), 20]),
                            value=self.wells,
                        ),
            
            
        ]

#    def set_callbacks(self) -> None:
        
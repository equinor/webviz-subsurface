from typing import Dict, List

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds


class Filter(SettingsGroupABC):
    class Ids(str):
        ENSEMBLE = "ensemble"
        WELLS = "wells"
        MAX_NUMBER_OF_WELLS_SLIDER = "max-number-of-wells-slider"
        SORT_BY = "sort-by"
        ASCENDING_DESCENDING = "ascending-descending"

    def __init__(self, bhp_df: pd.DataFrame) -> None:
        super().__init__("Filter")

        self.bhp_df = bhp_df

    @property
    def ensembles(self) -> List[str]:
        return list(self.bhp_df["ENSEMBLE"].unique())

    @property
    def label_map(self) -> Dict[str, str]:
        return {
            "Mean": "mean",
            "Count (data points)": "count",
            "Stddev": "std",
            "Minimum": "min",
            "Maximum": "max",
            "P10 (high)": "high_p10",
            "P50": "p50",
            "P90 (low)": "low_p90",
        }

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
                label="Sort by",
                id=self.register_component_unique_id(Filter.Ids.SORT_BY),
                options=[
                    {"label": key, "value": value}
                    for key, value in self.label_map.items()
                ],
                clearable=False,
                value="low_p90",
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
                id=self.register_component_unique_id(
                    Filter.Ids.MAX_NUMBER_OF_WELLS_SLIDER
                ),
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

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLE), "data"
            ),
            Input(self.component_unique_id(Filter.Ids.ENSEMBLE).to_string(), "value"),
        )
        def _set_ensembles(selected_ensemble: str) -> str:
            return selected_ensemble

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_SORT_BY), "data"),
            Input(self.component_unique_id(Filter.Ids.SORT_BY).to_string(), "value"),
        )
        def _set_sort_by(selected_sort_by: List[str]) -> List[str]:
            return selected_sort_by

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.SELECTED_ASCENDING_DESCENDING
                ),
                "data",
            ),
            Input(
                self.component_unique_id(Filter.Ids.ASCENDING_DESCENDING).to_string(),
                "value",
            ),
        )
        def _set_ascending_descending(selected_ascending_descending: str) -> str:
            return selected_ascending_descending

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_MAX_NUMBER_OF_WELLS),
                "data",
            ),
            Input(
                self.component_unique_id(
                    Filter.Ids.MAX_NUMBER_OF_WELLS_SLIDER
                ).to_string(),
                "value",
            ),
        )
        def _set_max_number_of_wells(
            max_number_of_wells_slider: List[int],
        ) -> List[int]:
            return max_number_of_wells_slider

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_WELLS), "data"),
            Input(self.component_unique_id(Filter.Ids.WELLS).to_string(), "value"),
        )
        def _set_wells(selected_wells: List[str]) -> List[str]:
            if selected_wells == []:
                raise PreventUpdate
            return selected_wells


# ADD SELECT STATISTICS
class ViewSettings(SettingsGroupABC):
    class Ids(StrEnum):
        SELECT_STATISTICS = "select-statistics"

    def __init__(self) -> None:
        super().__init__("View Settings")

    @property
    def label_map(self) -> Dict[str, str]:
        return {
            "Mean": "mean",
            "Count (data points)": "count",
            "Stddev": "std",
            "Minimum": "min",
            "Maximum": "max",
            "P10 (high)": "high_p10",
            "P50": "p50",
            "P90 (low)": "low_p90",
        }

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Select statistics",
                id=self.register_component_unique_id(
                    ViewSettings.Ids.SELECT_STATISTICS
                ),
                options=[
                    {"label": key, "value": value}
                    for key, value in self.label_map.items()
                ],
                size=8,
                value=["min", "low_p90", "mean", "high_p10", "max"],
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_STATISTICS), "data"
            ),
            Input(
                self.component_unique_id(
                    ViewSettings.Ids.SELECT_STATISTICS
                ).to_string(),
                "value",
            ),
        )
        def _set_select_statistics(selected_statistics: List[str]) -> List[str]:
            return selected_statistics

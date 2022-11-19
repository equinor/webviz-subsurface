from datetime import datetime
from typing import List

import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC

from .._plugin_ids import PluginIds


class Filter(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        ENSEMBLE_SELECTOR = "ensemble-selector"
        DATE_SELECTOR = "date-selector"
        PHASE_SELECTOR = "phase-selector"
        WELL_SELECTOR = "well-selector"
        COMBINE_WELL_AND_COLLECTION_AS = "combine-well-and-collection-as"
        WELL_COLLECTION_SELECTOR = "well-collection-selector"
        REALIZATION_SELECTOR = "realization-selector"

        FIG_LAYOUT_HEIGHT = "fig-layout-height"

    def __init__(
        self,
        ensemble_names: List[str],
        dates: List[datetime],
        phases: List[str],
        wells: List[str],
        realizations: List[int],
        all_well_collection_names: List[str],
    ) -> None:
        super().__init__("Filter")

        self.ensemble_names = ensemble_names
        self.dates = dates
        self.phases = phases
        self.wells = wells
        self.realizations = realizations
        self.all_well_collection_names = all_well_collection_names

    def layout(self) -> List[Component]:
        return [
            wcc.Checklist(
                label="Ensemble selector",
                id=self.register_component_unique_id(Filter.Ids.ENSEMBLE_SELECTOR),
                options=[{"label": ens, "value": ens} for ens in self.ensemble_names],
                value=self.ensemble_names[:2],
                vertical=False,
            ),
            wcc.SelectWithLabel(
                label="Date selector",
                id=self.register_component_unique_id(Filter.Ids.DATE_SELECTOR),
                options=[
                    {
                        "label": _date.strftime("%Y-%m-%d"),
                        "value": str(_date),
                    }
                    for _date in self.dates
                ],
                value=[str(self.dates[-1])],
                size=min([len(self.dates), 5]),
            ),
            wcc.SelectWithLabel(
                label="Phase selector",
                id=self.register_component_unique_id(Filter.Ids.PHASE_SELECTOR),
                options=[{"label": phase, "value": phase} for phase in self.phases],
                value=self.phases,
                size=min([len(self.phases), 3]),
            ),
            wcc.SelectWithLabel(
                label="Well selector",
                id=self.register_component_unique_id(Filter.Ids.WELL_SELECTOR),
                options=[{"label": well, "value": well} for well in self.wells],
                value=self.wells,
                size=min([len(self.wells), 9]),
            ),
            wcc.RadioItems(
                label="Combine wells and collections as",
                id=self.register_component_unique_id(
                    Filter.Ids.COMBINE_WELL_AND_COLLECTION_AS
                ),
                options=[
                    {
                        "label": "Intersection",
                        "value": "intersection",
                    },
                    {"label": "Union", "value": "union"},
                ],
                value="intersection",
            ),
            wcc.SelectWithLabel(
                label="Well collection selector",
                id=self.register_component_unique_id(
                    Filter.Ids.WELL_COLLECTION_SELECTOR
                ),
                options=[
                    {"label": collection, "value": collection}
                    for collection in self.all_well_collection_names
                ],
                value=self.all_well_collection_names,
                size=min([len(self.all_well_collection_names), 5]),
            ),
            wcc.SelectWithLabel(
                label="Realization selector",
                id=self.register_component_unique_id(Filter.Ids.REALIZATION_SELECTOR),
                options=[{"label": real, "value": real} for real in self.realizations],
                value=self.realizations,
                size=min([len(self.wells), 5]),
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLES), "data"
            ),
            Input(
                self.component_unique_id(Filter.Ids.ENSEMBLE_SELECTOR).to_string(),
                "value",
            ),
        )
        def _set_ensembles(ensembles: List[str]) -> List[str]:
            return ensembles

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_DATES), "data"),
            Input(
                self.component_unique_id(Filter.Ids.DATE_SELECTOR).to_string(),
                "value",
            ),
        )
        def _set_dates(dates: List[datetime]) -> List[datetime]:
            return dates

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE), "data"),
            Input(
                self.component_unique_id(Filter.Ids.PHASE_SELECTOR).to_string(),
                "value",
            ),
        )
        def _set_phase(phase: List[str]) -> List[str]:
            return phase

        @callback(
            Output(self.get_store_unique_id(PluginIds.Stores.SELECTED_WELLS), "data"),
            Input(
                self.component_unique_id(Filter.Ids.WELL_SELECTOR).to_string(),
                "value",
            ),
        )
        def _set_wells(wells: List[str]) -> List[str]:
            return wells

        @callback(
            Output(
                self.get_store_unique_id(
                    PluginIds.Stores.SELECTED_COMBINE_WELLS_COLLECTION
                ),
                "data",
            ),
            Input(
                self.component_unique_id(
                    Filter.Ids.COMBINE_WELL_AND_COLLECTION_AS
                ).to_string(),
                "value",
            ),
        )
        def _set_combine_well_and_collection(combine_well_and_collection: str) -> str:
            return combine_well_and_collection

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_WELL_COLLECTIONS),
                "data",
            ),
            Input(
                self.component_unique_id(
                    Filter.Ids.WELL_COLLECTION_SELECTOR
                ).to_string(),
                "value",
            ),
        )
        def _set_well_collection_selector(well_collection: List[str]) -> List[str]:
            return well_collection

        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_REALIZATIONS), "data"
            ),
            Input(
                self.component_unique_id(Filter.Ids.REALIZATION_SELECTOR).to_string(),
                "value",
            ),
        )
        def _set_realizations(realizations: List[int]) -> List[int]:
            return realizations

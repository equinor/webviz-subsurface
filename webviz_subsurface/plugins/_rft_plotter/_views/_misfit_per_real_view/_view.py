from typing import List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from webviz_config.utils import StrEnum
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._reusable_settings import FilterLayout
from ..._reusable_view_element import GeneralViewElement
from ..._utils import RftPlotterDataModel, filter_frame
from ._settings import Selections
from ._utils import update_misfit_per_real_plot


class MisfitPerRealView(ViewABC):
    class Ids(StrEnum):
        SELECTIONS = "selections"
        FILTERS = "filters"
        VIEW_ELEMENT = "view-element"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Misfit per real")
        self._datamodel = datamodel

        self.add_settings_groups(
            {
                self.Ids.SELECTIONS: Selections(self._datamodel.ensembles),
                self.Ids.FILTERS: FilterLayout(
                    wells=self._datamodel.well_names,
                    zones=self._datamodel.zone_names,
                    dates=self._datamodel.dates,
                ),
            }
        )

        self.add_view_element(GeneralViewElement(), self.Ids.VIEW_ELEMENT)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(self.Ids.VIEW_ELEMENT)
                .component_unique_id(GeneralViewElement.Ids.CHART)
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(self.Ids.SELECTIONS)
                .component_unique_id(Selections.Ids.ENSEMBLES)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(FilterLayout.Ids.FILTER_WELLS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(FilterLayout.Ids.FILTER_ZONES)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(FilterLayout.Ids.FILTER_DATES)
                .to_string(),
                "value",
            ),
        )
        def _misfit_plot(
            ensembles: List[str], wells: List[str], zones: List[str], dates: List[str]
        ) -> Union[str, List[wcc.Graph]]:
            df = filter_frame(
                self._datamodel.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            if df.empty:
                return "No data matching the given filter criterias"

            return update_misfit_per_real_plot(df, self._datamodel.enscolors)

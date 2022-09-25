from typing import List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._shared_settings import FilterLayout
from ..._shared_view_element import GeneralViewElement
from ..._types import ColorAndSizeByType
from ..._utils import RftPlotterDataModel, filter_frame
from ._settings import SizeColorLayout
from ._utils import update_crossplot, update_errorplot


class SimVsObsView(ViewABC):
    class Ids(StrEnum):
        FILTERS = "filters"
        SETTINGS = "settings"
        VIEW_ELEMENT = "view-element"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Sim vs obs")
        self._datamodel = datamodel

        self.add_settings_groups(
            {
                self.Ids.FILTERS: FilterLayout(self._datamodel),
                self.Ids.SETTINGS: SizeColorLayout(),
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
                self.settings_group(self.Ids.FILTERS)
                .component_unique_id(FilterLayout.Ids.FILTER_ENSEMBLES)
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
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(SizeColorLayout.Ids.CROSSPLOT_SIZE_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SETTINGS)
                .component_unique_id(SizeColorLayout.Ids.CROSSPLOT_COLOR_BY)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_graph(
            ensembles: List[str],
            wells: List[str],
            zones: List[str],
            dates: List[str],
            sizeby: ColorAndSizeByType,
            colorby: ColorAndSizeByType,
        ) -> Union[str, List[wcc.Graph]]:
            df = filter_frame(
                self._datamodel.ertdatadf,
                {"WELL": wells, "ZONE": zones, "DATE": dates, "ENSEMBLE": ensembles},
            )
            if df.empty:
                return "No data matching the given filter criterias"

            return update_crossplot(df, sizeby, colorby)

from typing import List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import ViewABC

from ..._reusable_settings import FilterLayout
from ..._reusable_view_element import GeneralViewElement
from ..._types import ColorAndSizeByType
from ..._utils import RftPlotterDataModel, filter_frame
from ._settings import Ensembles, PlotType, PlotTypeSettings, SizeColorSettings
from ._utils import update_crossplot, update_errorplot


class SimVsObsView(ViewABC):
    class Ids(StrEnum):
        PLOT_TYPE = "plot-type"
        ENSEMBLES = "ensembles"
        FILTERS = "filters"
        SIZE_COLOR_SETTINGS = "size-color-settings"
        VIEW_ELEMENT = "view-element"

    def __init__(self, datamodel: RftPlotterDataModel) -> None:
        super().__init__("Sim vs obs")
        self._datamodel = datamodel

        self.add_settings_groups(
            {
                self.Ids.PLOT_TYPE: PlotTypeSettings(),
                self.Ids.ENSEMBLES: Ensembles(self._datamodel.ensembles),
                self.Ids.FILTERS: FilterLayout(
                    wells=self._datamodel.well_names,
                    zones=self._datamodel.zone_names,
                    dates=self._datamodel.dates,
                ),
                self.Ids.SIZE_COLOR_SETTINGS: SizeColorSettings(),
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
                self.settings_group(self.Ids.PLOT_TYPE)
                .component_unique_id(PlotTypeSettings.Ids.PLOT_TYPE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.ENSEMBLES)
                .component_unique_id(Ensembles.Ids.ENSEMBLES)
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
                self.settings_group(self.Ids.SIZE_COLOR_SETTINGS)
                .component_unique_id(SizeColorSettings.Ids.CROSSPLOT_SIZE_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SIZE_COLOR_SETTINGS)
                .component_unique_id(SizeColorSettings.Ids.CROSSPLOT_COLOR_BY)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_graph(
            plot_type: PlotType,
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

            if plot_type == PlotType.CROSSPLOT:
                return update_crossplot(df, sizeby, colorby)
            if plot_type == PlotType.ERROR_BOXPLOT:
                return [update_errorplot(df, self._datamodel.enscolors)]
            raise ValueError(f"Plot type: {plot_type.value} not implemented")

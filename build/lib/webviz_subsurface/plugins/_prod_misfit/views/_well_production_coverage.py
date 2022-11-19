from typing import Dict, List, Union

import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)

from .._plugin_ids import PluginIds
from ..utils import make_dataframes as makedf
from ..utils import make_figures as makefigs
from ._view_functions import _get_well_names_combined


class PlotSettingsCoverage(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        COLORBY = "colorby"
        FIG_LAYOUT_HEIGHT = "fig-layout-height"
        PLOT_TYPE = "plot-type"
        COLORBY_GROUPING = "colorby-grouping"
        SHOW_POINTS = "show-points"

    def __init__(self) -> None:
        super().__init__("Plot Settings")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Color by",
                id=self.register_component_unique_id(PlotSettingsCoverage.Ids.COLORBY),
                options=[
                    {
                        "label": "Ensemble",
                        "value": "ENSEMBLE",
                    },
                    # {"label": "Well", "value": "WELL"},
                    {"label": "Date", "value": "DATE"},
                ],
                value="ENSEMBLE",
                multi=False,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Plot type",
                id=self.register_component_unique_id(
                    PlotSettingsCoverage.Ids.PLOT_TYPE
                ),
                options=[
                    {"label": "Diff plot", "value": "diffplot"},
                    {
                        "label": "Diff plot relative (%)",
                        "value": "rel_diffplot",
                    },
                    {"label": "Cross plot", "value": "crossplot"},
                ],
                value="diffplot",
                multi=False,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Fig layout - height",
                id=self.register_component_unique_id(
                    PlotSettingsCoverage.Ids.FIG_LAYOUT_HEIGHT
                ),
                options=[
                    {
                        "label": "Very small",
                        "value": 250,
                    },
                    {
                        "label": "Small",
                        "value": 350,
                    },
                    {
                        "label": "Medium",
                        "value": 450,
                    },
                    {
                        "label": "Large",
                        "value": 700,
                    },
                    {
                        "label": "Very large",
                        "value": 1000,
                    },
                ],
                value=450,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.RadioItems(
                label="Grouping",
                id=self.register_component_unique_id(
                    PlotSettingsCoverage.Ids.COLORBY_GROUPING
                ),
                options=[
                    {"label": "Side by side", "value": "group"},
                    {"label": "Overlay", "value": "overlay"},
                ],
                value="group",
            ),
            wcc.RadioItems(
                label="Show points",
                id=self.register_component_unique_id(
                    PlotSettingsCoverage.Ids.SHOW_POINTS
                ),
                options=[
                    {"label": "Outliers only", "value": "outliers"},
                    {"label": "All points", "value": "all"},
                    {
                        "label": "All points, no box",
                        "value": "strip",
                    },
                ],
                value="outliers",
            ),
        ]


class ProdCoverageView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        PLOT_SETTINGS = "plot-settings"
        MAIN_COLUMN = "main-column"

    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-locals
    def __init__(
        self,
        input_provider_set: EnsembleSummaryProviderSet,
        ens_vectors: Dict[str, List[str]],
        ens_realizations: Dict[str, List[int]],
        well_collections: Dict[str, List[str]],
    ) -> None:
        super().__init__("Well production coverage")

        self.input_provider_set = input_provider_set
        self.ens_vectors = ens_vectors
        self.ens_realizations = ens_realizations
        self.well_collections = well_collections

        self.add_settings_group(
            PlotSettingsCoverage(), ProdCoverageView.Ids.PLOT_SETTINGS
        )
        self.main_column = self.add_column(ProdCoverageView.Ids.MAIN_COLUMN)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(ProdCoverageView.Ids.MAIN_COLUMN)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLES), "data"
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_DATES), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_PHASE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_WELLS), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_WELL_COLLECTIONS),
                "data",
            ),
            Input(
                self.get_store_unique_id(
                    PluginIds.Stores.SELECTED_COMBINE_WELLS_COLLECTION
                ),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_REALIZATIONS), "data"
            ),
            Input(
                self.settings_group(ProdCoverageView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsCoverage.Ids.COLORBY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ProdCoverageView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsCoverage.Ids.PLOT_TYPE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ProdCoverageView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsCoverage.Ids.FIG_LAYOUT_HEIGHT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ProdCoverageView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsCoverage.Ids.COLORBY_GROUPING)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ProdCoverageView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsCoverage.Ids.SHOW_POINTS)
                .to_string(),
                "value",
            ),
            # prevent_initial_call=True,
        )
        def _update_plots(
            ensemble_names: List[str],
            selector_dates: List[str],
            selector_phases: List[str],
            selector_well_names: List[str],
            selector_well_collection_names: List[str],
            selector_well_combine_type: str,
            selector_realizations: List[int],
            colorby: str,
            plot_type: str,
            figheight: int,
            boxmode: str,
            boxplot_points: str,
        ) -> Union[str, List[Component]]:

            if not ensemble_names:
                return "No ensembles selected"

            well_names = _get_well_names_combined(
                self.well_collections,
                selector_well_collection_names,
                selector_well_names,
                selector_well_combine_type,
            )

            if plot_type in ["diffplot", "rel_diffplot"]:
                relative_diff = plot_type == "rel_diffplot"
                dframe = makedf.get_df_diff(
                    makedf.get_df_smry(
                        self.input_provider_set,
                        ensemble_names,
                        self.ens_vectors,
                        self.ens_realizations,
                        selector_realizations,
                        well_names,
                        selector_phases,
                        selector_dates,
                    ),
                    relative_diff=relative_diff,
                )
                figures = makefigs.coverage_diffplot(
                    dframe,
                    selector_phases,
                    colorby,
                    vector_type="well",
                    figheight=figheight,
                    boxmode=boxmode,
                    boxplot_points=boxplot_points,
                )
            if plot_type == "crossplot":
                dframe = makedf.get_df_smry(
                    self.input_provider_set,
                    ensemble_names,
                    self.ens_vectors,
                    self.ens_realizations,
                    selector_realizations,
                    well_names,
                    selector_phases,
                    selector_dates,
                )
                figures = makefigs.coverage_crossplot(
                    dframe,
                    selector_phases,
                    colorby,
                    vector_type="well",
                    figheight=figheight,
                    boxplot_points=boxplot_points,
                )

            return figures

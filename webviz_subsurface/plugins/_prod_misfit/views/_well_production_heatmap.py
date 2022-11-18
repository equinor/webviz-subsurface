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


class PlotSettingsHeatmap(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        COLOR_RANGE_SCALING = "color-range-scaling"
        FIG_LAYOUT_HEIGHT = "fig-layout-height"
        PLOT_TYPE = "plot-type"
        SHOW_WELLS_LARGEST_MISFIT = "show-wells-largest-misfit"

    def __init__(self) -> None:
        super().__init__("Plot Settings")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Show wells with largest misfit",
                id=self.register_component_unique_id(
                    PlotSettingsHeatmap.Ids.SHOW_WELLS_LARGEST_MISFIT
                ),
                options=[
                    {"label": "Show all", "value": 0},
                    {"label": "2", "value": 2},
                    {"label": "4", "value": 4},
                    {"label": "6", "value": 6},
                    {"label": "8", "value": 8},
                    {"label": "10", "value": 10},
                    {"label": "12", "value": 12},
                    {"label": "15", "value": 15},
                    {"label": "20", "value": 20},
                    {"label": "25", "value": 25},
                ],
                value=0,
                multi=False,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            wcc.Dropdown(
                label="Plot type",
                id=self.register_component_unique_id(PlotSettingsHeatmap.Ids.PLOT_TYPE),
                options=[
                    {"label": "Mean misfit", "value": "diffplot"},
                    {
                        "label": "Mean misfit relative (%)",
                        "value": "rel_diffplot",
                    },
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
                    PlotSettingsHeatmap.Ids.FIG_LAYOUT_HEIGHT
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
            wcc.Dropdown(
                label="Color range scaling (relative to max)",
                id=self.register_component_unique_id(
                    PlotSettingsHeatmap.Ids.COLOR_RANGE_SCALING
                ),
                options=[
                    {"label": f"{x:.0%}", "value": x}
                    for x in [
                        0.1,
                        0.2,
                        0.3,
                        0.4,
                        0.5,
                        0.6,
                        0.7,
                        0.8,
                        0.9,
                        1.0,
                        1.5,
                        2.0,
                    ]
                ],
                style={"display": "block"},
                value=1.0,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
        ]


class ProdHeatmapView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        PLOT_SETTINGS = "plot-settings"
        MAIN_COLUMN = "main-column"

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        input_provider_set: EnsembleSummaryProviderSet,
        ens_vectors: Dict[str, List[str]],
        ens_realizations: Dict[str, List[int]],
        well_collections: Dict[str, List[str]],
    ) -> None:
        super().__init__("Well production heatmap")

        self.input_provider_set = input_provider_set
        self.ens_vectors = ens_vectors
        self.ens_realizations = ens_realizations
        self.well_collections = well_collections

        self.add_settings_group(
            PlotSettingsHeatmap(), ProdHeatmapView.Ids.PLOT_SETTINGS
        )
        self.main_column = self.add_column(ProdHeatmapView.Ids.MAIN_COLUMN)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(ProdHeatmapView.Ids.MAIN_COLUMN)
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
                self.settings_group(ProdHeatmapView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsHeatmap.Ids.SHOW_WELLS_LARGEST_MISFIT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ProdHeatmapView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsHeatmap.Ids.PLOT_TYPE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ProdHeatmapView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsHeatmap.Ids.FIG_LAYOUT_HEIGHT)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(ProdHeatmapView.Ids.PLOT_SETTINGS)
                .component_unique_id(PlotSettingsHeatmap.Ids.COLOR_RANGE_SCALING)
                .to_string(),
                "value",
            ),
            # prevent_initial_call=True,
        )
        def _update_plots(
            ensemble_names: List[str],
            selector_dates: list,
            selector_phases: list,
            selector_well_names: list,
            selector_well_collection_names: list,
            selector_well_combine_type: str,
            selector_realizations: list,
            selector_filter_largest: int,
            selector_plot_type: str,
            selector_figheight: int,
            selector_scale_col_range: float,
        ) -> Union[str, List[Component]]:
            # pylint disable=too-many-arguments

            if not ensemble_names:
                return "No ensembles selected"

            well_names = _get_well_names_combined(
                self.well_collections,
                selector_well_collection_names,
                selector_well_names,
                selector_well_combine_type,
            )

            relative_diff = selector_plot_type == "rel_diffplot"
            dframe = makedf.get_df_diff_stat(
                makedf.get_df_diff(
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
            )

            figures = makefigs.heatmap_plot(
                dframe,
                selector_phases,
                vector_type="well",
                filter_largest=selector_filter_largest,
                figheight=selector_figheight,
                scale_col_range=selector_scale_col_range,
            )
            return figures

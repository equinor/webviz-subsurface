from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._shared_settings import CaseSettings, FilterSettings, MapPlotSettings
from .._supporting_files._plot_functions import update_obs_sim_map_plot
from .._supporting_files._support_functions import _map_initial_marker_size
from .._view_elements import SeismicSlider


class SliceSettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        SLICING_ACCURACY = "slicing-accuracy"
        PLOT_TYPE = "plot-type"

    def __init__(self) -> None:
        super().__init__("Plot settings and layout")

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                label="Slicing accuracy (north ± meters)",
                id=self.register_component_unique_id(self.Ids.SLICING_ACCURACY),
                options=[
                    {"label": "± 10m", "value": 10},
                    {"label": "± 25m", "value": 25},
                    {"label": "± 50m", "value": 50},
                    {"label": "± 75m", "value": 75},
                    {
                        "label": "± 100m",
                        "value": 100,
                    },
                    {
                        "label": "± 150m",
                        "value": 150,
                    },
                    {
                        "label": "± 200m",
                        "value": 200,
                    },
                    {
                        "label": "± 250m",
                        "value": 250,
                    },
                ],
                value=75,
                clearable=False,
                persistence=True,
                persistence_type="memory",
            ),
            # wcc.Dropdown(
            wcc.RadioItems(
                label="Plot type",
                id=self.register_component_unique_id(self.Ids.PLOT_TYPE),
                options=[
                    {"label": "Statistics", "value": "stat"},
                    {
                        "label": "Individual realizations",
                        "value": "reals",
                    },
                ],
                value="stat",
                # clearable=False,
                # persistence=True,
                # persistence_type="memory",
            ),
        ]


class MapPlot(ViewABC):
    class Ids:
        CASE_SETTINGS = "case-setting"
        FILTER_SETTINGS = "filter-settings"
        MAP_PLOT_SETTINGS = "map-plot-settings"
        SLICE_SETTINGS = "slice-settings"
        SLICE_POSITION = "slice-position"
        PLOT_FIGS = "plot-figs"
        PLOT_SLICE = "plot-slice"

    def __init__(
        self,
        attributes: List[str],
        ens_names: List,
        region_names: List[int],
        realizations: List,
        dframe: Dict,
        dframeobs: dict,
        df_polygons: pd.DataFrame,
        caseinfo: str,
    ) -> None:
        super().__init__("Errorbar - sim vs obs")
        self.attributes = attributes
        self.ens_names = ens_names
        self.region_names = region_names
        self.realizations = realizations
        self.dframe = dframe
        self.dframeobs = dframeobs
        self.df_polygons = df_polygons
        self.polygon_names = sorted(list(self.df_polygons.name.unique()))
        self.caseinfo = caseinfo
        self.map_y_range: List[float] = []

        # -- get initial obs data range
        self.obs_range_init = [
            self.dframeobs[self.attributes[0]]["obs"].min(),
            self.dframeobs[self.attributes[0]]["obs"].max(),
        ]
        self.obs_error_range_init = [
            self.dframeobs[self.attributes[0]]["obs_error"].min(),
            self.dframeobs[self.attributes[0]]["obs_error"].max(),
        ]

        self.map_intial_marker_size = _map_initial_marker_size(
            len(self.dframeobs[attributes[0]].index),
            len(self.ens_names),
        )

        # -- get map north range
        for attribute_name in self.attributes:
            if not self.map_y_range:
                self.map_y_range = [
                    self.dframeobs[attribute_name]["north"].min(),
                    self.dframeobs[attribute_name]["north"].max(),
                ]
            else:
                north_min = self.dframeobs[attribute_name]["north"].min()
                north_max = self.dframeobs[attribute_name]["north"].max()
                self.map_y_range = [
                    min(north_min, self.map_y_range[0]),
                    max(north_max, self.map_y_range[1]),
                ]

        self.add_settings_groups(
            {
                self.Ids.CASE_SETTINGS: CaseSettings(self.attributes, self.ens_names),
                self.Ids.FILTER_SETTINGS: FilterSettings(
                    self.region_names, self.realizations
                ),
                self.Ids.MAP_PLOT_SETTINGS: MapPlotSettings(
                    self.map_intial_marker_size, self.polygon_names
                ),
                self.Ids.SLICE_SETTINGS: SliceSettings(),
            }
        )

        column = self.add_column()
        column.make_row(self.Ids.PLOT_FIGS)
        slice_position = column.make_row()
        slice_position.add_view_element(
            SeismicSlider(self.map_y_range), self.Ids.SLICE_POSITION
        )
        column.make_row(self.Ids.PLOT_SLICE)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.settings_group(self.Ids.CASE_SETTINGS)
                .component_unique_id(CaseSettings.Ids.ENSEMBLES_NAME)
                .to_string(),
                "multi",
            ),
            Output(
                self.settings_group(self.Ids.CASE_SETTINGS)
                .component_unique_id(CaseSettings.Ids.ENSEMBLES_NAME)
                .to_string(),
                "value",
            ),
            Input("webviz-content-manager", "activeViewId"),
        )
        def _update_case_settings(viewId: str) -> Tuple:
            return (False, self.ens_names[0])

        @callback(
            Output(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_BY)
                .to_string(),
                "label",
            ),
            Output(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_BY)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_BY)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_RANGE_SCALING)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_RANGE_SCALING)
                .to_string(),
                "value",
            ),
            Input("webviz-content-manager", "activeViewId"),
        )
        def _update_map_plot_settings(viewId: str) -> Tuple:
            return (
                "Show difference or coverage plot",
                [
                    {
                        "label": "Difference plot",
                        "value": 0,
                    },
                    {
                        "label": "Coverage plot",
                        "value": 1,
                    },
                    {
                        "label": "Coverage plot (obs error adjusted)",
                        "value": 2,
                    },
                    {
                        "label": "Region plot",
                        "value": 3,
                    },
                ],
                0,
                [
                    {"label": f"{val:.0%}", "value": val}
                    for val in [
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
                        2,
                        5,
                        10,
                    ]
                ],
                0.8,
            )

        # --- Seismic errorbar plot - sim vs obs ---
        @callback(
            Output(
                self.layout_element(self.Ids.PLOT_FIGS).get_unique_id().to_string(),
                "children",
            ),
            Output(
                self.layout_element(self.Ids.PLOT_SLICE).get_unique_id().to_string(),
                "children",
            ),
            Input(
                self.settings_group(self.Ids.CASE_SETTINGS)
                .component_unique_id(CaseSettings.Ids.ATTRIBUTE_NAME)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.CASE_SETTINGS)
                .component_unique_id(CaseSettings.Ids.ENSEMBLES_NAME)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTER_SETTINGS)
                .component_unique_id(FilterSettings.Ids.REGION_SELECTOR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTER_SETTINGS)
                .component_unique_id(FilterSettings.Ids.REALIZATION_SELECTOR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_BY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_RANGE_SCALING)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.MARKER_SIZE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.POLYGONS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SLICE_SETTINGS)
                .component_unique_id(SliceSettings.Ids.SLICING_ACCURACY)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.SLICE_SETTINGS)
                .component_unique_id(SliceSettings.Ids.PLOT_TYPE)
                .to_string(),
                "value",
            ),
            Input(
                self.view_element(self.Ids.SLICE_POSITION)
                .component_unique_id(SeismicSlider.Ids.SLIDER)
                .to_string(),
                "value",
            ),
            # prevent_initial_call=True,
        )
        def _update_map_plot_obs_and_sim(
            attr_name: str,
            ens_name: str,
            regions: List[Union[int, str]],
            realizations: List[Union[int, str]],
            plot_coverage: int,
            scale_col_range: float,
            marker_size: int,
            map_plot_polygon: str,
            slice_accuracy: Union[int, float],
            slice_type: str,
            slice_position: float,
        ) -> Tuple[Optional[Any], Optional[Any]]:

            if not regions:
                raise PreventUpdate

            # --- ensure int type
            regions = [int(reg) for reg in regions]

            obs_range = [
                self.dframeobs[attr_name]["obs"].min(),
                self.dframeobs[attr_name]["obs"].max(),
            ]

            # --- apply region filter
            dframe = self.dframe[attr_name].loc[
                self.dframe[attr_name]["region"].isin(regions)
            ]

            # --- apply realization filter
            col_names = ["real-" + str(real) for real in realizations]
            dframe = dframe.drop(
                columns=[
                    col for col in dframe if "real-" in col and col not in col_names
                ]
            )

            df_poly = pd.DataFrame()
            if self.df_polygons is not None:
                df_poly = self.df_polygons[self.df_polygons.name == map_plot_polygon]

            fig_maps, fig_slice = update_obs_sim_map_plot(
                dframe,
                ens_name,
                df_polygon=df_poly,
                obs_range=obs_range,
                scale_col_range=scale_col_range,
                slice_accuracy=slice_accuracy,
                slice_position=slice_position,
                plot_coverage=plot_coverage,
                marker_size=marker_size,
                slice_type=slice_type,
            )

            return (wcc.Graph(figure=fig_maps), wcc.Graph(figure=fig_slice))

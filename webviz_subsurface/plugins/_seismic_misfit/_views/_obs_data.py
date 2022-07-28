from typing import List, Tuple, Union

import pandas as pd
import webviz_core_components as wcc
from dash import Input, Output, callback
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._shared_settings import CaseSettings, MapPlotSettings
from .._supporting_files._plot_functions import update_obsdata_map, update_obsdata_raw
from .._supporting_files._support_functions import _map_initial_marker_size
from .._view_elements import InfoBox


class ObsFilterSettings(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        REGION_NAME = "region-name"
        NOISE_FILTER = "noise-filter"
        FILTER_VALUE = "filter-value"

    def __init__(
        self, region_names: List[int], obs_error_range_init: List, obs_range_init: List
    ) -> None:
        super().__init__("filter sttings")
        self.region_names = region_names
        self.obs_error_range_init = obs_error_range_init
        self.obs_range_init = obs_range_init

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                label="Region selector",
                id=self.register_component_unique_id(self.Ids.REGION_NAME),
                options=[
                    {"label": regno, "value": regno} for regno in self.region_names
                ],
                size=min([len(self.region_names), 5]),
                value=self.region_names,
            ),
            wcc.Slider(
                label="Noise filter",
                id=self.register_component_unique_id(self.Ids.NOISE_FILTER),
                min=0,
                max=0.5
                * max(
                    abs(self.obs_range_init[0]),
                    abs(self.obs_range_init[1]),
                ),
                step=0.5 * self.obs_error_range_init[0],
                marks=None,
                value=0,
            ),
            wcc.Label(
                id=self.register_component_unique_id(self.Ids.FILTER_VALUE),
                style={
                    "color": "blue",
                    "font-size": "15px",
                },
            ),
        ]

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.component_unique_id(self.Ids.FILTER_VALUE).to_string(), "children"
            ),
            Input(self.component_unique_id(self.Ids.NOISE_FILTER).to_string(), "value"),
        )
        def _update_noise_filter_value(noise_filter_value: float) -> str:
            return f"Current noise filter value: {noise_filter_value}"


class RawPlotSettings(SettingsGroupABC):
    class Ids:
        OBS_ERROR = "obs-error"
        HISTOGRAM = "histogram"
        X_AXIS_SETTINGS = "x-axix-settings"

    def __init__(self) -> None:
        super().__init__("Raw plot settings")

    def layout(self) -> List[Component]:
        return [
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.OBS_ERROR),
                label="Obs error",
                options=[
                    {
                        "label": "On",
                        "value": True,
                    },
                    {
                        "label": "Off",
                        "value": False,
                    },
                ],
                value=False,
            ),
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.HISTOGRAM),
                label="Histogram",
                options=[
                    {
                        "label": "On",
                        "value": True,
                    },
                    {
                        "label": "Off",
                        "value": False,
                    },
                ],
                value=False,
            ),
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.X_AXIS_SETTINGS),
                label="X-axis settings",
                options=[
                    {
                        "label": "Reset index/sort by region",
                        "value": True,
                    },
                    {
                        "label": "Original ordering",
                        "value": False,
                    },
                ],
                value=False,
            ),
        ]


class ObsData(ViewABC):
    class Ids:
        CASE_SETTINGS = "case-setting"
        FILTER_SETTINGS = "filter-settings"
        RAW_PLOT_SETTINGS = "raw-plot-settings"
        MAP_PLOT_SETTINGS = "map_plot_settings"
        GRAPHS_RAW = "graphs-raw"
        GRAPHS_MAP = "graphs-map"
        ERROR_INFO = "error-info"
        ERROR_INFO_ELEMENT = "error-info-element"

    def __init__(
        self,
        attributes: List[str],
        ens_names: List,
        region_names: List[int],
        dframeobs: dict,
        df_polygons: pd.DataFrame,
        caseinfo: str,
    ) -> None:
        super().__init__("Seismic obs data")
        self.attributes = attributes
        self.ens_names = ens_names
        self.region_names = region_names
        self.dframeobs = dframeobs
        self.df_polygons = df_polygons
        self.polygon_names = sorted(list(self.df_polygons.name.unique()))
        self.caseinfo = caseinfo

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

        self.add_settings_groups(
            {
                self.Ids.CASE_SETTINGS: CaseSettings(self.attributes, self.ens_names),
                self.Ids.FILTER_SETTINGS: ObsFilterSettings(
                    self.region_names, self.obs_error_range_init, self.obs_range_init
                ),
                self.Ids.RAW_PLOT_SETTINGS: RawPlotSettings(),
                self.Ids.MAP_PLOT_SETTINGS: MapPlotSettings(
                    self.map_intial_marker_size, self.polygon_names
                ),
            }
        )

        column = self.add_column()
        column.make_row(self.Ids.GRAPHS_RAW)
        column.make_row(self.Ids.GRAPHS_MAP)
        error_info = column.make_row(self.Ids.ERROR_INFO)
        error_info.add_view_element(
            InfoBox("Obsdata info", self.caseinfo), self.Ids.ERROR_INFO_ELEMENT
        )

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

        # --- Seismic obs data ---
        @callback(
            Output(
                self.layout_element(self.Ids.GRAPHS_RAW).get_unique_id().to_string(),
                "children",
            ),
            Output(
                self.layout_element(self.Ids.GRAPHS_MAP).get_unique_id().to_string(),
                "children",
            ),
            # Output(self.uuid("obsdata-graph-map"), "figure"),
            Output(
                self.settings_group(self.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_RANGE_SCALING)
                .to_string(),
                "style",
            ),
            # Output(self.uuid("obsdata-noise_filter_text"), "children"),
            Output(
                self.settings_group(self.Ids.FILTER_SETTINGS)
                .component_unique_id(ObsFilterSettings.Ids.NOISE_FILTER)
                .to_string(),
                "max",
            ),
            Output(
                self.settings_group(self.Ids.FILTER_SETTINGS)
                .component_unique_id(ObsFilterSettings.Ids.NOISE_FILTER)
                .to_string(),
                "step",
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
                .component_unique_id(ObsFilterSettings.Ids.REGION_NAME)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.FILTER_SETTINGS)
                .component_unique_id(ObsFilterSettings.Ids.NOISE_FILTER)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.RAW_PLOT_SETTINGS)
                .component_unique_id(RawPlotSettings.Ids.OBS_ERROR)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.RAW_PLOT_SETTINGS)
                .component_unique_id(RawPlotSettings.Ids.HISTOGRAM)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(self.Ids.RAW_PLOT_SETTINGS)
                .component_unique_id(RawPlotSettings.Ids.X_AXIS_SETTINGS)
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
            # prevent_initial_call=True,
        )
        def _update_obsdata_graph(
            attr_name: str,
            ens_name: str,
            regions: List[Union[int, str]],
            noise_filter: float,
            showerror: bool,
            showhistogram: bool,
            resetindex: bool,
            obsmap_colorby: str,
            obsmap_scale_col_range: float,
            obsmap_marker_size: int,
            obsmap_polygon: str,
        ) -> Tuple:

            if not regions:
                raise PreventUpdate

            # --- ensure int type
            regions = [int(reg) for reg in regions]

            obs_range = [
                self.dframeobs[attr_name]["obs"].min(),
                self.dframeobs[attr_name]["obs"].max(),
            ]
            obs_error_range = [
                self.dframeobs[attr_name]["obs_error"].min(),
                self.dframeobs[attr_name]["obs_error"].max(),
            ]

            # --- apply region filter
            dframe_obs = self.dframeobs[attr_name].loc[
                self.dframeobs[attr_name]["region"].isin(regions)
            ]

            # --- apply ensemble filter
            dframe_obs = dframe_obs[dframe_obs.ENSEMBLE.eq(ens_name)]

            # --- apply noise filter
            dframe_obs = dframe_obs[abs(dframe_obs.obs).ge(noise_filter)]

            df_poly = pd.DataFrame()
            if self.df_polygons is not None:
                df_poly = self.df_polygons[self.df_polygons.name == obsmap_polygon]

            # --- make graphs
            fig_map = update_obsdata_map(
                dframe_obs.copy(),
                colorby=obsmap_colorby,
                df_polygon=df_poly,
                obs_range=obs_range,
                obs_err_range=obs_error_range,
                scale_col_range=obsmap_scale_col_range,
                marker_size=obsmap_marker_size,
            )
            # if fig_raw is run before fig_map some strange value error
            # my arise at init callback --> unknown reason
            fig_raw = update_obsdata_raw(
                dframe_obs.copy(),
                colorby="region",
                showerror=showerror,
                showhistogram=showhistogram,
                reset_index=resetindex,
            )

            graphs_raw = wcc.Graph(
                style={"height": "37vh"},
                figure=fig_raw,
            )
            graph_map = wcc.Graph(
                style={"height": "50vh"},
                figure=fig_map,
            )

            show_hide_range_scaling = {"display": "block"}
            if obsmap_colorby == "region":
                show_hide_range_scaling = {"display": "none"}

            noise_filter_max = 0.5 * max(abs(obs_range[0]), abs(obs_range[1]))
            noise_filter_step = 0.5 * obs_error_range[0]
            return (
                graphs_raw,
                graph_map,
                show_hide_range_scaling,
                noise_filter_max,
                noise_filter_step,
            )

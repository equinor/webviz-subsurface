import logging
from typing import Callable, List, Tuple

from dash import html
from dash.development.base_component import Component
from webviz_config import WebvizPluginABC, WebvizSettings

from ._plugin_ids import PluginIds
from ._shared_settings import CaseSettings, MapPlotSettings
from ._supporting_files._dataframe_functions import make_polygon_df, makedf
from ._supporting_files._support_functions import _compare_dfs_obs
from ._views import Crossplot, ErrorbarPlots, MapPlot, MisfitPerReal, ObsData
from ._views._obs_data import ObsFilterSettings, RawPlotSettings


class SeismicMisfit(WebvizPluginABC):
    """Seismic misfit plotting.
    Consists of several tabs with different plots of
    observed and simulated seismic 4d attribute.
    * Seismic obs data (overview)
    * Seismic misfit per real (misfit quantification and ranking)
    * Seismic crossplot - sim vs obs (data points statistics)
    * Seismic errorbar plot - sim vs obs (data points statistics)
    * Seismic map plot - sim vs obs (data points statistics)

    ---

    * **`ensembles`:** Which *scratch_ensembles* in *shared_settings* to include.
    <br>(Note that **realization-** must be part of the *shared_settings* paths.)

    * **`attributes`:** List of the simulated attribute file names to include.
    It is a requirement that there is a corresponding file with the observed
    and meta data included. This file must have the same name, but with an
    additional prefix = "meta--". For example, if one includes a file
    called "my_awesome_attribute.txt" in the attributes list, the corresponding
    obs/meta file must be called "meta--my_awesome_attribute.txt". See Data input
    section for more  details.

    * **`attribute_sim_path`:** Path to the `attributes` simulation file.
    Path is given as relative to *runpath*, where *runpath* = path as defined
    for `ensembles` in shared settings.

    * **`attribute_obs_path`:** Path to the `attributes` obs/meta file.
    Path is either given as relative to *runpath* or as an absolute path.

    * **`obs_mult`:** Multiplier for all observation and observation error data.
    Can be used for calibration purposes.

    * **`sim_mult`:** Multiplier for all simulated data.
    Can be used for calibration purposes.

    * **`polygon`:** Path to a folder or a file containing (fault-) polygons.
    If value is a folder all csv files in that folder will be included
    (e.g. "share/results/polygons/").
    If value is a file, then that file will be read. One can also use \\*-notation
    in filename to read filtered list of files
    (e.g. "share/results/polygons/\\*faultlines\\*csv").
    Path is either given as relative to *runpath* or as an absolute path.
    If path is ambigious (e.g. with multi-realization runpath),
    only the first successful find is used.

    * **`realrange`:** Realization range filter for each of the ensembles.
    Assign as list of two integers in square brackets (e.g. [0, 99]).
    Realizations outside range will be excluded.
    If `realrange` is omitted, no realization filter will be applied (i.e. include all).

    ---

    a) The required input data consists of 2 different file types.<br>

    1) Observation and meta data csv file (one per attribute):
    This csv file must contain the 5 column headers "EAST" (or "X_UTME"),
    "NORTH" (or "Y_UTMN"), "REGION", "OBS" and "OBS_ERROR".
    The column names are case insensitive and can be in any order.
    "OBS" is the observed attribute value and "OBS_ERROR"
    is the corresponding error.<br>
    ```csv
        X_UTME,Y_UTMN,REGION,OBS,OBS_ERROR
        456166.26,5935963.72,1,0.002072,0.001
        456241.17,5935834.17,2,0.001379,0.001
        456316.08,5935704.57,3,0.001239,0.001
        ...
        ...
    ```
    2) Simulation data file (one per attribute and realization):
    This is a 1 column file (ERT compatible format).
    The column is the simulated attribute value. This file has no header.
    ```
        0.0023456
        0.0012345
        0.0013579
        ...
        ...
    ```

    It is a requirement that each line of data in these 2 files represent
    the same data point. I.e. line number N+1 in obs/metadata file corresponds to
    line N in sim files. The +1 shift for the obs/metadata file
    is due to that file is the only one with a header.

    b) Polygon data is optional to include. Polygons must be stored in
    csv file(s) on the format shown below. A csv file can have multiple
    polygons (e.g. fault polygons), identified with the ID value.
    The alternative header names "X_UTME", "Y_UTMN", "Z_TVDSS", "POLY_ID" will also
    be accepted. The "Z"/"Z_TVDSS" column can be omitted. Any other column can be
    included, but they will be skipped upon reading.
    ```csv
        X,Y,Z,ID
        460606.36,5935605.44,1676.49,1
        460604.92,5935583.99,1674.84,1
        460604.33,5935575.08,1674.16,3
        ...
        ...
    ```
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        attributes: List[str],
        attribute_sim_path: str = "share/results/maps/",
        attribute_obs_path: str = "../../share/observations/seismic/",
        obs_mult: float = 1.0,
        sim_mult: float = 1.0,
        polygon: str = None,
        realrange: List[List[int]] = None,
    ) -> None:
        super().__init__()

        self.attributes = attributes

        self.ensemble_set = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }

        self.ens_names = []
        for ens_name, _ in self.ensemble_set.items():
            self.ens_names.append(ens_name)

        self.polygon = polygon
        if not polygon:
            self.df_polygons = None
            logging.info("Polygon not assigned in config file - continue without.\n")
        else:  # grab polygon files and store in dataframe
            self.df_polygons = make_polygon_df(
                ensemble_set=self.ensemble_set, polygon=self.polygon
            )

        self.caseinfo = ""
        self.dframe = {}
        self.dframeobs = {}
        self.makedf_args = {}
        self.region_names: List[int] = []

        for attribute_name in self.attributes:
            logging.debug(f"Build dataframe for attribute: \n{attribute_name}\n")
            # make dataframe with all data
            self.dframe[attribute_name] = makedf(
                self.ensemble_set,
                attribute_name,
                attribute_sim_path,
                attribute_obs_path,
                obs_mult,
                sim_mult,
                realrange,
            )
            # make dataframe with only obs and meta data
            self.dframeobs[attribute_name] = self.dframe[attribute_name].drop(
                columns=[
                    col
                    for col in self.dframe[attribute_name]
                    if col.startswith("real-")
                ]
            )

            self.makedf_args[attribute_name] = {  # for add_webvizstore
                "ensemble_set": self.ensemble_set,
                "attribute_name": attribute_name,
                "attribute_sim_path": attribute_sim_path,
                "attribute_obs_path": attribute_obs_path,
                "obs_mult": obs_mult,
                "sim_mult": sim_mult,
                "realrange": realrange,
            }

            obsinfo = _compare_dfs_obs(self.dframeobs[attribute_name], self.ens_names)
            self.caseinfo = (
                f"{self.caseinfo}Attribute: {attribute_name}"
                f"\n{obsinfo}\n-----------\n"
            )

            # get sorted list of unique region values
            # simplified approach: union across all attributes/metafiles
            if not self.region_names:
                self.region_names = sorted(
                    list(self.dframeobs[attribute_name]["region"].unique())
                )
            else:
                for regname in self.dframeobs[attribute_name]["region"].unique():
                    if regname not in self.region_names:
                        self.region_names.append(regname)
                self.region_names = sorted(self.region_names)

        # get list of all realizations (based on column names real-x)
        self.realizations = [
            col.replace("real-", "")
            for col in self.dframe[attributes[0]]
            if col.startswith("real")
        ]

        self.add_view(
            ObsData(
                self.attributes,
                self.ens_names,
                self.region_names,
                self.dframeobs,
                self.df_polygons,
                self.caseinfo,
            ),
            PluginIds.ViewsIds.OBS_DATA,
            PluginIds.ViewsIds.VIEWS_GROUP,
        )

        self.add_view(
            MisfitPerReal(
                self.attributes,
                self.ens_names,
                self.region_names,
                self.realizations,
                self.dframe,
                self.caseinfo,
            ),
            PluginIds.ViewsIds.MISFIT_PER_REAL,
            PluginIds.ViewsIds.VIEWS_GROUP,
        )

        self.add_view(
            Crossplot(
                self.attributes,
                self.ens_names,
                self.region_names,
                self.realizations,
                self.dframe,
                self.caseinfo,
            ),
            PluginIds.ViewsIds.CROSSPLOT,
            PluginIds.ViewsIds.VIEWS_GROUP,
        )

        self.add_view(
            ErrorbarPlots(
                self.attributes,
                self.ens_names,
                self.region_names,
                self.realizations,
                self.dframe,
                self.caseinfo,
            ),
            PluginIds.ViewsIds.ERRORBAR_PLOTS,
            PluginIds.ViewsIds.VIEWS_GROUP,
        )

        self.add_view(
            MapPlot(
                self.attributes,
                self.ens_names,
                self.region_names,
                self.realizations,
                self.dframe,
                self.dframeobs,
                self.df_polygons,
                self.caseinfo,
            ),
            PluginIds.ViewsIds.MAP_PLOT,
            PluginIds.ViewsIds.VIEWS_GROUP,
        )

    @property
    def layout(self) -> Component:
        return html.Div("No view is loaded.")

    def add_webvizstore(self) -> List[Tuple[Callable, list]]:
        funcs = []
        for attribute_name in self.attributes:
            funcs.append((makedf, [self.makedf_args[attribute_name]]))
        if self.polygon is not None:
            funcs.append(
                (
                    make_polygon_df,
                    [
                        {
                            "ensemble_set": self.ensemble_set,
                            "polygon": self.polygon,
                        }
                    ],
                )
            )
        return funcs

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .layout_element(ObsData.Ids.GRAPHS_RAW)
                .get_unique_id(),
                "content": ("Observation data 'raw' plot."),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .layout_element(ObsData.Ids.GRAPHS_MAP)
                .get_unique_id(),
                "content": ("Observation data map view plot."),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.CASE_SETTINGS)
                .component_unique_id(CaseSettings.Ids.ENSEMBLES_NAME),
                "content": (
                    "Select ensemble to view. "
                    "One can only select one at a time in this tab."
                ),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.CASE_SETTINGS)
                .component_unique_id(CaseSettings.Ids.ATTRIBUTE_NAME),
                "content": (
                    "Select which attribute to view. One can only select one at a time."
                ),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.FILTER_SETTINGS)
                .component_unique_id(ObsFilterSettings.Ids.REGION_NAME),
                "content": ("Region filter. "),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.FILTER_SETTINGS)
                .component_unique_id(ObsFilterSettings.Ids.NOISE_FILTER),
                "content": ("Noise filter. In steps of half of the lowest obs error."),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.RAW_PLOT_SETTINGS)
                .component_unique_id(RawPlotSettings.Ids.OBS_ERROR),
                "content": ("Toggle observation error on or off."),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.RAW_PLOT_SETTINGS)
                .component_unique_id(RawPlotSettings.Ids.HISTOGRAM),
                "content": ("Toggle observation data histogram on or off."),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.RAW_PLOT_SETTINGS)
                .component_unique_id(RawPlotSettings.Ids.X_AXIS_SETTINGS),
                "content": (
                    "Use original ordering (as from imported data) or reset index"
                    + " (can be useful in combination with filters."
                ),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_BY),
                "content": ("Select data to use for coloring of the map view plot."),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .settings_group(ObsData.Ids.MAP_PLOT_SETTINGS)
                .component_unique_id(MapPlotSettings.Ids.COLOR_RANGE_SCALING),
                "content": (
                    "Select color range scaling factor used "
                    + "with the map view plot."
                ),
            },
            {
                "id": self.view(PluginIds.ViewsIds.OBS_DATA)
                .layout_element(ObsData.Ids.ERROR_INFO)
                .get_unique_id(),
                "content": (
                    "Info of the ensembles observation data comparison. "
                    + "For a direct comparison they should have the same "
                    + "observation and observation error data."
                ),
            },
        ]

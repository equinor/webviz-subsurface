from typing import Callable, Dict, List, Tuple

from dash import Dash, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.deprecation_decorators import deprecated_plugin

from ._business_logic import WellCompletionsDataModel
from ._callbacks import plugin_callbacks
from ._layout import layout_tour_steps, main_layout


@deprecated_plugin(
    "This plugin has been replaced by the `WellCompletion` plugin (without "
    "the `s`) which is based on the `wellcompletionsdata` export from `ecl2df`. "
    "The new plugin is faster and has more functionality. "
)
class WellCompletions(WebvizPluginABC):
    # pylint: disable=line-too-long
    """Visualizes well completions data per well coming from export of the Eclipse COMPDAT output. \
    Data is grouped per well and zone and can be filtered accoring to flexible well categories.

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`compdat_file`:** `.csv` file with compdat data per realization
    * **`well_connection_status_file`:** `.parquet` file with well connection status per realization
    * **`zone_layer_mapping_file`:** `.lyr` file specifying the zone ➔ layer mapping
    * **`stratigraphy_file`:** `.json` file defining the stratigraphic levels
    * **`well_attributes_file`:** `.json` file with categorical well attributes
    * **`kh_unit`:** e.g. mD·m, will try to extract from eclipse files if defaulted
    * **`kh_decimal_places`:**

    ---
    The minimum requirement is to define `ensembles`.

    **COMPDAT input**

    `compdat_file` is a path to a file stored per realization (e.g. in \
    `share/results/tables/compdat.csv`). This file can be exported to disk per realization by using
    the `ECL2CSV` forward model in ERT with subcommand `compdat`. [Link to ecl2csv compdat documentation.](https://equinor.github.io/ecl2df/usage/compdat.html)

    The connection status history of each cell is not necessarily complete in the `ecl2df` export,
    because status changes resulting from ACTIONs can't be extracted from the Eclipse input
    files. If the `ecl2df` export is good, it is recommended to use that. This will often be the
    case for history runs. But if not, an alternative way of extracting the data is described in
    the next section.

    **Well Connection status input**

    The `well_connection_status_file` is a path to a file stored per realization (e.g. in \
    `share/results/tables/wellconnstatus.csv`. This file can be exported to disk per realization
    by using the `ECL2CSV` forward model in ERT with subcommand `wellconnstatus`.  [Link to ecl2csv wellconnstatus documentation.](https://equinor.github.io/ecl2df/usage/wellconnstatus.html)

    This approach uses the CPI summary data to create a well connection status history: for
    each well connection cell there is one line for each time the connection is opened or closed.
    This data is sparse, but be aware that the CPI summary data can potentially become very large.

    **Zone layer mapping**

    The `zone_layer_mapping_file` file can be dumped to disk per realization by an internal \
    RMS script as part of the FMU workflow. A sample python script should be available in the \
    Drogon project.

    The file needs to be on the lyr format used by ResInsight:
    [Link to description of lyr format](https://resinsight.org/3d-main-window/formations/#formation-names-description-files-_lyr_).

    Zone colors can be specified in the lyr file, but only 6 digit hexadecimal codes will be used.

    If no file exists, layers will be used as zones.

    **Stratigraphy file**

    The `stratigraphy_file` file is intended to be generated per realization by an internal \
    RMS script as part of the FMU workflow, but can also be set up manually and copied to each
    realization. The stratigraphy is a tree structure, where each node has a name, an optional
    `color` parameter, and an optional `subzones` parameter which itself is a list of the same format.
    ```json
    [
        {
            "name": "ZoneA",
            "color": "#FFFFFF",
            "subzones": [
                {
                    "name": "ZoneA.1"
                },
                {
                    "name": "ZoneA.2"
                }
            ]
        },
        {
            "name": "ZoneB",
            "color": "#FFF000",
            "subzones": [
                {
                    "name": "ZoneB.1",
                    "color": "#FFF111"
                },
                {
                    "name": "ZoneB.2",
                    "subzones: {"name": "ZoneB.2.2"}
                }
            ]
        },
    ]
    ```
    The `stratigraphy_file` and the `zone_layer_mapping_file` will be combined to create the final \
    stratigraphy. A node will be removed if the name or any of the subnode names are not \
    present in the zone layer mapping. A Value Error is raised if any zones are present in the
    zone layer mapping but not in the stratigraphy.

    Colors can be supplied both trough the stratigraphy and through the zone_layer_mapping. \
    The following prioritization will be applied:
    1. Colors specified in the stratigraphy
    2. Colors specified in the zone layer mapping lyr file
    3. If none of the above is specified, theme colors will be added to the leaves of the tree

    **Well Attributes file**

    The `well_attributes_file` file is intended to be generated per realization by an internal \
    RMS script as part of the FMU workflow. A sample script will be made available, but it is \
    possible to manually set up the file and copy it to the correct folder on the scratch disk.\
    The categorical well attributes are completely flexible.

    The file should be a `.json` file on the following format:
    ```json
    {
        "version" : "0.1",
        "wells" : [
            {
                "alias" : {
                    "eclipse" : "OP_1"
                },
                "attributes" : {
                    "mlt_singlebranch" : "mlt",
                    "structure" : "East",
                    "welltype" : "producer"
                },
                "name" : "OP_1"
            },
            {
                "alias" : {
                    "eclipse" : "GI_1"
                },
                "attributes" : {
                    "mlt_singlebranch" : "singlebranch",
                    "structure" : "West",
                    "welltype" : "gas injector"
                },
                "name" : "GI_1"
            },
        ]
    }
    ```

    **KH unit**

    If defaulted, the plugin will look for the unit system of the Eclipse deck in the DATA file. \
    The kh unit will be deduced from the unit system, e.g. mD·m if METRIC.

    """

    def __init__(
        # pylint: disable=too-many-arguments
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        compdat_file: str = "share/results/tables/compdat.csv",
        well_connection_status_file: str = "share/results/tables/wellconnstatus.csv",
        zone_layer_mapping_file: str = "rms/output/zone/simgrid_zone_layer_mapping.lyr",
        stratigraphy_file: str = "rms/output/zone/stratigraphy.json",
        well_attributes_file: str = "rms/output/wells/well_attributes.json",
        kh_unit: str = None,
        kh_decimal_places: int = 2,
    ):
        super().__init__()

        self._data_models = {
            ensemble: WellCompletionsDataModel(
                ensemble_name=ensemble,
                ensemble_path=webviz_settings.shared_settings["scratch_ensembles"][
                    ensemble
                ],
                compdat_file=compdat_file,
                well_connection_status_file=well_connection_status_file,
                zone_layer_mapping_file=zone_layer_mapping_file,
                stratigraphy_file=stratigraphy_file,
                well_attributes_file=well_attributes_file,
                kh_unit=kh_unit,
                kh_decimal_places=kh_decimal_places,
                theme_colors=webviz_settings.theme.plotly_theme["layout"]["colorway"],
            )
            for ensemble in ensembles
        }

        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return [data_model.webviz_store for _, data_model in self._data_models.items()]

    @property
    def tour_steps(self) -> list:
        return layout_tour_steps(self.uuid)

    @property
    def layout(self) -> html.Div:
        return main_layout(
            get_uuid=self.uuid,
            ensembles=list(self._data_models.keys()),
        )

    def set_callbacks(self, app: Dash) -> None:
        plugin_callbacks(app, self.uuid, self._data_models)

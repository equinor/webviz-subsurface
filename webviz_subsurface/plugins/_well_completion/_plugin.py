from typing import Any, Callable, Dict, List, Tuple

from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from webviz_subsurface._models import StratigraphyModel, WellAttributesModel

from ..._providers import EnsembleTableProviderFactory
from ._utils import WellCompletionDataModel
from ._views._well_completion_view import WellCompletionView, WellCompletionViewElement


class WellCompletion(WebvizPluginABC):
    """Vizualizes Eclipse well completions data per well. The data is grouped per well
    and zone and can be filtered according to flexible well categories.

    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`wellcompletiondata_file`:** `.arrow` file with well completion data
    * **`stratigraphy_file`:** `.json` file defining the stratigraphic levels
    * **`well_attributes_file`:** `.json` file with categorical well attributes
    * **`kh_unit`:** e.g. mD·m, will try to extract from eclipse files if defaulted
    * **`kh_decimal_places`:**

    ---
    The minimum requirement is to define `ensembles`.

    **Well Completion data**

    `wellcompletiondata_file` is a path to an `.arrow` file stored per realization (e.g in \
    `share/results/tables/wellcompletiondata.arrow`). This file can be exported to disk by using the
    `ECL2CSV` forward model in ERT with subcommand `wellcompletiondata`. This forward model will
    read the eclipse `COMPDAT`, but then aggregate from layer to zone according to a given zone ➔
    layer mapping `.lyr` file. If the `use_wellconnstatus` option is used, then the `OP/SH` status
    of each well connection is deduced from `CPI` summary data which in som cases is more accurate
    than the data coming from parsing the schedule file (f.ex if connections are changing status in
    an `ACTION` keyword).

    The reason for doing the layer ➔ zone aggregation in the FMU post processing instead of in the
    plugin is to improve speed and to open up for more functionality.

    **Stratigraphy file**

    The `stratigraphy_file` file is intended to be generated per realization by an internal \
    RMS script as part of the FMU workflow, but can also be set up manually and copied to each
    realization. The stratigraphy is a tree structure, where each node has a name, an optional
    `color` parameter, and an optional `subzones` parameter which itself is a list of the same
    format.
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

    class Ids(StrEnum):
        WELL_COMPLETION_VIEW = "well-completion-view"

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        ensembles: list,
        wellcompletiondata_file: str = "share/results/tables/wellcompletiondata.arrow",
        stratigraphy_file: str = "rms/output/zone/stratigraphy.json",
        well_attributes_file: str = "rms/output/wells/well_attributes.json",
    ):

        super().__init__(stretch=True)
        factory = EnsembleTableProviderFactory.instance()

        self._data_models = {}
        for ens_name in ensembles:
            ens_path = webviz_settings.shared_settings["scratch_ensembles"][ens_name]
            self._data_models[ens_name] = WellCompletionDataModel(
                ensemble_path=ens_path,
                wellcompletion_provider=factory.create_from_per_realization_arrow_file(
                    ens_path, wellcompletiondata_file
                ),
                stratigraphy_model=StratigraphyModel(
                    ens_name, ens_path, stratigraphy_file
                ),
                well_attributes_model=WellAttributesModel(
                    ens_name, ens_path, well_attributes_file
                ),
                theme_colors=webviz_settings.theme.plotly_theme["layout"]["colorway"],
            )

        self.add_view(
            WellCompletionView(self._data_models),
            self.Ids.WELL_COMPLETION_VIEW,
        )

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return [
            webviz_store_tuple
            for _, ens_data_model in self._data_models.items()
            for webviz_store_tuple in ens_data_model.webviz_store
        ]

    @property
    def tour_steps(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": self.view(self.Ids.WELL_COMPLETION_VIEW)
                .settings_group(WellCompletionView.Ids.SETTINGS)
                .get_unique_id(),
                "content": "Menu for selecting ensemble and other options",
            },
            {
                "id": self.view(self.Ids.WELL_COMPLETION_VIEW)
                .view_element(WellCompletionView.Ids.VIEW_ELEMENT)
                .component_unique_id(WellCompletionViewElement.Ids.COMPONENT),
                "content": "Visualization of the well completions. "
                "Time slider for selecting which time steps to display. "
                "Different vizualisation and filtering alternatives are available "
                "in the upper right corner.",
            },
        ]

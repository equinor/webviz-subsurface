from pathlib import Path
from typing import Callable, List, Optional, Tuple

import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, WebvizSettings

from ._business_logic import SwatinitQcDataModel
from ._callbacks import plugin_callbacks
from ._layout import plugin_main_layout


class SwatinitQC(WebvizPluginABC):
    """This plugin is used to visualize the output from [check_swatinit]\
(https://fmu-docs.equinor.com/docs/subscript/scripts/check_swatinit.html) which is a QC tool
for Water Initialization in Eclipse runs when the `SWATINIT` keyword has been used. It is used to
quantify how much the volume changes from `SWATINIT` to `SWAT` at time zero in the dynamical model,
and help understand why it changes.

---
* **`csvfile`:** Path to an csvfile from check_swatinit. The path should be relative to the runpath
if ensemble and realization is given as input, if not the path needs to be absolute.
* **`ensemble`:** Which ensemble in `shared_settings` to visualize.
* **`realization`:** Which realization to pick from the ensemble
* **`faultlines`**: A csv file containing faultpolygons to be visualized together with the map view.
Export format from [xtgeo.xyz.polygons.dataframe](
https://xtgeo.readthedocs.io/en/latest/apiref/xtgeo.xyz.polygons.html#xtgeo.xyz.polygons.Polygons.dataframe
) \
[(example file)](\
https://github.com/equinor/webviz-subsurface-testdata/blob/master/01_drogon_ahm/\
realization-0/iter-0/share/results/polygons/toptherys--gl_faultlines_extract_postprocess.csv).

---
The `csvfile` can be generated by running the [CHECK_SWATINIT](https://fmu-docs.equinor.com/\
docs/ert/reference/forward_models.html?highlight=swatinit#CHECK_SWATINIT) forward model in ERT,
or with the "check_swatinit" command line tool.

"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile: str = "share/results/tables/check_swatinit.csv",
        ensemble: Optional[str] = None,
        realization: Optional[int] = None,
        faultlines: Optional[Path] = None,
    ) -> None:
        super().__init__()

        self._datamodel = SwatinitQcDataModel(
            webviz_settings=webviz_settings,
            csvfile=csvfile,
            ensemble=ensemble,
            realization=realization,
            faultlines=faultlines,
        )
        self.add_webvizstore()
        self.set_callbacks()

    @property
    def layout(self) -> wcc.Tabs:
        return plugin_main_layout(self.uuid, self._datamodel)

    def set_callbacks(self) -> None:
        plugin_callbacks(self.uuid, self._datamodel)

    def add_webvizstore(self) -> List[Tuple[Callable, List[dict]]]:
        return self._datamodel.webviz_store

from pathlib import Path
from typing import Callable, List, Optional, Tuple

import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, WebvizSettings

from webviz_subsurface._datainput.fmu_input import find_sens_type
from webviz_subsurface._providers import EnsembleTableProviderFactory

from ._error import error
from ._plugin_ids import PlugInIDs
from .shared_settings import PickTab


class SwatinitQC(WebvizPluginABC):
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile: str = "share/results/tables/check_swatinit.csv",
        ensemble: Optional[str] = None,
        realization: Optional[int] = None,
        faultlines: Path = None,
    ) -> None:
        super().__init__()

        self._datamodel = SwatinitQcDataModel(
            webviz_settings=webviz_settings,
            csvfile=csvfile,
            ensemble=ensemble,
            realization=realization,
            faultlines=faultlines,
        )

        self.add_store(PlugInIDs.Stores.Shared.PICK_VIEW)
        self.add_shared_settings_group(PickTab)

        self.add_store(PlugInIDs.Stores.Shared.EQLNUM)
        self.add_shared_settings_group()

    @property
    def layout(self) -> wcc.Tabs:
        return plugin_main_layout(self.uuid, self._datamodel)

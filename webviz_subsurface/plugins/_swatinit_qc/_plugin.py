from pathlib import Path
from typing import Callable, List, Optional, Tuple

import webviz_core_components as wcc
from webviz_config import WebvizPluginABC, WebvizSettings

from ._error import error
from ._plugin_ids import PlugInIDs
from ._swatint import SwatinitQcDataModel
from .views import OverviewTabLayout, TabMaxPcInfoLayout, TabQqPlotLayout


class SwatinitQC(WebvizPluginABC):
    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile: str = "share/results/tables/check_swatinit.csv",
        ensemble: Optional[str] = None,
        realization: Optional[int] = None,
        faultlines: Path = None,
    ) -> None:
        super().__init__(stretch=True)

        self._datamodel = SwatinitQcDataModel(
            webviz_settings=webviz_settings,
            csvfile=csvfile,
            ensemble=ensemble,
            realization=realization,
            faultlines=faultlines,
        )
        self.error_message = ""

        # Stores used in Overview tab
        self.add_store(
            PlugInIDs.Stores.Overview.BUTTON, WebvizPluginABC.StorageType.SESSION
        )

        # Stores used in Water tab
        self.add_store(
            PlugInIDs.Stores.Water.QC_VIZ, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.EQLNUM, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.COLOR_BY, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.MAX_POINTS, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.QC_FLAG, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Water.SATNUM, WebvizPluginABC.StorageType.SESSION
        )

        # Stores used in Capilaty tab
        self.add_store(
            PlugInIDs.Stores.Capilary.SPLIT_TABLE_BY,
            WebvizPluginABC.StorageType.SESSION,
        )
        self.add_store(
            PlugInIDs.Stores.Capilary.MAX_PC_SCALE, WebvizPluginABC.StorageType.SESSION
        )
        self.add_store(
            PlugInIDs.Stores.Capilary.EQLNUM, WebvizPluginABC.StorageType.SESSION
        )

        self.add_view(
            OverviewTabLayout(self._datamodel),
            PlugInIDs.SwatinitViews.OVERVIEW,
            PlugInIDs.SwatinitViews.GROUP_NAME,
        )
        self.add_view(
            TabQqPlotLayout(self._datamodel),
            PlugInIDs.SwatinitViews.WATER,
            PlugInIDs.SwatinitViews.GROUP_NAME
        )
        self.add_view(
            TabMaxPcInfoLayout(self._datamodel),
            PlugInIDs.SwatinitViews.WATER,
            PlugInIDs.SwatinitViews.GROUP_NAME
        )

    @property
    def layout(self) -> wcc.Tabs:
        return error(self.error_message)

    def add_webvizstore(self) -> List[Tuple[Callable, List[dict]]]:
        return self._datamodel.webviz_store


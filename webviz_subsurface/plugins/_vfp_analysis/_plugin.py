from typing import Optional

from webviz_config import WebvizPluginABC, WebvizSettings

from ._business_logic import VfpDataModel
from ._plugin_ids import PluginIds
from .views import VfpView


class VfpAnalysis(WebvizPluginABC):
    """Vizualises VFP curves"""

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        csvfile: str = "share/results/tables/vfp.csv",
        ensemble: Optional[str] = None,
        realization: Optional[int] = None,
    ) -> None:
        super().__init__()

        self._datamodel = VfpDataModel(
            webviz_settings=webviz_settings,
            csvfile=csvfile,
            ensemble=ensemble,
            realization=realization,
        )

        self.add_view(VfpView(self._datamodel), PluginIds.Views.VFP_VIEW)

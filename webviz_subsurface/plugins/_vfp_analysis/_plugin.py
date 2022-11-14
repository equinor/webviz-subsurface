from typing import Callable, Dict, List, Optional, Tuple

from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from ._utils import VfpDataModel
from ._views._vfp_view import VfpView


class VfpAnalysis(WebvizPluginABC):
    """Vizualises VFP curves"""

    class Ids(StrEnum):
        VFP_VIEW = "vpf-view"

    def __init__(
        self,
        webviz_settings: WebvizSettings,
        vfp_file_pattern: str = "share/results/tables/vfp/*.arrow",
        ensemble: Optional[str] = None,
        realization: Optional[int] = None,
    ) -> None:
        super().__init__(stretch=True)

        self._datamodel = VfpDataModel(
            webviz_settings=webviz_settings,
            vfp_file_pattern=vfp_file_pattern,
            ensemble=ensemble,
            realization=realization,
        )

        self.add_view(VfpView(self._datamodel), self.Ids.VFP_VIEW)

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        return self._datamodel.webviz_store

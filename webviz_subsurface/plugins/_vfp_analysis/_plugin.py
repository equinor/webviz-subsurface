from typing import Callable, Dict, List, Optional, Tuple

from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.utils import StrEnum

from ._utils import VfpDataModel
from ._views._vfp_view import VfpView


class VfpAnalysis(WebvizPluginABC):
    """Vizualizes VFP curves.

    ---

    * **`vfp_file_pattern`:** File pattern for where to search for vfp arrow files. The path
    should be relative to the runpath if ensemble and realization is given as input, if not
    the path needs to be absolute.
    * **`ensemble`:** Which ensemble in `shared_settings` to use.
    * **`realization`:** Which realization to pick from the ensemble.
    ---

    The plugin uses an `.arrow` representation of the VFP curves, which can be exported to disk by
    using the `ECL2CSV` forward model in ERT with subcommand `vfp`.

    So far, the plugin only vizualizes VFPPROD curves, but the plan is to extend it also to
    VFPINJ curves soon.

    """

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

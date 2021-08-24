from typing import List, Tuple, Callable, Dict
import glob

import pandas as pd
import dash
import dash_html_components as html
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.webviz_store import webvizstore

from ..._models import EnsembleSetModel
from ..._models import caching_ensemble_set_model_factory
from .views import main_view
from .controllers import controllers


class NetworkAnalysis(WebvizPluginABC):
    """This plugins vizualizes network control modes and pressure.

    ---
    * **`ensembles`:** Which ensembles in `shared_settings` to include.
    * **`sampling`:** Frequency for the data sampling.
    * **`gruptree_file`:** `.csv` with gruptree information.
    ---

    **Summary data**

    This plugin uses data from these summary keywords:
    * WMCTL:
    * GMCTP:
    * FMCTP
    * WTHP:
    * GPR:

    It is recommended to use monthly sampling of summary data.

    **GRUPTREE input**

    `gruptree_file` is a path to a file stored per realization (e.g. in \
    `share/results/tables/gruptree.csv"`).

    The `gruptree_file` file can be dumped to disk per realization by a forward model in ERT that
    wraps the command `ecl2csv compdat input_file -o output_file` (requires that you have `ecl2df`
    installed).
    [Link to ecl2csv compdat documentation.](https://equinor.github.io/ecl2df/usage/gruptree.html)

    Gruptrees changing with time is supported, but trees that are varying
    over realizations is not supported.
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        sampling: str = "monthly",
        gruptree_file: str = "share/results/tables/gruptree.csv",
    ):

        super().__init__()
        self.time_index = sampling
        self.gruptree_file = gruptree_file
        self.ens_paths = {
            ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
            for ens in ensembles
        }
        self.emodel: EnsembleSetModel = (
            caching_ensemble_set_model_factory.get_or_create_model(
                ensemble_paths={
                    ens: webviz_settings.shared_settings["scratch_ensembles"][ens]
                    for ens in ensembles
                },
                time_index=self.time_index,
                column_keys=[
                    "WMCTL:*",
                    "GMCT*",
                    "FMCT*",
                    "WTHP:*",
                    "WBHP:*",
                    "GPR:*",
                ],
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.ensembles = list(self.smry["ENSEMBLE"].unique())
        self.gruptree = read_gruptree_files(self.ens_paths, self.gruptree_file)
        self.theme = webviz_settings.theme

        self.set_callbacks(app)

    def add_webvizstore(self) -> List[Tuple[Callable, List[Dict]]]:
        functions: List[Tuple[Callable, List[Dict]]] = self.emodel.webvizstore
        functions.append(
            (
                read_gruptree_files,
                [{"ens_paths": self.ens_paths, "gruptree_file": self.gruptree_file}],
            )
        )
        return functions

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("layout"),
                "content": "Dashboard vizualizing Eclipse network control modes and pressures.",
            },
            {
                "id": self.uuid("selections_layout"),
                "content": "Menu for selecting ensemble, node and various plotting options.",
            },
            {
                "id": self.uuid("graph"),
                "content": "Vizualisation of network control modes and pressures.",
            },
        ]

    @property
    def layout(self) -> html.Div:
        return html.Div(
            children=[
                # clientside_stores(get_uuid=self.uuid),
                main_view(get_uuid=self.uuid, ensembles=self.ensembles),
            ],
        )

    def set_callbacks(self, app: dash.Dash) -> None:
        controllers(
            app=app,
            get_uuid=self.uuid,
            smry=self.smry,
            gruptree=self.gruptree,
            theme=self.theme,
        )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
@webvizstore
def read_gruptree_files(ens_paths: Dict[str, str], gruptree_file: str) -> pd.DataFrame:
    """Searches for gruptree files on the scratch disk. These
    files can be exported in the FMU workflow using the ECL2CSV
    forward job with subcommand gruptree

    If one file is found per ensemble this file is assumed to be
    valid for the whole ensemble.

    If BRANPROP is in the KEYWORDS, GRUPTREE rows are filtered out
    """
    df = pd.DataFrame()
    for ens_name, ens_path in ens_paths.items():
        for filename in glob.glob(f"{ens_path}/{gruptree_file}"):
            df_ens = pd.read_csv(filename)
            df_ens["ENSEMBLE"] = ens_name
            df = pd.concat([df, df_ens])
            break
    if "BRANPROP" in df.KEYWORD.unique():
        df = df[df.KEYWORD != "GRUPTREE"]
    return df

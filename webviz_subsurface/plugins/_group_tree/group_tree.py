from typing import List, Dict, Tuple, Callable
import glob

import pandas as pd
import dash
import dash_html_components as html

from webviz_config.webviz_store import webvizstore
from webviz_config import WebvizPluginABC
from webviz_config import WebvizSettings

from ..._models import EnsembleSetModel
from ..._models import caching_ensemble_set_model_factory
from .controllers import controllers
from .views import main_view


class GroupTree(WebvizPluginABC):
    """This plugin vizualizes the network tree and displays pressures,
    rates and other network related information.

    ---
    * **`ensembles`:** Which ensembles in `shared_settings` to include.
    * **`gruptree_file`:** `.csv` with gruptree information.
    * **`time_index`:** Frequency for the data sampling.
    ---

    **Summary data**

    This plugin need the following summary vectors to be exported:
    * FOPR, FWPR and FGPR
    * GOPR, GWPR, GGPR and GPR for all nodes in the network
    * WOPR, WWPR, WGPR, WTHP and WBHP for all wells

    **GRUPTREE input**

    `gruptree_file` is a path to a file stored per realization (e.g. in \
    `share/results/tables/gruptree.csv"`).

    The `gruptree_file` file can be dumped to disk per realization by a forward model in ERT that
    wraps the command `ecl2csv compdat input_file -o output_file` (requires that you have `ecl2df`
    installed).
    [Link to ecl2csv compdat documentation.](https://equinor.github.io/ecl2df/usage/gruptree.html)

    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        gruptree_file: str = "share/results/tables/gruptree.csv",
        time_index: str = "monthly",
    ):
        super().__init__()
        self.ensembles = ensembles
        self.gruptree_file = gruptree_file
        self.time_index = time_index
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
                    "FOPR",
                    "FGPR",
                    "FWPR",
                    "FWIR",
                    "FPR",
                    "GOPR:*",
                    "GGPR:*",
                    "GWPR:*",
                    "GPR:*",
                    "WOPR:*",
                    "WGPR:*",
                    "WWPR:*",
                    "WTHP:*",
                    "WBHP:*",
                ],
            )
        )
        self.smry = self.emodel.get_or_load_smry_cached()
        self.gruptree = read_gruptree_files(self.ens_paths, self.gruptree_file)
        self.smry["DATE"] = pd.to_datetime(self.smry["DATE"]).dt.date
        self.gruptree["DATE"] = pd.to_datetime(self.gruptree["DATE"]).dt.date

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
                "content": "Dashboard vizualizing Eclipse network tree.",
            },
            {
                "id": self.uuid("selections_layout"),
                "content": "Menu for selecting ensemble and other options.",
            },
            {
                "id": self.uuid("grouptree_wrapper"),
                "content": "Vizualisation of network tree.",
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
        )


@webvizstore
def read_gruptree_files(ens_paths: Dict[str, str], gruptree_file: str) -> pd.DataFrame:
    """Searches for gruptree files on the scratch disk. These
    files can be exported in the FMU workflow using the ECL2CSV
    forward job with subcommand gruptree.

    If one file is found per ensemble this file is assumed to be
    valid for the whole ensemble.

    If BRANPROP is in the KEYWORDS, GRUPTREE rows are filtered out
    """
    df = pd.DataFrame()
    for ens_name, ens_path in ens_paths.items():
        for filename in glob.glob(f"{ens_path}/{gruptree_file}"):
            df_ens = pd.read_csv(filename)
            df_ens["ENSEMBLE"] = ens_name
            if "BRANPROP" in df_ens["KEYWORD"].unique():
                df_ens = df_ens[df_ens["KEYWORD"] != "GRUPTREE"]
            df = pd.concat([df, df_ens])
            break
    df = df.where(pd.notnull(df), None)
    return df

from typing import Callable, Dict, List, Tuple

import dash
import pandas as pd
from dash import html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.webviz_store import webvizstore

from ..._datainput.fmu_input import scratch_ensemble
from ..._models import EnsembleSetModel, caching_ensemble_set_model_factory
from .controllers import controllers
from .group_tree_data import GroupTreeData
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

    This plugin needs the following summary vectors to be exported:
    * FOPR, FWPR, FOPR, FWIR and FGIR
    * GPR for all group nodes in the network
    * GOPR, GWPR and GGPR for all group nodes in the production network \
    (GOPRNB etc for BRANPROP trees)
    * GGIR and/or GWIR for all group nodes in the injection network
    * WSTAT, WTHP, WBHP, WMCTL for all wells
    * WOPR, WWPR, WGPR for all producers
    * WWIR and/or WGIR for all injectors

    **GRUPTREE input**

    `gruptree_file` is a path to a file stored per realization (e.g. in \
    `share/results/tables/gruptree.csv"`).

    The `gruptree_file` file can be dumped to disk per realization by the `ECL2CSV` forward
    model with subcommand `gruptree`:
    [Link to ECL2CSV](https://fmu-docs.equinor.com/docs/ert/reference/forward_models.html).

    The forward model uses `ecl2df` to export a table representation of the Eclipse network:
    [Link to ecl2csv gruptree documentation.](https://equinor.github.io/ecl2df/usage/gruptree.html).

    **time_index**

    This is the sampling interval of the summary data. It is `yearly` by default, but can be set
    to `monthly` if needed.
    """

    def __init__(
        self,
        app: dash.Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        gruptree_file: str = "share/results/tables/gruptree.csv",
        time_index: str = "yearly",
    ):
        super().__init__()
        assert time_index in [
            "monthly",
            "yearly",
        ], "time_index must be monthly or yearly"
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
                time_index="monthly",
            )
        )
        smry = self.emodel.get_or_load_smry_cached()
        gruptree = read_gruptree_files(self.ens_paths, self.gruptree_file)
        smry["DATE"] = pd.to_datetime(smry["DATE"])
        gruptree["DATE"] = pd.to_datetime(gruptree["DATE"])

        if time_index == "yearly":
            smry = smry[smry["DATE"].dt.is_year_start]

        self.grouptreedata = GroupTreeData(smry, gruptree)

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
                "id": self.uuid("filters_layout"),
                "content": "Menu for filtering options.",
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
        controllers(app=app, get_uuid=self.uuid, grouptreedata=self.grouptreedata)


@webvizstore
def read_gruptree_files(ens_paths: Dict[str, str], gruptree_file: str) -> pd.DataFrame:
    """Searches for gruptree files on the scratch disk. These
    files can be exported in the FMU workflow using the ECL2CSV
    forward model with subcommand gruptree.
    """
    df = pd.DataFrame()
    for ens_name, ens_path in ens_paths.items():
        df_ens = read_ensemble_gruptree(ens_name, ens_path, gruptree_file)
        df_ens["ENSEMBLE"] = ens_name
        df = pd.concat([df, df_ens])
    return df.where(pd.notnull(df), None)


def read_ensemble_gruptree(
    ens_name: str, ens_path: str, gruptree_file: str
) -> pd.DataFrame:
    """Reads the gruptree file for an ensemble.

    If BRANPROP is found in the KEYWORD column, then GRUPTREE rows
    are filtered out.

    If the trees are equal in every realization, only one realization is kept.
    """

    ens = scratch_ensemble(ens_name, ens_path, filter_file="OK")
    df_files = ens.find_files(gruptree_file)

    if df_files.empty:
        raise ValueError(f"No gruptree file available for ensemble: {ens_name}")

    # Load all gruptree dataframes and check if they are equal
    compare_columns = ["DATE", "CHILD", "KEYWORD", "PARENT"]
    df_prev = pd.DataFrame()
    dataframes = []
    gruptrees_are_equal = True
    for i, row in df_files.iterrows():
        df_real = pd.read_csv(row["FULLPATH"])

        if "BRANPROP" in df_real["KEYWORD"].unique():
            df_real = df_real[df_real["KEYWORD"] != "GRUPTREE"]
        if (
            i > 0
            and gruptrees_are_equal
            and not df_real[compare_columns].equals(df_prev)
        ):
            gruptrees_are_equal = False
        else:
            df_prev = df_real[compare_columns].copy()

        df_real["REAL"] = row["REAL"]
        dataframes.append(df_real)
    df_all = pd.concat(dataframes)

    # Return either one or all realization in a common dataframe
    if gruptrees_are_equal:
        return df_all[df_all["REAL"] == df_all["REAL"].min()]
    return df_all

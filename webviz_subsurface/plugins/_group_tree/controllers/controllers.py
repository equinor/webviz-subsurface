from typing import Callable, Optional, Any, Tuple, List, Dict
import json
import pandas as pd
import dash
from dash.dependencies import Input, Output, State, ALL
import plotly.graph_objects as go

from webviz_config import WebvizConfigTheme
import webviz_subsurface_components

from ..utils.utils import create_ensemble_dataset


def controllers(
    app: dash.Dash,
    get_uuid: Callable,
    smry: pd.DataFrame,
    gruptree: pd.DataFrame,
) -> None:
    @app.callback(
        Output({"id": get_uuid("controls"), "element": "realization"}, "options"),
        Output({"id": get_uuid("controls"), "element": "realization"}, "value"),
        Input({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _update_realization_dropdown(
        ensemble_name: str,
    ) -> Tuple[List[Dict[str, Any]], Optional[int]]:
        print("update dropdown")
        smry_ens = smry[smry.ENSEMBLE == ensemble_name].copy()
        smry_ens.dropna(how="all", axis=1, inplace=True)
        realizations = [
            {"label": real, "value": real} for real in sorted(smry_ens.REAL.unique())
        ]
        return realizations, 0

    @app.callback(
        Output(get_uuid("grouptree_wrapper"), "children"),
        Input({"id": get_uuid("controls"), "element": "mean_or_single_real"}, "value"),
        Input({"id": get_uuid("controls"), "element": "realization"}, "value"),
        State({"id": get_uuid("controls"), "element": "ensemble"}, "value"),
    )
    def _render_grouptree(
        mean_or_single_real: str, real: int, ensemble_name: str
    ) -> list:
        print("render gruptree...")

        smry_ens = smry[smry.ENSEMBLE == ensemble_name].copy()
        smry_ens.dropna(how="all", axis=1, inplace=True)
        if mean_or_single_real == "plot_mean":
            smry_ens = smry_ens.groupby("DATE").mean().reset_index()
        elif mean_or_single_real == "single_real":
            smry_ens = smry_ens[smry_ens.REAL == real]
        else:
            raise ValueError(f"Not valid option :{mean_or_single_real}")

        smry_ens["DATE"] = pd.to_datetime(smry_ens["DATE"]).dt.date
        gruptree["DATE"] = pd.to_datetime(gruptree["DATE"]).dt.date

        data = json.load(
            create_ensemble_dataset(
                ensemble_name,
                smry_ens,
                gruptree[gruptree.ENSEMBLE == ensemble_name],
            )
        )
        return [
            webviz_subsurface_components.GroupTree(id="grouptree", data=data),
        ]

    @app.callback(
        Output(
            {"id": get_uuid("controls"), "element": "single_real_options"},
            "style",
        ),
        Input(
            {"id": get_uuid("controls"), "element": "mean_or_single_real"},
            "value",
        ),
    )
    def _show_hide_single_real_options(mean_or_single_real: str) -> Dict:
        if mean_or_single_real == "plot_mean":
            return {"display": "none"}
        return {"display": "block"}

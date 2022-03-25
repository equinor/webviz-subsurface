from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from webviz_subsurface._models import GruptreeModel
from webviz_subsurface._providers import EnsembleSummaryProvider


class EnsembleWellAnalysisData:
    """This class holds the summary data provider."""

    def __init__(
        self,
        ensemble_name: str,
        provider: EnsembleSummaryProvider,
        gruptree_model: GruptreeModel,
        filter_out_startswith: Optional[str] = None,
    ):
        self._ensemble_name = ensemble_name
        self._gruptree_model = gruptree_model
        self._provider = provider
        self._vector_names = self._provider.vector_names()
        self._realizations = self._provider.realizations()
        self._wells: List[str] = [
            vec.split(":")[1] for vec in self._vector_names if vec.startswith("WOPT:")
        ]
        if filter_out_startswith is not None:
            self._wells = [
                well
                for well in self._wells
                if not well.startswith(filter_out_startswith)
            ]

        well_sumvecs = [vec for vec in self._vector_names if vec.startswith("W")]
        group_sumvecs = [vec for vec in self._vector_names if vec.startswith("GPR:")]
        self._smry = provider.get_vectors_df(well_sumvecs + group_sumvecs, None)

    @property
    def webviz_store(self) -> Tuple[Callable, List[Dict]]:
        return self._gruptree_model.webviz_store

    @property
    def summary_data(self) -> pd.DataFrame:
        return self._smry

    @property
    def realizations(self) -> List[int]:
        return self._realizations

    @property
    def wells(self) -> List[str]:
        return self._wells

    def get_dataframe_melted(self, well_sumvec: str) -> pd.DataFrame:
        """Returns a dataframe on long form consisting of these columns:
        * WELL
        * well_sumvec (f.ex WOPT)
        * ENSEMBLE
        """
        sumvecs = [f"{well_sumvec}:{well}" for well in self._wells]
        df = self._smry[["REAL", "DATE"] + sumvecs]
        df = df[df["DATE"] == df["DATE"].max()]
        df_melted = pd.melt(
            df, value_vars=sumvecs, var_name="WELL", value_name=well_sumvec
        )
        df_melted["WELL"] = df_melted.agg(
            lambda x: f"{x['WELL'].split(':')[1]}", axis=1
        )
        df_melted["ENSEMBLE"] = self._ensemble_name
        return df_melted

    def get_node_info(self, node: str, node_type: str = "well") -> Dict[str, Any]:
        """Returns a list of dictionaries containing the network nodes
        ending in the input node, with from_date and end_date. If end_date
        is None it means that the network is valid for the rest of the
        simulations.
        Dict[str, Any]
        The output has the form:
        {
            "name": "A1",
            "type: "well",
            "ctrlmode_sumvec": "WMCTL:A1",
            "networks: [
                {
                    "start_date": "2018-01-01",
                    "end_date": "2018-05-01",
                    "nodes": [
                        {
                            "name": "A1",
                            "label": "THP"
                            "pressure_sumvec": "WTHP:A1"
                            "type": "well"
                        },
                        ...
                    ],
                },
                ...
            ]
        }
        """
        gruptree_df = self._gruptree_model.dataframe
        if gruptree_df.empty:
            return {
                "name": node,
                "type": node_type,
                "ctrlmode_sumvec": _get_ctrlmode_sumvec(node_type, node),
                "networks": [
                    {
                        "start_date": self._smry["DATE"].min(),
                        "end_date": None,
                        "nodes": [_get_node_field(node_type, node)],
                    }
                ],
            }

        node_networks: List[Dict[str, Any]] = []
        prev_nodelist: List[Dict[str, Any]] = []
        for date, df in gruptree_df.groupby("DATE"):
            nodelist = _get_nodelist(df, node_type, node)
            remaining_dates = gruptree_df[gruptree_df["DATE"] > date].DATE
            if remaining_dates.empty:
                next_date = None
            else:
                next_date = remaining_dates.min()

            if nodelist != prev_nodelist:
                node_networks.append(
                    {"start_date": date, "end_date": next_date, "nodes": nodelist}
                )
                prev_nodelist = nodelist
            else:
                if node_networks:
                    node_networks[-1]["end_date"] = next_date
        return {
            "name": node,
            "type": node_type,
            "ctrlmode_sumvec": _get_ctrlmode_sumvec(node_type, node),
            "networks": node_networks,
        }


def _get_nodelist(df: pd.DataFrame, node_type: str, node: str) -> List[Dict[str, str]]:
    """Returns a list of node dictionaries ending up in the input
    node. The input dataframe has only one date.

    The function is recursively getting all the nodes ending up in
    the node which the function was called from the outside.

    For wells, both THP and BHP nodes are added
    """
    if node == "FIELD":
        return [_get_node_field(node_type, node)]

    child_row = df[df.CHILD == node]

    if child_row.empty:
        return []
    if child_row.shape[0] > 1:
        raise ValueError(
            f"There can be maximum one row per child per date: {child_row}"
        )
    if is_terminal_node(node, child_row):
        return [_get_node_field("terminal_node", node)]
    parent = child_row.PARENT.values[0]
    nodelist = [_get_node_field(node_type, node)]
    if node_type == "well":
        nodelist.append(_get_node_field("well_bhp", node))
    return nodelist + _get_nodelist(df, "field_group", parent)


def is_terminal_node(node: str, row: pd.Series) -> bool:
    """Desc"""
    if node == "FIELD":
        return True
    if (
        "TERMINAL_PRESSURE" in row
        and row["TERMINAL_PRESSURE"].values[0] is not None
        and not np.isnan(row["TERMINAL_PRESSURE"].values[0])
    ):
        return True
    return False


def _get_node_field(node_type: str, node: str) -> Dict[str, str]:
    """Returns a dictionary with info about a single node:
    * Name
    * Label to be used in pressure plot
    * Type: well, well_bhp or field_group
    """
    if node_type in ["field_group", "terminal_node"]:
        return {
            "name": node,
            "label": node,
            "type": node_type,
            "pressure": f"GPR:{node}",
        }
    if node_type == "well":
        return {
            "name": node,
            "label": "THP",
            "type": "well",
            "pressure": f"WTHP:{node}",
        }
    if node_type == "well_bhp":
        return {
            "name": node,
            "label": "BHP",
            "type": "well_bhp",
            "pressure": f"WBHP:{node}",
        }
    raise ValueError(f"Node type {node_type} not implemented.")


def _get_ctrlmode_sumvec(node_type: str, node: str) -> str:
    """Returns the control mode sumvec for a given node type
    and node name. Only production network implemented so far.
    """
    if node == "FIELD":
        return "FMCTP"
    if node_type == "well":
        return f"WMCTL:{node}"
    if node_type == "field_group":
        return f"GMCTP:{node}"
    raise ValueError(f"Node type {node_type} not implemented")

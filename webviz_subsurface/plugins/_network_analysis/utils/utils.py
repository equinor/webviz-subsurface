import glob
from typing import List, Dict, Any

import pandas as pd
import numpy as np


def get_node_info(
    gruptree: pd.DataFrame, node_type: str, node: str, start_date: str
) -> Dict[str, Any]:
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
                        "type": "well
                    },
                    ...
                ],
            },
            ...
        ]
    }
    """
    if gruptree.empty:
        return {
            "name": node,
            "type": node_type,
            "ctrlmode_sumvec": _get_ctrlmode_sumvec(node_type, node),
            "networks": [
                {
                    "start_date": start_date,
                    "end_date": None,
                    "nodes": [get_node_field(node_type, node)],
                }
            ],
        }

    node_networks: List[Dict[str, Any]] = []
    prev_nodelist: List[Dict[str, Any]] = []
    for date, df in gruptree.groupby("DATE"):
        nodelist = _get_nodelist(df, node_type, node)
        remaining_dates = gruptree[gruptree.DATE > date].DATE
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
    if node == "FIELD" or (
        "TERMINAL_PRESSURE" in df.columns
        and not np.isnan(child_row["TERMINAL_PRESSURE"].values[0])
    ):
        return [_get_node_field("terminal_node", node)]

    parent = child_row.PARENT.values[0]
    nodelist = [_get_node_field(node_type, node)]
    if node_type == "well":
        nodelist.append(_get_node_field("well_bhp", node))
    return nodelist + _get_nodelist(df, "field_group", parent)


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

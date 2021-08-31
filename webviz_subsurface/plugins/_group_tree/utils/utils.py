from typing import List, Dict
import time
import io
import json
import pandas as pd
import numpy as np
import math
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def create_ensemble_dataset(
    ensemble: str,
    smry: pd.DataFrame,
    gruptrees: pd.DataFrame,
) -> io.BytesIO:
    """Description"""
    t1 = time.time()
    trees = []

    # loop trees
    for tree_date, df_gruptree in gruptrees.groupby("DATE"):
        next_tree_date = gruptrees[gruptrees.DATE > tree_date].DATE.min()
        if pd.isna(next_tree_date):
            next_tree_date = smry.DATE.max()
        smry_in_datespan = smry[
            (smry.DATE >= tree_date) & (smry.DATE < next_tree_date)
        ].copy()
        dates = list(smry_in_datespan.DATE.unique())
        trees.append(
            {
                "dates": [date.strftime("%Y-%m-%d") for date in dates],
                "tree": extract_tree(df_gruptree, "FIELD", smry_in_datespan, dates),
            }
        )

    with open(f"/private/olind/webviz/grouptree_{ensemble}.json", "w") as handle:
        json.dump(trees, handle)
        print("output exported")
    print(f"create_ensemble_dataset( run in {round(time.time()-t1, 0)} seconds.")
    return io.BytesIO(json.dumps(trees).encode())


def extract_tree(
    df_gruptree: pd.DataFrame, node: str, smry_in_datespan: pd.DataFrame, dates: list
) -> dict:
    """Description"""
    nodedict = get_node_data(df_gruptree, node)
    node_values = get_node_smry(node, nodedict["KEYWORD"], smry_in_datespan, dates)
    grupnet_info = get_grupnet_info(nodedict)
    result = {
        "name": node,
        "pressure": node_values["pressure"],
        "oilrate": node_values["oilrate"],
        "waterrate": node_values["waterrate"],
        "gasrate": node_values["gasrate"],
        "grupnet": get_grupnet_info(nodedict),
    }
    children = list(df_gruptree[df_gruptree.PARENT == node].CHILD.unique())
    if children:
        result["children"] = [
            extract_tree(df_gruptree, child_node, smry_in_datespan, dates)
            for child_node in df_gruptree[df_gruptree.PARENT == node].CHILD.unique()
        ]
    return result


def get_grupnet_info(nodedict: dict) -> str:
    """Description"""
    if "VFP_TABLE" not in nodedict:
        return ""
    if nodedict["VFP_TABLE"] in [None, 9999]:
        return ""
    return "VFP " + str(int(nodedict["VFP_TABLE"]))


def get_node_data(df_gruptree: pd.DataFrame, node: str) -> dict:
    """Description"""
    if node not in list(df_gruptree.CHILD):
        raise ValueError(f"Node {node} not found in gruptree table.")
    df_node = df_gruptree[df_gruptree.CHILD == node]
    if df_node.shape[0] > 1:
        raise ValueError(f"Multiple nodes found for {node} in gruptree table.")
    return df_node.to_dict("records")[0]


def get_node_smry(
    node: str, node_type: str, smry_in_datespan: pd.DataFrame, dates: list
) -> Dict[str, List[float]]:
    """Description"""
    if node == "FIELD":
        sumvecs = {
            "oilrate": "FOPR",
            "gasrate": "FGPR",
            "waterrate": "FWPR",
            "pressure": "GPR:FIELD",
        }
    elif node_type in ["GRUPTREE", "BRANPROP"]:
        sumvecs = {
            "oilrate": f"GOPR:{node}",
            "gasrate": f"GGPR:{node}",
            "waterrate": f"GWPR:{node}",
            "pressure": f"GPR:{node}",
        }
    elif node_type == "WELSPECS":
        sumvecs = {
            "oilrate": f"WOPR:{node}",
            "gasrate": f"WGPR:{node}",
            "waterrate": f"WWPR:{node}",
            "pressure": f"WTHP:{node}",
        }
    else:
        raise ValueError(f"Node type {node_type} not implemented")

    for sumvec in sumvecs.values():
        if sumvec not in smry_in_datespan.columns:
            smry_in_datespan[sumvec] = np.nan

    output: Dict[str, List[float]] = {
        "pressure": [],
        "oilrate": [],
        "waterrate": [],
        "gasrate": [],
    }

    # sumvecs = {key: value for key, value in sumvecs.items() if key in smry_in_datespan.columns}

    for date in dates:
        smry_at_date = smry_in_datespan[smry_in_datespan.DATE == date]
        # print(smry_at_date)
        for key, sumvec in sumvecs.items():
            output[key].append(round(smry_at_date[sumvec].values[0], 2))
    return output

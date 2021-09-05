from typing import List, Dict, Optional
import time
import io
import json
import pandas as pd
from webviz_config.common_cache import CACHE


def qc_summary(
    smry: pd.DataFrame, gruptree: pd.DataFrame, ensembles: List[str]
) -> None:
    """Description"""
    missing_sumvecs = []
    for ensemble in ensembles:
        smry_ens = smry[smry.ENSEMBLE == ensemble]
        gruptree_ens = gruptree[gruptree.ENSEMBLE == ensemble]

        for _, row in gruptree_ens.iterrows():
            sumvecs = get_sumvecs_for_node(row["CHILD"], row["KEYWORD"])
            for _, sumvec in sumvecs.items():
                if sumvec not in smry_ens.columns:
                    missing_sumvecs.append(f"{sumvec}, ens: {ensemble}")
    if missing_sumvecs:
        raise ValueError(missing_sumvecs)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_ensemble_real_options(
    smry: pd.DataFrame, ensemble_name: str
) -> List[Dict[str, int]]:
    """Returns a list of realization dropdown options for an ensemble."""
    smry_ens = smry[smry.ENSEMBLE == ensemble_name]
    return [{"label": real, "value": real} for real in sorted(smry_ens.REAL.unique())]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_smry(
    smry: pd.DataFrame, ensemble_name: str, real: Optional[int] = None
) -> pd.DataFrame:
    """Filters the smry dataframe and takes the mean of all summary vectors if no real is given."""
    smry_ens = smry[smry.ENSEMBLE == ensemble_name].copy()
    smry_ens.dropna(how="all", axis=1, inplace=True)

    if real is None:
        return smry_ens.groupby("DATE").mean().reset_index()
    return smry_ens[smry_ens["REAL"] == real]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_gruptree(
    gruptree: pd.DataFrame, ensemble_name: str, real: Optional[int] = None
) -> pd.DataFrame:
    """Description"""

    gruptree_ens = gruptree[gruptree.ENSEMBLE == ensemble_name]

    if real is None or len(gruptree_ens["REAL"].unique()) == 1:
        # This means that the trees are equal for all realizations
        # and no further filtering is necessary
        return gruptree_ens

    # Else: trees are not equal and all trees are stored in the dataframe
    # Filter on realization
    return gruptree_ens[gruptree_ens["REAL"] == real]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def create_grouptree_dataset(
    smry: pd.DataFrame,
    gruptrees: pd.DataFrame,
) -> io.BytesIO:
    """This function creates the dataset that is input to the GroupTree
    component the webviz_subsurface_components.

    A sample dataset can be found here:
    https://github.com/equinor/webviz-subsurface-components/blob/\
    master/react/src/demo/example-data/group-tree.json

    """
    starttime = time.time()
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

    print(f"create_grouptree_dataset used {round(time.time()-starttime, 2)} seconds.")
    return io.BytesIO(json.dumps(trees).encode())


def extract_tree(
    df_gruptree: pd.DataFrame, node: str, smry_in_datespan: pd.DataFrame, dates: list
) -> dict:
    """Extract the tree part of the GroupTree component dataset. This functions
    works recursively and is initially called with the top node of the tree: FIELD."""
    nodedict = get_node_data(df_gruptree, node)
    node_values = get_node_smry(node, nodedict["KEYWORD"], smry_in_datespan, dates)
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
    """Returns the VFP table number for the edge if it exists"""
    if "VFP_TABLE" not in nodedict:
        return ""
    if nodedict["VFP_TABLE"] in [None, 9999]:
        return ""
    return "VFP " + str(int(nodedict["VFP_TABLE"]))


def get_node_data(df_gruptree: pd.DataFrame, node: str) -> dict:
    """Returns the data fields for a specific node as a dictionary"""
    if node not in list(df_gruptree.CHILD):
        raise ValueError(f"Node {node} not found in gruptree table.")
    df_node = df_gruptree[df_gruptree.CHILD == node]
    if df_node.shape[0] > 1:
        df_gruptree.to_csv("/private/olind/webviz/debug.csv")
        raise ValueError(f"Multiple nodes found for {node} in gruptree table.")
    return df_node.to_dict("records")[0]


def get_node_smry(
    node: str, node_type: str, smry_in_datespan: pd.DataFrame, dates: list
) -> Dict[str, List[float]]:
    """Returns the node data for all the dates in a period where the tree
    is constant.
    """
    sumvecs = get_sumvecs_for_node(node, node_type)

    output: Dict[str, List[float]] = {
        "pressure": [],
        "oilrate": [],
        "waterrate": [],
        "gasrate": [],
    }

    for date in dates:
        smry_at_date = smry_in_datespan[smry_in_datespan.DATE == date]
        for key, sumvec in sumvecs.items():
            output[key].append(round(smry_at_date[sumvec].values[0], 2))
    return output


def get_sumvecs_for_node(node: str, node_type: str) -> Dict[str, str]:
    """Returns the summary vectors for node as a dictionary"""
    if node == "FIELD":
        return {
            "oilrate": "FOPR",
            "gasrate": "FGPR",
            "waterrate": "FWPR",
            "pressure": "GPR:FIELD",
        }
    if node_type in ["GRUPTREE", "BRANPROP"]:
        return {
            "oilrate": f"GOPR:{node}",
            "gasrate": f"GGPR:{node}",
            "waterrate": f"GWPR:{node}",
            "pressure": f"GPR:{node}",
        }
    if node_type == "WELSPECS":
        return {
            "oilrate": f"WOPR:{node}",
            "gasrate": f"WGPR:{node}",
            "waterrate": f"WWPR:{node}",
            "pressure": f"WTHP:{node}",
        }
    raise ValueError(f"Node type {node_type} not implemented")

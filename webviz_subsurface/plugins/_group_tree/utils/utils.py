from typing import List, Dict
import io
import json
import pandas as pd
import numpy as np
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def create_ensemble_dataset(
    ensemble: str,
    smry: pd.DataFrame,
    gruptrees: pd.DataFrame,
) -> io.BytesIO:
    """Description"""
    print("Lager datasett ...")

    # smry = load_smry(ensemble, ensemble_path, time_index)
    # df_gruptrees = load_csv(
    #     ensemble_paths={ensemble: ensemble_path}, csv_file=gruptree_file
    # )
    # df_gruptrees.DATE = pd.to_datetime(df_gruptrees.DATE).dt.date
    #
    trees = []

    # loop trees
    for tree_date, df_gruptree in gruptrees.groupby("DATE"):
        next_tree_date = gruptrees[gruptrees.DATE > tree_date].DATE.min()
        if pd.isna(next_tree_date):
            next_tree_date = smry.DATE.max()
        smry_in_datespan = smry[(smry.DATE >= tree_date) & (smry.DATE < next_tree_date)]
        dates = list(smry_in_datespan.DATE.unique())
        # str_dates = [date.strftime("%Y-%m-%d") for date in dates]
        # print(
        #     f"from date: {tree_date} "
        #     f"next_date: {next_tree_date} "
        #     f"dates: {str_dates} "
        # )
        trees.append(
            {
                "dates": [date.strftime("%Y-%m-%d") for date in dates],
                "tree": extract_tree(df_gruptree, "FIELD", smry_in_datespan, dates),
            }
        )

    with open(f"/private/olind/webviz/grouptree_{ensemble}.json", "w") as handle:
        json.dump(trees, handle)
        print("output exported")

    return io.BytesIO(json.dumps(trees).encode())


def extract_tree(
    df_gruptree: pd.DataFrame, node: str, smry_in_datespan: pd.DataFrame, dates: list
) -> dict:
    """Description"""
    node_type = df_gruptree[df_gruptree.CHILD == node].KEYWORD.iloc[0]
    node_values = get_node_smry(node, node_type, smry_in_datespan, dates)
    result = {
        "name": node,
        "pressure": node_values["pressure"],
        "oilrate": node_values["oilrate"],
        "waterrate": node_values["waterrate"],
        "gasrate": node_values["gasrate"],
        "grupnet": "Grupnet info",
    }
    children = list(df_gruptree[df_gruptree.PARENT == node].CHILD.unique())
    if children:
        result["children"] = [
            extract_tree(df_gruptree, child_node, smry_in_datespan, dates)
            for child_node in df_gruptree[df_gruptree.PARENT == node].CHILD.unique()
        ]
    return result


def get_node_smry(
    node: str, node_type: str, smry_in_datespan: pd.DataFrame, dates: list
) -> Dict[str, List[float]]:
    """Description"""
    if node == "FIELD":
        sumvecs = {
            "oilrate": "FOPR",
            "gasrate": "FGPR",
            "waterrate": "FWPR",
            "pressure": "FPR",
        }
    elif node_type == "GRUPTREE":
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
    for sumvec in sumvecs.values():
        if sumvec not in smry_in_datespan.columns:
            smry_in_datespan[sumvec] = np.nan

    output: Dict[str, List[float]] = {
        "pressure": [],
        "oilrate": [],
        "waterrate": [],
        "gasrate": [],
    }
    for date in dates:
        smry_at_date = smry_in_datespan[smry_in_datespan.DATE == date]
        # print(smry_at_date)
        for key, sumvec in sumvecs.items():
            output[key].append(round(smry_at_date[sumvec].values[0], 2))
    return output

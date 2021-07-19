import glob
from typing import List, Dict
import pandas as pd

# this needs webvizstore and CACHE probably
def read_gruptree_files(ens_paths, gruptree_file) -> pd.DataFrame:
    """Description"""
    df = pd.DataFrame()
    for ens_name, ens_path in ens_paths.items():
        for filename in glob.glob(f"{ens_path}/{gruptree_file}"):
            df_ens = pd.read_csv(filename)
            df_ens["ENSEMBLE"] = ens_name
            df = pd.concat([df, df_ens])
            break
    return df


def get_upstream_nodes(
    gruptree: pd.DataFrame, node_type: str, node: str
) -> Dict[str, List[Dict[str, str]]]:
    """
    [
        {
            "start_date": "2018-01-01",
            "end_date": "2018-05-01",
            "nodes": [
                {
                    "name": "FIELD",
                    "pressure_sumvec": "FPR"
                    "type": "field"
                },
                ...
            ],
        },
        ...
    ]
    """
    output = []
    prev_nodelist = []
    for date, df in gruptree.groupby("DATE"):
        if "BRANPROP" in df.KEYWORD.unique():
            df = df[df.KEYWORD != "GRUPTREE"]
        nodelist = _get_nodelist(df, node_type, node)
        remaining_dates = gruptree[gruptree.DATE>date].DATE
        if remaining_dates.empty:
            next_date = None
        else:
            next_date = remaining_dates.min()

        if nodelist != prev_nodelist:
            output.append(
                {
                    "start_date": date,
                    "end_date": next_date,
                    "nodes": nodelist
                }
            )
            prev_nodelist = nodelist
        else:
            if output:
                output[-1]["end_date"] = next_date
    return output


def _get_nodelist(df, node_type, node) -> List[Dict[str, str]]:
    """Description"""
    if node == "FIELD":
        return [get_node_field(node_type, node)]

    child_row = df[df.CHILD == node]
    if child_row.empty:
        return []
    elif child_row.shape[0] > 1:
        raise ValueError(f"CHILD can only maximum once per date: {child_row}")

    parent = child_row.PARENT.values[0]

    if node_type == "well":
        return [get_node_field(node_type, node), get_node_field("well_bhp", node)] + _get_nodelist(df, "field_group", parent)
    return [get_node_field(node_type, node)] + _get_nodelist(
        df, "field_group", parent
    )


def get_node_field(node_type: str, node: str) -> Dict[str, str]:
    """Description"""
    if node == "FIELD":
        return {"name": node, "type": "field", "pressure": "GPR:FIELD"}
    if node_type == "field_group":
        return {"name": node, "type": "group", "pressure": f"GPR:{node}"}
    if node_type == "well":
        return {
            "name": f"{node} - THP",
            "type": "well",
            "pressure": f"WTHP:{node}",
        }
    if node_type == "well_bhp":
        return {
            "name": f"{node} - BHP",
            "type": "well_bhp",
            "pressure": f"WBHP:{node}",
        }
    raise ValueError(f"Node type {node_type} not implemented.")

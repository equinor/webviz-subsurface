import glob
from typing import List, Dict
import pandas as pd

# this needs webvizstore probably
def read_gruptree_files(ens_paths, gruptree_file ) -> pd.DataFrame:
    """Description"""
    df = pd.DataFrame()
    for ens_name, ens_path in ens_paths.items():
        for filename in glob.glob(f"{ens_path}/{gruptree_file}"):
            df_ens = pd.read_csv(filename)
            df_ens["ENSEMBLE"] = ens_name
            df = pd.concat([df, df_ens])
            break
    return df

def get_upstream_nodes(gruptree: pd.DataFrame, node_type: str, node:str) -> Dict[str, List[Dict[str, str]]]:
    """
    {
        "2018-01-01:[
            {
                "name": "FIELD",
                "pressure_sumvec": "FPR"
            },
            ...
        ],
        ...
    }
    """
    return {
        date: get_upstream_nodes_for_date(group, node_type, node)
        for date, group in gruptree.groupby("DATE")
    }

def _get_upstream_nodes_for_date(gruptree_date, node_type, node) -> List[Dict[str, str]]:
    """Description"""

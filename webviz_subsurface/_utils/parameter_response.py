from typing import Optional, List, Dict

import pandas as pd
import numpy as np
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_and_sum_responses(
    dframe: pd.DataFrame,
    ensemble: str,
    response: str,
    filteroptions: Optional[List[Dict[str, str]]] = None,
    aggregation: str = "sum",
) -> pd.DataFrame:
    """Cached wrapper for _filter_and_sum_responses"""
    return _filter_and_sum_responses(
        dframe=dframe,
        ensemble=ensemble,
        response=response,
        filteroptions=filteroptions,
        aggregation=aggregation,
    )


def _filter_and_sum_responses(
    dframe: pd.DataFrame,
    ensemble: str,
    response: str,
    filteroptions: Optional[List[Dict[str, str]]] = None,
    aggregation: str = "sum",
) -> pd.DataFrame:
    """Filter response dataframe for the given ensemble
    and optional filter columns. Returns dataframe grouped and
    aggregated per realization.
    """
    df = dframe.copy()
    df = df.loc[df["ENSEMBLE"] == ensemble]
    if filteroptions:
        for opt in filteroptions:
            if opt["type"] == "multi" or opt["type"] == "single":
                if isinstance(opt["values"], list):
                    df = df.loc[df[opt["name"]].isin(opt["values"])]
                else:
                    if opt["name"] == "DATE" and isinstance(opt["values"], str):
                        df = df.loc[df["DATE"].astype(str) == opt["values"]]
                    else:
                        df = df.loc[df[opt["name"]] == opt["values"]]

            elif opt["type"] == "range":
                df = df.loc[
                    (df[opt["name"]] >= np.min(opt["values"]))
                    & (df[opt["name"]] <= np.max(opt["values"]))
                ]
    if aggregation == "sum":
        return df.groupby("REAL").sum().reset_index()[["REAL", response]]
    if aggregation == "mean":
        return df.groupby("REAL").mean().reset_index()[["REAL", response]]
    raise ValueError(f"Unknown aggregation '{aggregation}'.")

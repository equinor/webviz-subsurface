from collections.abc import Iterable
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


def filter_and_sum_responses(
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

    df = dframe.loc[dframe["ENSEMBLE"] == ensemble]
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


def check_runs(parameterdf: pd.DataFrame, responsedf: pd.DataFrame) -> None:
    """Check that input parameters and response files have
    the same number of runs"""
    for col in ["ENSEMBLE", "REAL"]:
        if sorted(list(parameterdf[col].unique())) != sorted(
            list(responsedf[col].unique())
        ):
            raise ValueError("Parameter and response files have different runs")


def check_response_filters(
    responsedf: pd.DataFrame, response_filters: Optional[dict]
) -> None:
    """Check that provided response filters are valid"""
    if response_filters:
        for col_name, col_type in response_filters.items():
            if col_name not in responsedf.columns:
                raise ValueError(f"{col_name} is not in response file")
            if col_type not in ["single", "multi", "range"]:
                raise ValueError(f"Filter type {col_type} for {col_name} is not valid.")


def filter_numerical_columns(
    df: pd.DataFrame,
    column_ignore: Optional[List[str]] = None,
    column_include: Optional[List[str]] = None,
    filter_columns: Optional[Iterable] = None,
) -> List[str]:
    """Filter to numerical columns, and respect ignore/include and filters.
    Also remove ENSEMBLE and REAL. Return list of column labels."""
    cols: List[str] = []
    for col in df.columns[[np.issubdtype(dtype, np.number) for dtype in df.dtypes]]:
        if (
            (column_ignore and col in column_ignore)
            or (col in ["ENSEMBLE", "REAL"])
            or (filter_columns and col in filter_columns)
        ):
            continue
        if column_include and col in column_include or column_include is None:
            cols.append(col)
    return cols


def make_response_filters(
    response_filters: dict, response_filter_values: list
) -> List[dict]:
    """Returns a list of active response filters"""
    filteroptions = []
    if response_filter_values:
        for i, (col_name, col_type) in enumerate(response_filters.items()):
            filteroptions.append(
                {
                    "name": col_name,
                    "type": col_type,
                    "values": response_filter_values[i],
                }
            )
    return filteroptions

import logging
import time
from typing import Dict, List

import pandas as pd

from webviz_subsurface._utils.ensemble_summary_provider_set import (
    EnsembleSummaryProviderSet,
)


# -------------------
def get_df_smry(
    input_provider_set: EnsembleSummaryProviderSet,
    ensemble_names: List[str],
    ens_vectors: Dict[str, List[str]],
    ens_realizations: Dict[str, List[int]],
    selector_realizations: List[int],
    selector_well_names: List[str],
    selector_phases: List[str],
    selector_dates: List[str],
) -> pd.DataFrame:
    """Return dataframe filtered on ensemble names, realizations,
    well names, phases and dates selectors."""

    start_time = time.time()

    dfs = []

    for ens_name in ensemble_names:

        df_smry = _get_filtered_df(
            input_provider_set,
            ens_name,
            ens_vectors,
            ens_realizations,
            selector_realizations,
            selector_well_names,
            selector_phases,
            selector_dates,
        )

        dfs.append(df_smry)

    logging.debug(
        f"\n--- get_df_smry --- Total time: {time.time() - start_time} seconds.\n"
    )

    return pd.concat(dfs)


# --------------------------------
def get_df_diff(
    df_smry: pd.DataFrame,
    obs_error_weight: float = 0,
    weight_reduction_factor_oil: float = 1,
    weight_reduction_factor_wat: float = 1,
    weight_reduction_factor_gas: float = 1,
    misfit_exponent: float = 1.0,
    relative_diff: bool = False,
) -> pd.DataFrame:
    """Return dataframe with diff (sim-obs) for all data.
    Return empty dataframe if no realizations included."""

    start_time = time.time()

    if df_smry.empty:
        return pd.DataFrame()

    df_diff = _build_df_diff(
        df_smry,
        obs_error_weight,
        weight_reduction_factor_oil,
        weight_reduction_factor_wat,
        weight_reduction_factor_gas,
        misfit_exponent,
        relative_diff,
    )

    logging.debug(
        f"\n--- get_df_diff --- Total time: {time.time() - start_time} seconds.\n"
    )
    return df_diff


# --------------------------------
# pylint: disable = too-many-locals
def get_df_diff_stat(df_diff: pd.DataFrame) -> pd.DataFrame:
    """Return dataframe with statistics of production difference
    across all realizations per ensemble, well and date.
    Return empty dataframe if no realizations included in df."""

    if df_diff.empty:
        return pd.DataFrame()

    ensembles = []
    dates = []
    wells = []
    diff_vectors = []
    diff_mean_values = []
    diff_std_values = []
    diff_p10_values = []
    diff_p90_values = []

    for ens_name, dframe in df_diff.groupby("ENSEMBLE"):
        for _date, ensdf in dframe.groupby("DATE"):

            for col in ensdf.columns:
                if ":" in col:
                    vector = col.split(":")[0]
                    if vector in [
                        "DIFF_WOPT",
                        "DIFF_WWPT",
                        "DIFF_WGPT",
                        "DIFF_GOPT",
                        "DIFF_GWPT",
                        "DIFF_GGPT",
                    ]:
                        well = col.split(":")[1]
                        wells.append(well)
                        dates.append(_date)
                        ensembles.append(ens_name)
                        diff_vectors.append(vector)
                        diff_mean_values.append(ensdf[col].mean())
                        diff_std_values.append(ensdf[col].std())
                        diff_p10_values.append(ensdf[col].quantile(0.9))
                        diff_p90_values.append(ensdf[col].quantile(0.1))

    df_stat = pd.DataFrame(
        data={
            "ENSEMBLE": ensembles,
            "WELL": wells,
            "VECTOR": diff_vectors,
            "DATE": dates,
            "DIFF_MEAN": diff_mean_values,
            "DIFF_STD": diff_std_values,
            "DIFF_P10": diff_p10_values,
            "DIFF_P90": diff_p90_values,
        }
    )

    return df_stat


# -- help functions -------------

# --------------------------------
def get_df_hist_avg(df_long: pd.DataFrame) -> pd.DataFrame:
    """Read long format dataframe and replace hist vectors (WOPTH, etc) column
    values for each realization with it's average value grouped by WELL, DATE and
    ENSEMBLE columns. The three groupby columns must be part of df_long.
    This function will only have an effect in cases where the history rates
    have uncertainty (varies per realization)."""

    for col in df_long.columns:
        if "PTH" in col:
            df_long[col] = df_long.groupby(["WELL", "ENSEMBLE", "DATE"])[col].transform(
                "mean"
            )
    return df_long


# --------------------------------
def _get_vector_types(phases: List[str]) -> List[str]:
    """Return summary vector types associated with phases."""

    vector_types = []
    if "Oil" in phases:
        vector_types.append("WOPT")
    if "Water" in phases:
        vector_types.append("WWPT")
    if "Gas" in phases:
        vector_types.append("WGPT")

    return vector_types


# --------------------------------
def _get_filtered_df(
    input_provider_set: EnsembleSummaryProviderSet,
    ens_name: str,
    ens_vectors: Dict[str, List[str]],
    ens_realizations: Dict[str, List[int]],
    selector_realizations: List[int],
    selector_well_names: List[str],
    selector_phases: List[str],
    selector_dates: List[str],
) -> List[str]:
    """Return filtered dataframe."""

    filtered_vector_types = _get_vector_types(selector_phases)

    filtered_vectors = []
    filtered_realizations = []

    for vector in ens_vectors[ens_name]:
        if (
            vector.split(":")[0] in filtered_vector_types
            and vector.split(":")[1] in selector_well_names
        ):
            hvector = vector.split(":")[0] + "H:" + vector.split(":")[1]
            filtered_vectors.append(vector)
            filtered_vectors.append(hvector)
    # logging.debug(f"Filtered vectors:\n{filtered_vectors}")

    filtered_realizations = [
        real
        for real in ens_realizations[ens_name]
        if real in set(selector_realizations)
    ]
    logging.debug(f"Filtered realizations:\n{filtered_realizations}")

    df = pd.DataFrame()
    if filtered_vectors and filtered_realizations:
        df = input_provider_set.provider(ens_name).get_vectors_df(
            filtered_vectors, None, filtered_realizations
        )

        df = df.astype({"DATE": "string"})
        df = df.loc[df["DATE"].isin(selector_dates)]  # --- apply date filter

        df["ENSEMBLE"] = ens_name

    return df


# --------------------------------
def _build_df_diff(
    df_smry: pd.DataFrame,
    obs_error_weight: float = 0,
    weight_reduction_factor_oil: float = 1,
    weight_reduction_factor_wat: float = 1,
    weight_reduction_factor_gas: float = 1,
    misfit_exponent: float = 1.0,
    relative_diff: bool = False,
) -> pd.DataFrame:
    """Calculate diffs (sim-obs) and return dataframe"""

    df_diff = df_smry[["ENSEMBLE", "DATE", "REAL"]].copy()

    for simvector in df_smry.columns:
        if "PT:" in simvector:
            vectortype, wellname = simvector.split(":")[0], simvector.split(":")[1]
            obsvector = vectortype + "H:" + wellname
            diff_col_name = "DIFF_" + vectortype + ":" + wellname
            if relative_diff:
                df_diff[diff_col_name] = (
                    (df_smry[simvector] - df_smry[obsvector])
                    / df_smry[obsvector].clip(1000)
                ) * 100
            elif obs_error_weight > 0:
                # obs error, including a lower bound (diminish very low values)
                obs_error = (obs_error_weight * df_smry[obsvector]).clip(1000)
                df_diff[diff_col_name] = (
                    (df_smry[simvector] - df_smry[obsvector]) / obs_error
                ) ** misfit_exponent
            elif obs_error_weight < 0:
                if vectortype == "WOPT":
                    weight_reduction = weight_reduction_factor_oil
                if vectortype == "WWPT":
                    weight_reduction = weight_reduction_factor_wat
                if vectortype == "WGPT":
                    weight_reduction = weight_reduction_factor_gas
                df_diff[diff_col_name] = (
                    (df_smry[simvector] - df_smry[obsvector]) / (weight_reduction)
                ) ** misfit_exponent
            else:
                df_diff[diff_col_name] = (
                    (df_smry[simvector] - df_smry[obsvector])
                ) ** misfit_exponent

    return df_diff

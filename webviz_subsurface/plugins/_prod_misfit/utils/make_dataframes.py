import logging
import time
from typing import Dict, List

import pandas as pd

from ..types.provider_set import ProviderSet


# -------------------
def get_df_smry(
    input_provider_set: ProviderSet,
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

    filtered_vector_types = []
    if "Oil" in selector_phases:
        filtered_vector_types.append("WOPT")
    if "Water" in selector_phases:
        filtered_vector_types.append("WWPT")
    if "Gas" in selector_phases:
        filtered_vector_types.append("WGPT")

    dfs = []
    for ens_name in ensemble_names:

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
            # df.DATE = df.DATE.str[:10]
            df = df.loc[df["DATE"].isin(selector_dates)]  # --- apply date filter

            df["ENSEMBLE"] = ens_name

        dfs.append(df)

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

    df_diff = df_smry[["ENSEMBLE", "DATE", "REAL"]].copy()

    for col in df_smry.columns:
        if "PT:" in col:
            simvector = col
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

    # df_diff = df_diff.astype({"DATE": "string"})

    logging.debug(
        f"\n--- get_df_diff --- Total time: {time.time() - start_time} seconds.\n"
    )
    return df_diff


# --------------------------------
def get_df_diff_stat(df_diff: pd.DataFrame) -> pd.DataFrame:
    """Return dataframe with statistics of production difference
    across all realizations per ensemble, well and date.
    Return empty dataframe if no realizations included in df."""

    my_ensembles = []
    my_dates = []
    my_wells = []
    my_diff_vectors = []
    my_diff_mean_values = []
    my_diff_std_values = []
    my_diff_p10_values = []
    my_diff_p90_values = []

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
                        my_wells.append(well)
                        my_dates.append(_date)
                        my_ensembles.append(ens_name)
                        my_diff_vectors.append(vector)
                        my_diff_mean_values.append(ensdf[col].mean())
                        my_diff_std_values.append(ensdf[col].std())
                        my_diff_p10_values.append(ensdf[col].quantile(0.9))
                        my_diff_p90_values.append(ensdf[col].quantile(0.1))

    df_stat = pd.DataFrame(
        data={
            "ENSEMBLE": my_ensembles,
            "WELL": my_wells,
            "VECTOR": my_diff_vectors,
            "DATE": my_dates,
            "DIFF_MEAN": my_diff_mean_values,
            "DIFF_STD": my_diff_std_values,
            "DIFF_P10": my_diff_p10_values,
            "DIFF_P90": my_diff_p90_values,
        }
    )
    # df_stat = df_stat.astype({"DATE": "string"})
    return df_stat

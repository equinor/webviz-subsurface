from typing import List, Union

import numpy as np
import pandas as pd


def calc_from_cumulatives(
    data: pd.DataFrame,
    column_keys: Union[List[str], str],
    time_index: str,
    time_index_input: str,
    as_rate: bool,
) -> pd.DataFrame:
    """Calculates interval delta and average rate at given time interval `time_index`.
    `data` is a dataframe which has the columns "DATE", "ENSEMBLE", "REAL" and the columns
    that you want to make the calculation for

    Assumes that the data is already sampled to a time interval `time_index_input`.
    `time_index` can currently be `daily`, `monthly` or `yearly`.

    Interpolation is not performed, and the time interval `time_index` therefore has to be shorter
    or equal to `time_index_input` (e.g. `time_index` = `yearly` is compatible with
    `time_index_input` = `monthly`, but the opposite is invalid).

    `column_keys` define vectors to take calculate for of.

    If `as_rate` == True, the calculated cumulative for an interval is divided by the number of
    days in the interval to give a rate per day.

    Assumes that the data for each realization comes in consecutive lines, and that it is sorted as
    increasing in time.

    The average rate and interval production is stored at the beginning date of the interval,
    opposite to rates in e.g. the Eclipse simulator's summary format, but similar to fmu-ensemble's
    get_volumetric_rates(). E.g. for a monthly interval, the values stored at 2010-01-01 would be
    the average rate and production for January 2010.
    """
    data = data.copy()
    if isinstance(column_keys, str):
        column_keys = [column_keys]

    # Converting the DATE axis to datetime to allow for timedeltas
    data.loc[:, ["DATE"]] = pd.to_datetime(data["DATE"])
    _verify_time_index(data, time_index, time_index_input)
    # Creating a column of unique values per ensemble-realization combination. A non-zero
    # diff of this column will then mean that it is a diff between different realizations.
    # Could alternatively loop over ensembles and realizations, but this is quicker for
    # larger datasets.
    data["ensrealuid"] = (
        data["ENSEMBLE"].astype("category").cat.codes * data["REAL"].nunique()
        + data["REAL"]
    )

    # Allows us to resample on DATE without merging ensembles and realizations.
    data.set_index(["ENSEMBLE", "REAL", "DATE"], inplace=True)

    # Resample on DATE frequency
    data = _resample_time_index(
        df=data, time_index=time_index, time_index_input=time_index_input
    )

    data.reset_index(level=["ENSEMBLE", "REAL"], inplace=True)

    calc_cols = {vec: rename_vec_from_cum(vec, as_rate) for vec in column_keys}
    listed_calc_cols = [calc_cols[col] for col in column_keys]

    # Take diff of given column_keys + the ensemble-realization identifier.
    # Preserve ENSEMBLE and REAL
    diff_cum = pd.concat(
        [
            data[["ENSEMBLE", "REAL"]],
            data[["ensrealuid"] + column_keys]
            .diff()
            .shift(-1)
            .rename(
                mapper=calc_cols,
                axis=1,
            ),
        ],
        axis=1,
    )
    diff_cum[listed_calc_cols] = diff_cum[listed_calc_cols].fillna(value=0)

    # Reset index (DATE becomes regular column)
    diff_cum.reset_index(inplace=True)

    # Convert interval cumulative to daily average rate if requested
    if as_rate:
        days = diff_cum["DATE"].diff().shift(-1).dt.days.fillna(value=0)
        for vec in column_keys:
            with np.errstate(invalid="ignore"):
                diff_cum.loc[:, calc_cols[vec]] = (
                    diff_cum[calc_cols[vec]].values / days.values
                )

    # Set last value of each real to 0 (as we don't loop over the realizations)
    diff_cum.loc[diff_cum["ensrealuid"] != 0, listed_calc_cols] = 0
    diff_cum.drop("ensrealuid", axis=1, inplace=True)

    return diff_cum


def _verify_time_index(
    df: pd.DataFrame, time_index: str, time_index_input: str
) -> None:
    freqs = {"D": "daily", "MS": "monthly", "AS-JAN": "yearly"}
    valid_time_indices = {
        "daily": ["daily", "monthly", "yearly"],
        "monthly": ["monthly", "yearly"],
        "yearly": ["yearly"],
    }
    inferred_frequency = pd.infer_freq(sorted(df["DATE"].unique()))
    if not freqs.get(inferred_frequency) == time_index_input:
        raise ValueError(
            "The DataFrame most likely contains data points which are not sampled on "
            f"frequency time_index_input={time_index_input}. The inferred frequency from the "
            f"unique DATE values was {inferred_frequency}."
        )
    if not time_index in valid_time_indices[time_index_input]:
        raise ValueError(
            f"The time_index {time_index} has higher frequency than time_index_input "
            f"{time_index_input}. Valid time_index options are "
            f"{valid_time_indices[time_index_input]}."
        )


def _resample_time_index(
    df: pd.DataFrame, time_index: str, time_index_input: str
) -> pd.DataFrame:
    if time_index == time_index_input:
        return df
    if time_index == "yearly" and time_index_input in ["daily", "monthly"]:
        return df.groupby(
            [
                pd.Grouper(level="ENSEMBLE"),
                pd.Grouper(level="REAL"),
                pd.Grouper(level="DATE", freq="YS"),
            ]
        ).first()
    if time_index == "monthly" and time_index_input == "daily":
        return df.groupby(
            [
                pd.Grouper(level="ENSEMBLE"),
                pd.Grouper(level="REAL"),
                pd.Grouper(level="DATE", freq="MS"),
            ]
        ).first()
    raise ValueError(
        f"Cannot combine `time_index`={time_index} and `time_index_input`={time_index_input}. "
        "Ensure that `time_index_input` has a higher than or equal frequency to `time_index`. "
        "Valid options are `daily`, `monthly` and `yearly` (dependent on input data)."
    )


def rename_vec_from_cum(vector: str, as_rate: bool) -> str:
    """This function assumes that it is a cumulative/total vector named in the Eclipse standard
    and is fairly naive when converting to rate. Based in the list in libecl
    https://github.com/equinor/libecl/blob/69f1ee0ddf696c87b6d85eca37eed7e8b66ac2db/\
        lib/ecl/smspec_node.cpp#L531-L586
    the T identifying total/cumulative should not occur before letter 4,
    as all the listed strings are prefixed with one or two letters in the vectors.
    Therefore starting the replace at the position 3 (4th letter) to reduce risk of errors
    in the conversion to rate naming, but hard to be completely safe.
    """
    return (
        f"AVG_{vector[0:3] + vector[3:].replace('T', 'R', 1)}"
        if as_rate
        else f"INTVL_{vector}"
    )

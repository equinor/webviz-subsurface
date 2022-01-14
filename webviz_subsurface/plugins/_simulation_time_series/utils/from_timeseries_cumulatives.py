import datetime
from typing import Optional

import numpy as np
import pandas as pd

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.dataframe_utils import (
    assert_date_column_is_datetime_object,
    make_date_column_datetime_object,
)

###################################################################################
# NOTE: This code is a copy and modification of
# webviz_subsurface/_datainput/from_timeseries_cumulatives.py for usage with
# EnsembleSummaryProvider functionality
#
# Renaming is performed for clarity
#
# Some additional functions are added.
###################################################################################


def is_interval_or_average_vector(vector: str) -> bool:
    return vector.startswith("AVG_") or vector.startswith("INTVL_")


def get_cumulative_vector_name(vector: str) -> str:
    if not is_interval_or_average_vector(vector):
        raise ValueError(
            f'Expected "{vector}" to be a vector calculated from cumulative!'
        )

    if vector.startswith("AVG_"):
        return f"{vector[4:7] + vector[7:].replace('R', 'T', 1)}"
    if vector.startswith("INTVL_"):
        return vector.lstrip("INTVL_")
    raise ValueError(f"Expected {vector} to be a cumulative vector!")


def calculate_from_resampled_cumulative_vectors_df(
    vectors_df: pd.DataFrame,
    as_rate_per_day: bool,
) -> pd.DataFrame:
    """
    Calculates interval delta or average rate data for vector columns in provided dataframe.
    This function assumes data is already resampled when retrieved with ensemble summary
    provider.

    Date sampling should be according to Frequency enum in
    webviz_subsurface/_providers/ensemble_summary_provider.py.
    Does not handle raw data and varying time delta less than daily!

    `INPUT:`
    * vectors_df: pd.Dataframe - Dataframe with columns:
        ["DATE", "REAL", vector1, ..., vectorN]

    `NOTE:`
    - Does not handle raw data format with varying sampling or sampling frequency higher than
    daily!
    - Dataframe has columns:\n
    "DATE": Series with dates on datetime.datetime format
    "REAL": Series of realization number identifier
    vector1, ..., vectorN: Series of vector data for vector of given column name

    `TODO:`
    * IMPROVE FUNCTION NAME?
    * Handle raw data format?
    * Give e.g. a dict with info of "avg and intvl" calculation for each vector column?
    Can thereby calculate everything for provided vector columns and no iterate column per
    column?
    """
    assert_date_column_is_datetime_object(vectors_df)

    vectors_df = vectors_df.copy()

    column_keys = [elm for elm in vectors_df.columns if elm not in ["DATE", "REAL"]]

    # Sort by realizations, thereafter dates
    vectors_df.sort_values(by=["REAL", "DATE"], inplace=True)

    # Create column of unique id for realizations. .diff() takes diff between an index
    # and previous index in a column. Thereby if "realuid" is != 0, the .diff() is
    # between two realizations.
    # Could alternatively loop over ensembles and realizations, but this is quicker for
    # larger datasets.
    vectors_df["realuid"] = vectors_df["REAL"]

    vectors_df.set_index(["DATE"], inplace=True)

    cumulative_name_map = {
        vector: rename_vector_from_cumulative(vector, as_rate_per_day)
        for vector in column_keys
    }
    cumulative_vectors = list(cumulative_name_map.values())

    # Take diff of given column_keys indexes - preserve REAL
    cumulative_vectors_df = pd.concat(
        [
            vectors_df[["REAL"]],
            vectors_df[["realuid"] + column_keys]
            .diff()
            .shift(-1)
            .rename(
                mapper=cumulative_name_map,
                axis=1,
            ),
        ],
        axis=1,
    )
    cumulative_vectors_df[cumulative_vectors] = cumulative_vectors_df[
        cumulative_vectors
    ].fillna(value=0)

    # Reset index (DATE becomes regular column)
    cumulative_vectors_df.reset_index(inplace=True)

    # Convert interval cumulative to daily average rate if requested
    if as_rate_per_day:
        days = cumulative_vectors_df["DATE"].diff().shift(-1).dt.days.fillna(value=0)
        for vector in column_keys:
            with np.errstate(invalid="ignore"):
                cumulative_vector_name = cumulative_name_map[vector]
                cumulative_vectors_df.loc[:, cumulative_vector_name] = (
                    cumulative_vectors_df[cumulative_vector_name].values / days.values
                )

    # Find .diff() between two realizations and set value = 0
    cumulative_vectors_df.loc[
        cumulative_vectors_df["realuid"] != 0, cumulative_vectors
    ] = 0
    cumulative_vectors_df.drop("realuid", axis=1, inplace=True)

    make_date_column_datetime_object(cumulative_vectors_df)

    return cumulative_vectors_df


def rename_vector_from_cumulative(vector: str, as_rate: bool) -> str:
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


# pylint: disable=too-many-return-statements
def datetime_to_intervalstr(date: datetime.datetime, freq: Frequency) -> Optional[str]:
    if date is None:
        return None

    if freq == Frequency.DAILY:
        return f"{date.year}-{date.month:02d}-{date.day:02d}"
    if freq == Frequency.WEEKLY:
        # Note: weekyear may differ from actual year for week numbers 1,52,53.
        (weekyear, week, _) = date.isocalendar()
        return f"{weekyear}-W{week:02d}"
    if freq == Frequency.MONTHLY:
        return f"{date.year}-{date.month:02d}"
    if freq == Frequency.QUARTERLY:
        return f"{date.year}-Q{1 + (date.month-1)//3}"
    if freq == Frequency.YEARLY:
        return f"{date.year}"

    # Using isoformat if frequency is none of the listed instead of error.
    return date.isoformat()

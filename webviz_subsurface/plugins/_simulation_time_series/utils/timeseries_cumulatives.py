import numpy as np
import pandas as pd

###################################################################################
# NOTE: This code is a copy and modification of
# webviz_subsurface/_datainput/from_timeseries_cumulatives.py for usage with
# EnsembleSummaryProvider functionality
#
# Renaming is performed for clarity
#
# Some additional functions are added.
###################################################################################


def is_cumulative_vector(vector: str) -> bool:
    return vector.startswith("AVG_") or vector.startswith("INTVL_")


def get_total_vector_from_cumulative(vector: str) -> str:
    if not is_cumulative_vector(vector):
        raise ValueError(f"Expected {vector} to be a cumulative vector!")

    if vector.startswith("AVG_"):
        return vector.lstrip("AVG_")
    if vector.startswith("INTVL_"):
        return vector.lstrip("INTVL_")
    raise ValueError(f"Expected {vector} to be a cumulative vector!")


def calculate_cumulative_vectors_df(
    vectors_df: pd.DataFrame,
    sampling_frequency: str,
    resampling_frequency: str,
    as_rate: bool,
) -> pd.DataFrame:
    """
    Interpolation is not performed, and the time interval `resampling_frequency` therefore has to be
    shorter or equal to `sampling_frequency` (e.g. `resampling_frequency` = `yearly` is compatible
    with `sampling_frequency` = `monthly`, but the opposite is invalid).
    """
    vectors_df = vectors_df.copy()

    column_keys = [elm for elm in vectors_df.columns if elm not in ["DATE", "REAL"]]

    # Converting the DATE axis to datetime to allow for timedeltas
    vectors_df.loc[:, ["DATE"]] = pd.to_datetime(vectors_df["DATE"])
    _verify_resampling_frequency(vectors_df, resampling_frequency, sampling_frequency)

    # NOTE: Not creating ensrealuid - no need for uid for reals?

    vectors_df.set_index(["REAL", "DATE"], inplace=True)

    # Resample on DATE frequency
    vectors_df = _resample_dates(vectors_df, resampling_frequency, sampling_frequency)

    vectors_df.reset_index(level=["REAL"], inplace=True)

    cumulative_name_map = {
        vector: rename_vector_from_cumulative(vector, as_rate) for vector in column_keys
    }
    cumulative_vectors = list(cumulative_name_map.values())

    # Take diff of given column_keys indexes - preserve REAL
    cumulative_vectors_df = pd.concat(
        [
            vectors_df[["REAL"]],
            vectors_df[column_keys]
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
    if as_rate:
        days = cumulative_vectors_df["DATE"].diff().shift(-1).dt.days.fillna(value=0)
        for vector in column_keys:
            with np.errstate(invalid="ignore"):
                cumulative_vector_name = cumulative_name_map[vector]
                cumulative_vectors_df.loc[:, cumulative_vector_name] = (
                    cumulative_vectors_df[cumulative_vector_name].values / days.values
                )

    # Set last value of each real to 0 (as we don't loop over the realizations)
    last_date = max(cumulative_vectors_df["DATE"])
    cumulative_vectors_df.loc[
        cumulative_vectors_df["DATE"] == last_date, cumulative_vectors
    ] = 0

    return cumulative_vectors_df


def _verify_resampling_frequency(
    df: pd.DataFrame, resampling_frequency: str, sampling_frequency: str
) -> None:
    frequencies = {"D": "daily", "MS": "monthly", "AS-JAN": "yearly"}
    valid_time_indices = {
        "daily": ["daily", "monthly", "yearly"],
        "monthly": ["monthly", "yearly"],
        "yearly": ["yearly"],
    }
    inferred_frequency = pd.infer_freq(sorted(df["DATE"].unique()))
    if not frequencies.get(inferred_frequency) == sampling_frequency:
        raise ValueError(
            "The DataFrame most likely contains data points which are not sampled on "
            f"frequency sampling_frequency={sampling_frequency}. The inferred frequency from the "
            f"unique DATE values was {inferred_frequency}."
        )
    if not resampling_frequency in valid_time_indices[sampling_frequency]:
        raise ValueError(
            f"The resampling_frequency {resampling_frequency} has higher frequency than "
            f"sampling_frequency {sampling_frequency}. Valid time_index options are "
            f"{valid_time_indices[sampling_frequency]}."
        )


def _resample_dates(
    df: pd.DataFrame, resampling_frequency: str, sampling_frequency: str
) -> pd.DataFrame:
    if resampling_frequency == sampling_frequency:
        return df
    if resampling_frequency == "yearly" and sampling_frequency in ["daily", "monthly"]:
        return df.groupby(
            [
                pd.Grouper(level="REAL"),
                pd.Grouper(level="DATE", freq="YS"),
            ]
        ).first()
    if resampling_frequency == "monthly" and sampling_frequency == "daily":
        return df.groupby(
            [
                pd.Grouper(level="REAL"),
                pd.Grouper(level="DATE", freq="MS"),
            ]
        ).first()
    raise ValueError(
        f"Cannot combine `resampling_frequency`={resampling_frequency} and `sampling_frequency`="
        f"{sampling_frequency}. Ensure that `sampling_frequency` has a higher than or equal "
        "frequency to `resampling_frequency`. Valid options are `daily`, `monthly` and `yearly` "
        "(dependent on input data)."
    )


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

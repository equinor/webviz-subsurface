import datetime
import glob
import logging
import os
import re
from pathlib import Path
from typing import Optional

import datacompy  # pylint: disable=import-error, useless-suppression
import dateutil.parser  # type: ignore
import ecl2df
import numpy as np
import pandas as pd
from fmu.ensemble import ScratchEnsemble

from .ensemble_summary_provider import Frequency
from .ensemble_summary_provider_factory import (
    EnsembleSummaryProvider,
    EnsembleSummaryProviderFactory,
)

# pylint: disable=line-too-long

# Note that running this script requires the additional install of datacompy.
#   pip install datacompy

# Tolerances inspired by
#   https://numpy.org/doc/stable/reference/generated/numpy.isclose.html
# and
#   https://pandas.pydata.org/docs/reference/api/pandas.testing.assert_frame_equal.html#pandas.testing.assert_frame_equal
ABS_TOLERANCE = 1e-8
REL_TOLERANCE = 1e-5


def _make_date_column_datetime_object(df: pd.DataFrame) -> pd.DataFrame:

    sampled_date_value = df["DATE"].values[0]

    # Infer datatype based on the first element:
    if isinstance(sampled_date_value, pd.Timestamp):
        df["DATE"] = pd.Series(
            [ts.to_pydatetime() for ts in df["DATE"]], dtype="object"
        )

    elif isinstance(sampled_date_value, np.datetime64):
        df["DATE"] = pd.Series(df["DATE"].dt.to_pydatetime(), dtype="object")

    elif isinstance(sampled_date_value, str):
        # Do not use pd.Series.apply() here, Pandas would try to convert it to
        # datetime64[ns] which is limited at year 2262.
        df["DATE"] = pd.Series(
            [dateutil.parser.parse(datestr) for datestr in df["DATE"]], dtype="object"
        )

    elif isinstance(sampled_date_value, datetime.date):
        df["DATE"] = pd.Series(
            [
                datetime.datetime.combine(dateobj, datetime.datetime.min.time())
                for dateobj in df["DATE"]
            ],
            dtype="object",
        )

    # sampled_after_conv = df["DATE"].values[0]
    # print(f"sampled_after_conv={sampled_after_conv}   type={type(sampled_after_conv)}")

    return df


def _load_smry_dataframe_using_fmu(
    ens_path: str, frequency: Optional[Frequency]
) -> pd.DataFrame:

    time_index: str = "raw"
    if frequency:
        time_index = frequency.value

    print(f"## Loading data into DataFrame using FMU  time_index={time_index}...")

    scratch_ensemble = ScratchEnsemble("tempEnsName", paths=ens_path)
    df = scratch_ensemble.load_smry(time_index=time_index)

    df = _make_date_column_datetime_object(df)

    # Convert float columns to float32 and real column to int32
    floatcols = df.select_dtypes("float").columns
    df[floatcols] = df[floatcols].apply(pd.to_numeric, downcast="float")
    df["REAL"] = df["REAL"].astype("int32")

    # Sort on real, then date to align with provider
    df.sort_values(by=["REAL", "DATE"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


def _load_smry_dataframe_using_ecl2df(
    ens_path: str, frequency: Optional[Frequency]
) -> pd.DataFrame:

    time_index: str = "raw"
    if frequency:
        time_index = frequency.value

    print(f"## Loading data into DataFrame using ECL2DF  time_index={time_index}...")

    realidxregexp = re.compile(r"realization-(\d+)")
    globpattern = os.path.join(ens_path, "eclipse/model/*.UNSMRY")
    globbedpaths = sorted(glob.glob(globpattern))

    per_real_df_arr = []

    for smry_file in globbedpaths:
        real = None
        for path_comp in reversed(smry_file.split(os.path.sep)):
            realmatch = re.match(realidxregexp, path_comp)
            if realmatch:
                real = int(realmatch.group(1))
                break

        if real is None:
            raise ValueError(
                f"Unable to determine realization number for file: {smry_file}"
            )

        print(f"R={real}:  {smry_file}")

        eclfiles = ecl2df.EclFiles(smry_file.replace(".UNSMRY", ""))
        real_df = ecl2df.summary.df(eclfiles, time_index=time_index)
        real_df.insert(0, "REAL", real)
        real_df.index.name = "DATE"
        per_real_df_arr.append(real_df)

    df = pd.concat(per_real_df_arr, sort=False).reset_index()

    df = _make_date_column_datetime_object(df)

    # Convert float columns to float32 and real column to int32
    floatcols = df.select_dtypes("float").columns
    df[floatcols] = df[floatcols].apply(pd.to_numeric, downcast="float")
    df["REAL"] = df["REAL"].astype("int32")

    # Sort on real, then date to align with provider
    df.sort_values(by=["REAL", "DATE"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


def _compare_reference_df_to_provider_get_vectors_df(
    reference_df: pd.DataFrame,
    provider: EnsembleSummaryProvider,
    frequency: Optional[Frequency],
) -> None:

    reference_df = reference_df.reset_index(drop=True)
    # print(ref_df)

    print("## Getting data for all vectors from provider...")
    provider_df = provider.get_vectors_df(provider.vector_names(), frequency)
    provider_df.sort_values(by=["REAL", "DATE"], inplace=True)
    provider_df.reset_index(drop=True, inplace=True)
    # print(provider_df)

    print("## Running compare...")
    compare = datacompy.Compare(
        reference_df,
        provider_df,
        df1_name="ref_df",
        df2_name="provider_df",
        join_columns=["REAL", "DATE"],
        abs_tol=ABS_TOLERANCE,
        rel_tol=REL_TOLERANCE,
    )
    if compare.matches():
        print("## Comparison ok")
    else:
        print("## Comparison DID NOT MATCH")
        print(compare.report())

        print("## Columns that are only present in reference_df:")
        print(compare.df1_unq_columns())

        print("## Columns that are only present in provider_df:")
        print(compare.df2_unq_columns())


def _compare_reference_df_to_provider_get_vectors_for_date(
    reference_df: pd.DataFrame, provider: EnsembleSummaryProvider
) -> None:

    all_dates = reference_df["DATE"].unique()
    num_dates = len(all_dates)
    # print(all_dates)

    lookup_date_arr = []
    lookup_date_arr.append(all_dates[0])
    lookup_date_arr.append(all_dates[int(num_dates / 3)])
    lookup_date_arr.append(all_dates[int(num_dates / 2)])
    lookup_date_arr.append(all_dates[int(2 * num_dates / 3)])
    lookup_date_arr.append(all_dates[num_dates - 1])

    for lookup_date in lookup_date_arr:
        # print(f"lookup_date={lookup_date}   type={type(lookup_date)}")
        ref_res_df = reference_df.loc[reference_df["DATE"] == lookup_date].copy()
        ref_res_df.drop(columns="DATE", inplace=True)
        ref_res_df.reset_index(drop=True, inplace=True)
        # print("## Dumping ref_res_df:")
        # print(ref_res_df)

        provider_df = provider.get_vectors_for_date_df(
            lookup_date, provider.vector_names()
        )
        provider_df.reset_index(drop=True, inplace=True)
        # print("## Dumping provider_df:")
        # print(provider_df)

        print(f"## Running compare for date {lookup_date} ...")
        compare = datacompy.Compare(
            ref_res_df,
            provider_df,
            df1_name="ref_res_df",
            df2_name="provider_df",
            join_columns=["REAL"],
            abs_tol=ABS_TOLERANCE,
            rel_tol=REL_TOLERANCE,
        )
        if compare.matches():
            print(f"## Comparison ok for date {lookup_date}")
        else:
            print(f"## Comparison DID NOT MATCH for date {lookup_date}")
            print(compare.report())

            print("## Columns that are only present in ref_res_df:")
            print(compare.df1_unq_columns())

            print("## Columns that are only present in provider_df:")
            print(compare.df2_unq_columns())


def main() -> None:
    print()
    print("## Running comparison SMRY FMU vs lazy provider")
    print("## =================================================")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-3s [%(name)s]: %(message)s",
    )
    logging.getLogger("webviz_subsurface").setLevel(level=logging.INFO)
    logging.getLogger("webviz_subsurface").setLevel(level=logging.DEBUG)

    root_storage_dir = Path("/home/sigurdp/buf/webviz_storage_dir")

    ensemble_path = "../webviz-subsurface-testdata/01_drogon_ahm/realization-*/iter-0"
    # ensemble_path = (
    #     "../webviz-subsurface-testdata/01_drogon_design/realization-*/iter-0"
    # )
    # ensemble_path = (
    #     "/home/sigurdp/webviz_testdata/reek_history_match_large/realization-*/iter-0"
    # )

    # frequency = None
    # frequency = Frequency.DAILY
    frequency = Frequency.WEEKLY

    print()
    print("## root_storage_dir:", root_storage_dir)
    print("## ensemble_path:", ensemble_path)
    print("## frequency:", frequency)
    print()

    print("## Creating summary provider...")
    factory = EnsembleSummaryProviderFactory(
        root_storage_dir, allow_storage_writes=True
    )
    provider = factory.create_from_arrow_unsmry_lazy(
        ens_path=ensemble_path, rel_file_pattern="share/results/unsmry/*.arrow"
    )
    # provider = factory.create_from_arrow_unsmry_presampled(ensemble_path, frequency)

    print("## Loading data into reference DataFrame...")
    # Note that for version 2.13.0 and earlier of ecl, loading via FMU will not give the
    # correct results. This was remedied in https://github.com/equinor/ecl/pull/837
    # reference_df = _load_smry_dataframe_using_ecl2df(ensemble_path, frequency)
    reference_df = _load_smry_dataframe_using_fmu(ensemble_path, frequency)

    print("## Comparing get_vectors()...")
    resampling_frequency = frequency if provider.supports_resampling() else None
    _compare_reference_df_to_provider_get_vectors_df(
        reference_df, provider, resampling_frequency
    )

    print("## Comparing get_vectors_for date()...")
    _compare_reference_df_to_provider_get_vectors_for_date(reference_df, provider)

    print("## done")


# Running:
# python -m webviz_subsurface._providers.ensemble_summary_provider.dev_compare_fmu_to_lazy_provider
if __name__ == "__main__":
    main()

import datetime
import logging
from pathlib import Path

import datacompy
import dateutil.parser  # type: ignore
import pandas as pd
from fmu.ensemble import ScratchEnsemble

from .ensemble_summary_provider import Frequency
from .ensemble_summary_provider_factory import EnsembleSummaryProvider
from .ensemble_summary_provider_factory import EnsembleSummaryProviderFactory

# pylint: disable=line-too-long

# Tolerances inspired by
#   https://numpy.org/doc/stable/reference/generated/numpy.isclose.html
# and
#   https://pandas.pydata.org/docs/reference/api/pandas.testing.assert_frame_equal.html#pandas.testing.assert_frame_equal
ABS_TOLERANCE = 1e-8
REL_TOLERANCE = 1e-4


def _make_date_column_datetime_object(df: pd.DataFrame) -> pd.DataFrame:

    sampled_date_value = df["DATE"].values[0]

    # Infer datatype (Pandas cannot answer it) based on the first element:
    if isinstance(sampled_date_value, pd.Timestamp):
        df["DATE"] = pd.Series(pd.to_pydatetime(df["DATE"]), dtype="object")

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

    return df


def _load_smry_dataframe_using_fmu(ens_path: str, frequency: Frequency) -> pd.DataFrame:

    time_index: str = "raw"
    if frequency:
        time_index = frequency.value

    print("time_index", time_index)
    scratch_ensemble = ScratchEnsemble("tempEnsName", paths=ens_path)
    df = scratch_ensemble.load_smry(time_index=time_index)

    df = _make_date_column_datetime_object(df)

    # Convert float columns to float32 and real column to int32
    floatcols = df.select_dtypes("float").columns
    df[floatcols] = df[floatcols].apply(pd.to_numeric, downcast="float")
    df["REAL"] = df["REAL"].astype("int32")

    # Sort on real, then date to align with provider
    df.sort_values(by=["REAL", "DATE"], inplace=True)

    return df


def _compare_fmu_df_to_provider_get_vectors_df(
    fmu_df: pd.DataFrame, provider: EnsembleSummaryProvider, frequency: Frequency
) -> None:

    fmu_df = fmu_df.reset_index(drop=True)
    # print(fmu_df)

    print("## Getting data for all vectors from provider...")
    provider_df = provider.get_vectors_df(provider.vector_names(), frequency)
    provider_df = provider_df.reset_index(drop=True)
    # print(provider_df)

    print("## Running compare...")
    compare = datacompy.Compare(
        fmu_df,
        provider_df,
        df1_name="fmu_df",
        df2_name="provider_df",
        on_index=True,
        abs_tol=ABS_TOLERANCE,
        rel_tol=REL_TOLERANCE,
    )
    if compare.matches():
        print("## Comparison ok")
    else:
        print("## Comparison DID NOT MATCH")
        print(compare.report())

        print("## Columns that are only present in fmu_res_df:")
        print(compare.df1_unq_columns())

        print("## Columns that are only present in provider_df:")
        print(compare.df2_unq_columns())


def _compare_fmu_df_to_provider_get_vectors_for_date(
    fmu_df: pd.DataFrame, provider: EnsembleSummaryProvider
) -> None:

    all_dates = fmu_df["DATE"].unique()
    num_dates = len(all_dates)
    # print(all_dates)

    lookup_date_arr = []
    lookup_date_arr.append(all_dates[0])
    lookup_date_arr.append(all_dates[int(num_dates / 3)])
    lookup_date_arr.append(all_dates[int(num_dates / 2)])
    lookup_date_arr.append(all_dates[int(2 * num_dates / 3)])
    lookup_date_arr.append(all_dates[num_dates - 1])

    for lookup_date in lookup_date_arr:
        fmu_res_df = fmu_df.loc[fmu_df["DATE"] == lookup_date]
        fmu_res_df = fmu_res_df.drop(columns="DATE")
        fmu_res_df = fmu_res_df.reset_index(drop=True)
        # print("## Dumping fmu_res_df:")
        # print(fmu_res_df)

        provider_df = provider.get_vectors_for_date_df(
            lookup_date, provider.vector_names()
        )
        provider_df = provider_df.reset_index(drop=True)
        # print("## Dumping provider_df:")
        # print(provider_df)

        print(f"## Running compare for date {lookup_date} ...")
        compare = datacompy.Compare(
            fmu_res_df,
            provider_df,
            df1_name="fmu_res_df",
            df2_name="provider_df",
            on_index=True,
            abs_tol=ABS_TOLERANCE,
            rel_tol=REL_TOLERANCE,
        )
        if compare.matches():
            print(f"## Comparison ok for date {lookup_date}")
        else:
            print(f"## Comparison DID NOT MATCH for date {lookup_date}")
            print(compare.report())

            print("## Columns that are only present in fmu_res_df:")
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

    # frequency = Frequency.DAILY
    frequency = Frequency.WEEKLY

    print()
    print("## root_storage_dir:", root_storage_dir)
    print("## ensemble_path:", ensemble_path)
    print("## frequency:", frequency)
    print()

    print("## Creating provider...")
    factory = EnsembleSummaryProviderFactory(root_storage_dir)
    provider = factory.create_from_arrow_unsmry_lazy(ensemble_path)

    print("## Loading data into DataFrame using FMU...")
    fmu_df = _load_smry_dataframe_using_fmu(ensemble_path, frequency)

    print("## Comparing get_vectors...")
    _compare_fmu_df_to_provider_get_vectors_df(fmu_df, provider, frequency)

    print("## Comparing get_vectors_for date...")
    _compare_fmu_df_to_provider_get_vectors_for_date(fmu_df, provider)

    print("## done")


# Running:
# python -m webviz_subsurface._providers.ensemble_summary_provider.dev_compare_fmu_to_lazy_provider
if __name__ == "__main__":
    main()

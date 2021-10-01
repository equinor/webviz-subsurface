import datetime
import logging
from pathlib import Path

import datacompy
import dateutil.parser  # type: ignore
import pandas as pd
from fmu.ensemble import ScratchEnsemble

from .ensemble_summary_provider import Frequency
from .ensemble_summary_provider_factory import EnsembleSummaryProviderFactory


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


def _load_smry_dataframe_using_fmu(ens_path: str, time_index: str) -> pd.DataFrame:

    scratch_ensemble = ScratchEnsemble("tempEnsName", paths=ens_path)
    df = scratch_ensemble.load_smry(time_index=time_index)

    df = _make_date_column_datetime_object(df)

    # Convert float columns to float32 and real column to int32
    floatcols = df.select_dtypes("float").columns
    df[floatcols] = df[floatcols].apply(pd.to_numeric, downcast="float")
    df["REAL"] = df["REAL"].astype("int32")

    return df


def _compare_fmu_smry_to_lazy_provider(
    factory: EnsembleSummaryProviderFactory,
    ens_path: str,
    frequency: Frequency,
) -> pd.DataFrame:

    print("## Loading data into DataFrame using FMU...")
    time_index: str = "raw"
    if frequency:
        time_index = frequency.value

    print("time_index", time_index)
    fmu_df = _load_smry_dataframe_using_fmu(ens_path, time_index)
    fmu_df.sort_values(by=["REAL", "DATE"], inplace=True)
    fmu_df.reset_index(inplace=True, drop=True)
    # print(fmu_df)

    print("## Creating provider...")
    provider = factory.create_from_arrow_unsmry_lazy(ens_path)

    print("## Getting data from provider...")
    provider_df = provider.get_vectors_df(provider.vector_names(), frequency)
    provider_df.reset_index(inplace=True, drop=True)
    # print(provider_df)

    print("## Running compare...")
    compare = datacompy.Compare(
        fmu_df,
        provider_df,
        df1_name="fmu_df",
        df2_name="provider_df",
        on_index=True,
        # abs_tol=0.000001,
        rel_tol=1e-6,
    )
    print(compare.report())

    print("\nColumns that are only present in fmu_df:")
    print(compare.df1_unq_columns())

    print("\nColumns that are only present in provider_df:")
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

    # ensemble_path = "../webviz-subsurface-testdata/01_drogon_ahm/realization-*/iter-0"
    ensemble_path = (
        "../webviz-subsurface-testdata/01_drogon_design/realization-*/iter-0"
    )
    # ensemble_path = (
    #     "/home/sigurdp/webviz_testdata/reek_history_match_large/realization-*/iter-0"
    # )

    frequency = Frequency.WEEKLY

    print()
    print("## root_storage_dir:", root_storage_dir)
    print("## ensemble_path:", ensemble_path)
    print("## frequency:", frequency)

    factory = EnsembleSummaryProviderFactory(root_storage_dir)

    print("## Loading data and comparing...")
    _compare_fmu_smry_to_lazy_provider(factory, ensemble_path, frequency)

    print("## done")


# Running:
# python -m webviz_subsurface._providers.ensemble_summary_provider.dev_compare_fmu_to_lazy_provider
if __name__ == "__main__":
    main()

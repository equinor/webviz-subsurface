from typing import Dict
from pathlib import Path
import datetime
import time
import logging

from .ensemble_summary_provider_factory import EnsembleSummaryProviderFactory
from .ensemble_summary_provider_factory import BackingType
from .ensemble_summary_provider import EnsembleSummaryProvider


# -------------------------------------------------------------------------
def _get_n_vectors_one_by_one_all_realizations(
    provider: EnsembleSummaryProvider, num_vectors: int
) -> None:

    all_vectors = provider.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(f"## entering _get_n_vectors_one_by_one_all_realizations({num_vectors}) ...")

    start_tim = time.perf_counter()

    accum_rows = 0
    accum_cols = 0
    for vec_name in vectors_to_get:
        df = provider.get_vectors_df([vec_name])
        accum_rows += df.shape[0]
        accum_cols += df.shape[1]

    elapsed_time_ms = 1000 * (time.perf_counter() - start_tim)

    avg_shape = (
        int(accum_rows / num_vectors),
        int(accum_cols / num_vectors),
    )
    print("## avg shape:", avg_shape)
    print("## num unique dates:", df["DATE"].nunique())
    print("## num unique realizations:", df["REAL"].nunique())
    print("## avg time per vector (ms):", elapsed_time_ms / num_vectors)
    print(
        "## finished _get_n_vectors_one_by_one_all_realizations(), total time (ms)",
        elapsed_time_ms,
    )
    print("## ------------------")


# -------------------------------------------------------------------------
def _get_n_vectors_in_batch_all_realizations(
    provider: EnsembleSummaryProvider, num_vectors: int
) -> None:

    all_vectors = provider.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(f"## entering _get_n_vectors_in_batch_all_realizations({num_vectors}) ...")

    start_tim = time.perf_counter()

    df = provider.get_vectors_df(vectors_to_get)

    elapsed_time_ms = 1000 * (time.perf_counter() - start_tim)

    print("## df shape:", df.shape)
    print("## num unique dates:", df["DATE"].nunique())
    print("## num unique realizations:", df["REAL"].nunique())

    print("## avg time per vector (ms):", elapsed_time_ms / num_vectors)
    print(
        "## finished _get_n_vectors_in_batch_all_realizations(), total time (ms)",
        elapsed_time_ms,
    )
    print("## ------------------")


# -------------------------------------------------------------------------
def _get_n_vectors_for_date_all_realizations(
    provider: EnsembleSummaryProvider, num_vectors: int, date: datetime.datetime
) -> None:

    all_vectors = provider.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(
        f"## entering _get_n_vectors_for_date_all_realizations({num_vectors}, {date}) ..."
    )

    start_tim = time.perf_counter()

    df = provider.get_vectors_for_date_df(date, vectors_to_get)

    elapsed_time_ms = 1000 * (time.perf_counter() - start_tim)

    print("## df shape:", df.shape)
    print("## num unique realizations:", df["REAL"].nunique())
    print(
        "## finished _get_n_vectors_for_date_all_realizations(), total time (ms)",
        elapsed_time_ms,
    )
    print("## ------------------")


# -------------------------------------------------------------------------
def _get_vector_names_filtered_by_value(provider: EnsembleSummaryProvider) -> None:

    print("## ------------------")
    print("## entering _get_vector_names_filtered_by_value() ...")

    start_tim = time.perf_counter()

    filtered_vec_names = provider.vector_names_filtered_by_value(
        exclude_all_values_zero=True, exclude_constant_values=True
    )
    print("## number of names returned:", len(filtered_vec_names))

    elapsed_time_ms = 1000 * (time.perf_counter() - start_tim)

    print(
        "## finished _get_vector_names_filtered_by_value(), total time (ms)",
        elapsed_time_ms,
    )
    print("## ------------------")


# -------------------------------------------------------------------------
def _get_meta_for_n_vectors_one_by_one(
    provider: EnsembleSummaryProvider, num_vectors: int
) -> None:

    all_vectors = provider.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(f"## entering _get_meta_for_n_vectors_one_by_one({num_vectors}) ...")

    start_tim = time.perf_counter()

    for vec_name in vectors_to_get:
        meta_dict = provider.vector_metadata(vec_name)
        print(f"metadata for {vec_name}")
        print(meta_dict)

    elapsed_time_ms = 1000 * (time.perf_counter() - start_tim)

    print(
        "## finished _get_meta_for_n_vectors_one_by_one(), total time (ms)",
        elapsed_time_ms,
    )
    print("## ------------------")


# -------------------------------------------------------------------------
def _run_perf_tests(provider: EnsembleSummaryProvider) -> None:

    all_vector_names = provider.vector_names()
    all_realizations = provider.realizations()
    all_dates = provider.dates()
    num_vectors = len(all_vector_names)
    num_realizations = len(all_realizations)
    num_dates = len(all_dates)
    print("## num_vectors:", num_vectors)
    print("## num_realizations:", num_realizations)
    print("## num_dates", num_dates)

    print()

    _get_meta_for_n_vectors_one_by_one(provider, 10)

    _get_vector_names_filtered_by_value(provider)

    _get_n_vectors_one_by_one_all_realizations(provider, 1)
    _get_n_vectors_one_by_one_all_realizations(provider, 50)

    _get_n_vectors_in_batch_all_realizations(provider, 50)
    _get_n_vectors_in_batch_all_realizations(provider, 99999)

    n = 100
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[int(num_dates / 2)])
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[int(num_dates / 4)])

    n = 99999
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[0])
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[-1])
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[int(num_dates / 2)])
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[int(num_dates / 4)])


# Running:
#   python -m webviz_subsurface._providers.ensemble_summary_provider_perf_testing
#
# Memory profiling with memory-profiler:
#   mprof run --python  webviz_subsurface._providers.ensemble_summary_provider_perf_testing
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print()
    print("## Running EnsembleSummaryProvider performance tests")
    print("## =================================================")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-3s [%(name)s]: %(message)s",
    )
    logging.getLogger("webviz_subsurface").setLevel(level=logging.INFO)
    logging.getLogger("webviz_subsurface").setLevel(level=logging.DEBUG)

    ROOT_STORAGE_DIR = Path("/home/sigurdp/buf/webviz_storage_dir")
    # ROOT_STORAGE_DIR = Path("/home/sigurdp/buf/blobfuse/mounted/webviz_storage_dir")

    PREF_DF_BACKING: BackingType = BackingType.ARROW
    # PREF_DF_BACKING: BackingType = BackingType.PARQUET
    # PREF_DF_BACKING: BackingType = BackingType.INMEM_PARQUET

    ENSEMBLES: Dict[str, str] = {
        # "iter-0": "/home/sigurdp/webviz_testdata/reek_history_match_reduced/realization-*/iter-0",
        # "iter-0": "/home/sigurdp/webviz_testdata/reek_history_match_large/realization-*/iter-0",
        # "iter-0": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-0",
        # "iter-1": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-1",
        # "iter-2": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-2",
        # "iter-3": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-3",
        "iter-0": "/home/sigurdp/gitRoot/hk-webviz-subsurface-testdata/01_drogon_ahm/realization-*/iter-0",
    }

    print()
    print("## ROOT_STORAGE_DIR:", ROOT_STORAGE_DIR)
    print("## PREF_DF_BACKING:", PREF_DF_BACKING)
    print("## ENSEMBLES:", ENSEMBLES)

    print()
    print("## Creating EnsembleSummaryProviderSet...")

    start_tim = time.perf_counter()
    factory = EnsembleSummaryProviderFactory(ROOT_STORAGE_DIR, PREF_DF_BACKING)

    # provider_set = factory.create_provider_set_from_ensemble_smry_fmu(
    #     ENSEMBLES, "daily"
    # )

    # provider_set = (
    #     factory.create_provider_set_PRESAMPLED_from_FAKE_per_realization_arrow_file(
    #         ENSEMBLES, "daily"
    #     )
    # )

    provider_set = (
        factory.create_provider_set_LAZY_from_FAKE_per_realization_arrow_file(
            ENSEMBLES, "daily"
        )
    )

    print(
        "## Done creating EnsembleSummaryProviderSet, elapsed time (s):",
        time.perf_counter() - start_tim,
    )

    print()
    print("## Running perf tests...")
    _run_perf_tests(provider_set.provider("iter-0"))

    print("## done")

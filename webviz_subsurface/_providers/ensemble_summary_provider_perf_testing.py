from typing import Dict
from pathlib import Path
import datetime
import time
import logging

from .ensemble_summary_provider_factory import EnsembleSummaryProviderFactory
from .ensemble_summary_provider_factory import BackingType
from .ensemble_summary_provider import EnsembleSummaryProvider
from .ensemble_summary_provider_set import EnsembleSummaryProviderSet


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
def _run_perf_tests(factory: EnsembleSummaryProviderFactory) -> None:

    ensembles: Dict[str, str] = {
        "iter-0": "/home/sigurdp/webviz_testdata/reek_history_match_reduced/realization-*/iter-0",
        # "iter-0": "/home/sigurdp/webviz_testdata/reek_history_match_large/realization-*/iter-0",
        # "iter-0": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-0",
        # "iter-1": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-1",
        # "iter-2": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-2",
        # "iter-3": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-3",
    }

    # print("## ensembles:")
    # print(json.dumps(ensembles, indent=True))

    print()
    print("## Creating EnsembleSummaryProviderSet...")

    start_tim = time.perf_counter()

    provider_set: EnsembleSummaryProviderSet = (
        factory.create_provider_set_from_ensemble_smry(ensembles, "daily")
    )

    print(
        "## Done creating EnsembleSummaryProviderSet, elapsed time (s):",
        time.perf_counter() - start_tim,
    )

    print()
    print("## provider_set.ensemble_names()", provider_set.ensemble_names())

    provider = provider_set.provider("iter-0")
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
    print()

    _get_vector_names_filtered_by_value(provider)

    _get_n_vectors_one_by_one_all_realizations(provider, 1)
    _get_n_vectors_one_by_one_all_realizations(provider, 50)

    _get_n_vectors_in_batch_all_realizations(provider, 50)
    _get_n_vectors_in_batch_all_realizations(provider, 99999)

    n = 99999
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[0])
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[-1])
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[int(num_dates / 2)])
    _get_n_vectors_for_date_all_realizations(provider, n, all_dates[int(num_dates / 4)])


# Running:
#   python -m webviz_subsurface._models.ensemble_time_series_perf_testing
#
# Memory profiling with memory-profiler:
#   mprof run --python  webviz_subsurface._models.ensemble_time_series_perf_testing
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print()
    print("## Running EnsembleSummaryProvider performance tests")
    print("## ============================================")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-3s [%(name)s]: %(message)s",
    )
    logging.getLogger("webviz_subsurface").setLevel(level=logging.INFO)
    # logging.getLogger("webviz_subsurface").setLevel(level=logging.DEBUG)

    ROOT_STORAGE_DIR = Path("/home/sigurdp/buf/webviz_storage_dir")
    # ROOT_STORAGE_DIR = Path("/home/sigurdp/buf/blobfuse/mounted/webviz_storage_dir")

    BACKING_TYPE: BackingType = BackingType.ARROW
    # BACKING_TYPE: BackingType = BackingType.ARROW_PER_REAL_SMRY_IMPORT_EXPERIMENTAL
    # BACKING_TYPE: BackingType = BackingType.PARQUET
    # BACKING_TYPE: BackingType = BackingType.INMEM_PARQUET

    print()
    print("## ROOT_STORAGE_DIR:", ROOT_STORAGE_DIR)
    print("## BACKING_TYPE:", BACKING_TYPE)

    factory = EnsembleSummaryProviderFactory(ROOT_STORAGE_DIR, BACKING_TYPE)

    _run_perf_tests(factory)

    print("## done")

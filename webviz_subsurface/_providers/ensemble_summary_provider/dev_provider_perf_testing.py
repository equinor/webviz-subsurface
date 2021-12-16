import datetime
import logging
import time
from pathlib import Path
from typing import Optional

from .ensemble_summary_provider import EnsembleSummaryProvider, Frequency
from .ensemble_summary_provider_factory import EnsembleSummaryProviderFactory


def _get_n_vectors_one_by_one_all_realizations(
    provider: EnsembleSummaryProvider,
    resampling_frequency: Optional[Frequency],
    num_vectors: int,
) -> None:

    all_vectors = provider.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(
        f"## entering _get_n_vectors_one_by_one_all_realizations("
        f"{resampling_frequency}, {num_vectors}) ..."
    )

    start_tim = time.perf_counter()

    accum_rows = 0
    accum_cols = 0
    for vec_name in vectors_to_get:
        df = provider.get_vectors_df([vec_name], resampling_frequency)
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


def _get_n_vectors_in_batch_all_realizations(
    provider: EnsembleSummaryProvider,
    resampling_frequency: Optional[Frequency],
    num_vectors: int,
) -> None:

    all_vectors = provider.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(
        f"## entering _get_n_vectors_in_batch_all_realizations("
        f"{resampling_frequency}, {num_vectors}) ..."
    )

    start_tim = time.perf_counter()

    df = provider.get_vectors_df(vectors_to_get, resampling_frequency)

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


def _run_perf_tests(
    provider: EnsembleSummaryProvider, resampling_frequency: Optional[Frequency]
) -> None:

    all_vector_names = provider.vector_names()
    all_realizations = provider.realizations()
    all_dates = provider.dates(resampling_frequency)
    num_vectors = len(all_vector_names)
    num_realizations = len(all_realizations)
    num_dates = len(all_dates)
    print("## num_vectors:", num_vectors)
    print(f"## num_realizations: {num_realizations}   (head:{all_realizations[0:5]})")
    print(f"## num_dates: {num_dates}   (head: {all_dates[0:5]})")

    print()

    _get_meta_for_n_vectors_one_by_one(provider, 10)

    _get_vector_names_filtered_by_value(provider)

    _get_n_vectors_one_by_one_all_realizations(provider, resampling_frequency, 1)
    _get_n_vectors_one_by_one_all_realizations(provider, resampling_frequency, 50)

    _get_n_vectors_in_batch_all_realizations(provider, resampling_frequency, 50)
    _get_n_vectors_in_batch_all_realizations(provider, resampling_frequency, 99999)

    num_vecs = 100
    _get_n_vectors_for_date_all_realizations(
        provider, num_vecs, all_dates[int(num_dates / 2)]
    )
    _get_n_vectors_for_date_all_realizations(
        provider, num_vecs, all_dates[int(num_dates / 4)]
    )

    num_vecs = 99999
    _get_n_vectors_for_date_all_realizations(provider, num_vecs, all_dates[0])
    _get_n_vectors_for_date_all_realizations(provider, num_vecs, all_dates[-1])
    _get_n_vectors_for_date_all_realizations(
        provider, num_vecs, all_dates[int(num_dates / 2)]
    )
    _get_n_vectors_for_date_all_realizations(
        provider, num_vecs, all_dates[int(num_dates / 4)]
    )


def main() -> None:
    print()
    print("## Running EnsembleSummaryProvider performance tests")
    print("## =================================================")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-3s [%(name)s]: %(message)s",
    )
    logging.getLogger("webviz_subsurface").setLevel(level=logging.INFO)
    logging.getLogger("webviz_subsurface").setLevel(level=logging.DEBUG)

    root_storage_dir = Path("/home/sigurdp/buf/webviz_storage_dir")
    # root_storage_dir = Path("/home/sigurdp/buf/blobfuse/mounted/webviz_storage_dir")

    # pylint: disable=line-too-long
    ensemble_path = "/home/sigurdp/gitRoot/webviz-subsurface-testdata/01_drogon_ahm/realization-*/iter-0"
    # ensemble_path = "/home/sigurdp/gitRoot/webviz-subsurface-testdata/01_drogon_design/realization-*/iter-0"
    # ensemble_path = "/home/sigurdp/webviz_testdata/reek_history_match_reduced/realization-*/iter-0"
    # ensemble_path = "/home/sigurdp/webviz_testdata/reek_history_match_large/realization-*/iter-0"

    frequency: Optional[Frequency] = Frequency.DAILY

    print()
    print("## root_storage_dir:", root_storage_dir)
    print("## ensemble_path:", ensemble_path)
    print("## frequency:", frequency)

    print()
    print("## Creating EnsembleSummaryProvider...")

    start_tim = time.perf_counter()
    factory = EnsembleSummaryProviderFactory(
        root_storage_dir, allow_storage_writes=True
    )

    provider = factory.create_from_arrow_unsmry_lazy(
        ens_path=ensemble_path, rel_file_pattern="share/results/unsmry/*.arrow"
    )
    resampling_frequency = frequency

    # provider = factory.create_from_arrow_unsmry_presampled(ensemble_path, frequency)
    # resampling_frequency = None

    print(
        "## Done creating EnsembleSummaryProvider, elapsed time (s):",
        time.perf_counter() - start_tim,
    )

    print()
    print("## Running perf tests...")
    _run_perf_tests(provider, resampling_frequency)

    print("## done")


# Running:
#   python -m webviz_subsurface._providers.ensemble_summary_provider.dev_provider_perf_testing
# -------------------------------------------------------------------------
if __name__ == "__main__":
    main()

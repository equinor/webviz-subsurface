from typing import Dict
from pathlib import Path
import datetime
import time
import json

from .ensemble_time_series_factory import EnsembleTimeSeriesFactory
from .ensemble_time_series_factory import BackingType
from .ensemble_time_series_set import EnsembleTimeSeriesSet
from .ensemble_time_series import EnsembleTimeSeries


# -------------------------------------------------------------------------
def _get_n_vectors_one_by_one_all_realizations(
    ts: EnsembleTimeSeries, num_vectors: int
) -> None:

    all_vectors = ts.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(f"## entering _get_n_vectors_one_by_one_all_realizations({num_vectors}) ...")

    start_tim = time.perf_counter()

    accum_rows = 0
    accum_cols = 0
    for vec_name in vectors_to_get:
        df = ts.get_vectors_df([vec_name])
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
    ts: EnsembleTimeSeries, num_vectors: int
) -> None:

    all_vectors = ts.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(f"## entering _get_n_vectors_in_batch_all_realizations({num_vectors}) ...")

    start_tim = time.perf_counter()

    df = ts.get_vectors_df(vectors_to_get)

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
    ts: EnsembleTimeSeries, num_vectors: int, date: datetime.datetime
) -> None:

    all_vectors = ts.vector_names()
    num_vectors = min(num_vectors, len(all_vectors))
    vectors_to_get = all_vectors[0:num_vectors]

    print("## ------------------")
    print(
        f"## entering _get_n_vectors_for_date_all_realizations({num_vectors}, {date}) ..."
    )

    start_tim = time.perf_counter()

    df = ts.get_vectors_for_date_df(date, vectors_to_get)

    elapsed_time_ms = 1000 * (time.perf_counter() - start_tim)

    print("## df shape:", df.shape)
    print("## num unique realizations:", df["REAL"].nunique())
    print(
        "## finished _get_n_vectors_for_date_all_realizations(), total time (ms)",
        elapsed_time_ms,
    )
    print("## ------------------")


# -------------------------------------------------------------------------
def _get_vector_names_filtered_by_value(ts: EnsembleTimeSeries) -> None:

    print("## ------------------")
    print("## entering _get_vector_names_filtered_by_value() ...")

    start_tim = time.perf_counter()

    filtered_vec_names = ts.vector_names_filtered_by_value(
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
def _run_perf_tests(factory: EnsembleTimeSeriesFactory) -> None:

    ensembles: Dict[str, str] = {
        # "iter-0": "/home/sigurdp/webviz_testdata/reek_history_match_reduced/realization-*/iter-0",
        "iter-0": "/home/sigurdp/webviz_testdata/reek_history_match_large/realization-*/iter-0",
        # "iter-0": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-0",
        # "iter-1": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-1",
        # "iter-2": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-2",
        # "iter-3": "/home/sigurdp/gitRoot/webviz-subsurface-testdata/reek_history_match/realization-*/iter-3",
    }

    print("ensembles:")
    print(json.dumps(ensembles, indent=True))

    print()
    print("## Creating EnsembleTimeSeriesSet...")

    start_tim = time.perf_counter()

    ts_set: EnsembleTimeSeriesSet = factory.create_time_series_set_from_ensemble_smry(
        ensembles, "daily"
    )

    print(
        "## Done creating EnsembleTimeSeriesSet, elapsed time (s):",
        time.perf_counter() - start_tim,
    )

    print()
    print("## ts_set.ensemble_names()", ts_set.ensemble_names())

    ts = ts_set.ensemble("iter-0")
    all_vector_names = ts.vector_names()
    all_realizations = ts.realizations()
    all_dates = ts.dates()
    num_vectors = len(all_vector_names)
    num_realizations = len(all_realizations)
    num_dates = len(all_dates)
    print("## num_vectors:", num_vectors)
    print("## num_realizations:", num_realizations)
    print("## num_dates", num_dates)

    print()
    print()

    _get_vector_names_filtered_by_value(ts)

    _get_n_vectors_one_by_one_all_realizations(ts, 1)
    _get_n_vectors_one_by_one_all_realizations(ts, 50)

    _get_n_vectors_in_batch_all_realizations(ts, 50)
    _get_n_vectors_in_batch_all_realizations(ts, 99999)

    n = 99999
    _get_n_vectors_for_date_all_realizations(ts, n, all_dates[0])
    _get_n_vectors_for_date_all_realizations(ts, n, all_dates[-1])
    _get_n_vectors_for_date_all_realizations(ts, n, all_dates[int(num_dates / 2)])
    _get_n_vectors_for_date_all_realizations(ts, n, all_dates[int(num_dates / 4)])


# Running:
#   python -m webviz_subsurface._models.ensemble_time_series_perf_testing
#
# Memory profiling with memory-profiler:
#   mprof run --python  webviz_subsurface._models.ensemble_time_series_perf_testing
# -------------------------------------------------------------------------
if __name__ == "__main__":
    print()
    print("## Running EnsembleTimeSeries performance tests")
    print("## ============================================")

    ROOT_STORAGE_DIR = Path("/home/sigurdp/buf/webviz_storage_dir")
    BACKING_TYPE: BackingType = BackingType.ARROW

    factory = EnsembleTimeSeriesFactory(ROOT_STORAGE_DIR, BACKING_TYPE)

    print()
    print("ROOT_STORAGE_DIR:", ROOT_STORAGE_DIR)
    print("BACKING_TYPE:", BACKING_TYPE)

    _run_perf_tests(factory)

    print("done")

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
    print("## len(ts.vector_names())", len(ts.vector_names()))
    print("## len(ts.realizations())", len(ts.realizations()))
    print("## len(ts.dates())", len(ts.dates()))

    all_dates = ts.dates()

    print()
    print()

    _get_n_vectors_one_by_one_all_realizations(ts, 50)

    _get_n_vectors_in_batch_all_realizations(ts, 50)
    _get_n_vectors_in_batch_all_realizations(ts, 9999)

    _get_n_vectors_for_date_all_realizations(ts, 9999, all_dates[0])
    _get_n_vectors_for_date_all_realizations(ts, 9999, all_dates[-1])


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

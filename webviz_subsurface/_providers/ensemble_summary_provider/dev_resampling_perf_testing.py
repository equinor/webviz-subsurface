import logging
import time

import numpy as np
import pyarrow as pa

from webviz_subsurface._providers.ensemble_summary_provider._resampling import (
    sample_segmented_multi_real_table_at_date,
)


def _create_table(
    num_reals: int, start_date: np.datetime64, end_date: np.datetime64, num_columns: int
) -> pa.Table:

    date_arr_np = np.empty(0, np.datetime64)
    real_arr_np = np.empty(0, np.int32)

    for real in range(0, num_reals):
        dates_for_this_real = np.arange(start_date, end_date + 1)
        dates_for_this_real = dates_for_this_real.astype("datetime64[ms]")
        real_arr_np = np.concatenate(
            (real_arr_np, np.full(len(dates_for_this_real), real))
        )
        date_arr_np = np.concatenate((date_arr_np, dates_for_this_real))

    print(
        f"real_arr_np (num unique={len(np.unique(real_arr_np))}  len={len(real_arr_np)}):"
    )
    print(real_arr_np)
    print(
        f"date_arr_np (num unique={len(np.unique(date_arr_np))}  len={len(date_arr_np)}):"
    )
    print(date_arr_np)

    field_list = []
    columndata_list = []
    field_list.append(pa.field("DATE", pa.timestamp("ms")))
    field_list.append(pa.field("REAL", pa.int64()))
    columndata_list.append(pa.array(date_arr_np))
    columndata_list.append(pa.array(real_arr_np))

    num_rows = len(real_arr_np)

    for colnum in range(0, num_columns):
        if (colnum % 2) == 0:
            metadata = {b"is_rate": b'{"is_rate": False}'}
        else:
            metadata = {b"is_rate": b'{"is_rate": True}'}

        field_list.append(pa.field(f"c_{colnum}", pa.float32(), metadata=metadata))

        valarr = np.linspace(colnum, colnum + num_rows, num_rows)
        columndata_list.append(pa.array(valarr))

    schema = pa.schema(field_list)
    return pa.table(columndata_list, schema=schema)


def main() -> None:
    print()
    print("## Running resampling performance tests")
    print("## =================================================")

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)-3s [%(name)s]: %(message)s",
    )
    logging.getLogger("webviz_subsurface").setLevel(level=logging.INFO)
    logging.getLogger("webviz_subsurface").setLevel(level=logging.DEBUG)

    # table = _create_table(
    #     num_reals=3,
    #     start_date=np.datetime64("2020-12-30"),
    #     end_date=np.datetime64("2021-01-05"),
    #     num_columns=4,
    # )

    table = _create_table(
        num_reals=100,
        start_date=np.datetime64("2000-01-01", "M"),
        end_date=np.datetime64("2099-12-31", "M"),
        num_columns=10000,
    )

    print("## table shape (rows,columns):", table.shape)
    # print(table.to_pandas())

    start_tim = time.perf_counter()

    res = sample_segmented_multi_real_table_at_date(
        table, np.datetime64("2098-01-03", "ms")
    )

    # res = sample_segmented_multi_real_table_at_date(
    #     table, np.datetime64("2098-01-01", "ms")
    # )

    elapsed_time_ms = int(1000 * (time.perf_counter() - start_tim))

    # print(res)
    # print(res.to_pandas())

    print("## res shape:", res.shape)

    print(f"## sample at date took: {elapsed_time_ms}ms")


# Running:
#   python -m webviz_subsurface._providers.ensemble_summary_provider.dev_resampling_perf_testing
# -------------------------------------------------------------------------
if __name__ == "__main__":
    main()

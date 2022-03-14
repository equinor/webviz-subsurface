import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

from webviz_subsurface._providers.ensemble_summary_provider._table_utils import (
    find_intersection_of_realization_dates,
    find_min_max_date_per_realization,
    find_union_of_realization_dates,
)

# Since PyArrow's actual compute functions are not seen by pylint
# pylint: disable=no-member


def _create_table_from_row_data(per_row_input_data: list) -> pa.Table:
    # Turn rows into columns
    columns_with_header = list(zip(*per_row_input_data))

    input_dict = {}
    field_list = []
    for col in columns_with_header:
        colname = col[0]
        coldata = col[1:]
        input_dict[colname] = coldata

        if colname == "DATE":
            field_list.append(pa.field("DATE", pa.timestamp("ms")))
        elif colname == "REAL":
            field_list.append(pa.field("REAL", pa.int64()))
        else:
            field_list.append(pa.field(colname, pa.float32()))

    table = pa.Table.from_pydict(input_dict, schema=pa.schema(field_list))

    return table


def test_intersection_of_dates() -> None:
    # fmt:off
    input_data = [
        ["DATE",                             "REAL",  "V"],
        [np.datetime64("2020-01-03", "ms"),  1,       30.0],
        [np.datetime64("2020-01-02", "ms"),  1,       20.0],
        [np.datetime64("2020-01-01", "ms"),  1,       10.0],
        [np.datetime64("2020-01-01", "ms"),  2,       10.0],
        [np.datetime64("2020-01-02", "ms"),  2,       20.0],
        [np.datetime64("2099-01-02", "ms"),  3,       20.0],
    ]
    # fmt:on
    full_table = _create_table_from_row_data(input_data)

    # Intersection should end up empty due to outlier in real 3
    date_list_full = find_intersection_of_realization_dates(full_table).tolist()
    assert len(date_list_full) == 0

    r12_table = full_table.filter(
        pc.is_in(full_table["REAL"], value_set=pa.array([1, 2]))
    )
    date_list_r12 = find_intersection_of_realization_dates(r12_table).tolist()
    assert date_list_r12 == sorted(date_list_r12)
    assert len(date_list_r12) == 2

    r1_table = full_table.filter(pc.equal(full_table["REAL"], 1))
    date_list_r1 = find_intersection_of_realization_dates(r1_table).tolist()
    assert date_list_r1 == sorted(date_list_r1)
    assert len(date_list_r1) == 3

    empty_table = full_table.filter(pc.equal(full_table["REAL"], 99))
    date_list_empty = find_intersection_of_realization_dates(empty_table).tolist()
    assert len(date_list_empty) == 0


def test_union_of_dates() -> None:
    # fmt:off
    input_data = [
        ["DATE",                             "REAL",  "V"],
        [np.datetime64("2020-01-03", "ms"),  1,       20.0],
        [np.datetime64("2020-01-02", "ms"),  1,       10.0],
        [np.datetime64("2020-01-01", "ms"),  2,       10.0],
    ]
    # fmt:on
    table = _create_table_from_row_data(input_data)

    date_list = find_union_of_realization_dates(table).tolist()
    assert date_list == sorted(date_list)
    assert len(date_list) == 3

    empty_table = table.filter(pc.equal(table["REAL"], 99))
    date_list_empty = find_union_of_realization_dates(empty_table).tolist()
    assert len(date_list_empty) == 0


def test_find_min_max_date_per_realization() -> None:
    # fmt:off
    input_data = [
        ["DATE",                             "REAL",  "V"],
        [np.datetime64("2020-01-03", "ms"),  1,       20.0],
        [np.datetime64("2020-01-02", "ms"),  1,       10.0],
        [np.datetime64("2020-01-01", "ms"),  2,       10.0],
    ]
    # fmt:on
    table = _create_table_from_row_data(input_data)

    minmaxlist = find_min_max_date_per_realization(table)
    assert len(minmaxlist) == 2

    assert isinstance(minmaxlist[0][0], np.datetime64)

    r1_min_max = minmaxlist[0]
    assert r1_min_max[0] == np.datetime64("2020-01-02", "ms")
    assert r1_min_max[1] == np.datetime64("2020-01-03", "ms")

    r2_min_max = minmaxlist[1]
    assert r2_min_max[0] == np.datetime64("2020-01-01", "ms")
    assert r2_min_max[1] == np.datetime64("2020-01-01", "ms")

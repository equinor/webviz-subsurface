import json
from typing import Dict, List, Tuple

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc

_MAIN_WEBVIZ_METADATA_KEY = b"webviz"
_PER_VECTOR_MIN_MAX_KEY = "per_vector_min_max"


def find_min_max_for_numeric_table_columns(
    table: pa.Table,
) -> Dict[str, dict]:
    """Determine per-vector min/max values and return as dictionary indexed by vector name"""
    ret_dict = {}
    for field in table.schema:
        if pa.types.is_floating(field.type):
            # pylint: disable=no-member
            minmax = pc.min_max(table[field.name])
            ret_dict[field.name] = {
                "min": minmax.get("min").as_py(),
                "max": minmax.get("max").as_py(),
            }

    return ret_dict


def add_per_vector_min_max_to_table_schema_metadata(
    table: pa.Table, per_vector_min_max: Dict[str, dict]
) -> pa.Table:
    """Store dict with per-vector min/max values schema's metadata"""

    webviz_meta = {_PER_VECTOR_MIN_MAX_KEY: per_vector_min_max}
    new_combined_meta = {}
    if table.schema.metadata is not None:
        new_combined_meta.update(table.schema.metadata)
    new_combined_meta.update({_MAIN_WEBVIZ_METADATA_KEY: json.dumps(webviz_meta)})
    table = table.replace_schema_metadata(new_combined_meta)
    return table


def get_per_vector_min_max_from_schema_metadata(schema: pa.Schema) -> Dict[str, dict]:
    """Extract dict containing per-vector min/max values from the schema-level metadata"""

    webviz_meta = json.loads(schema.metadata[_MAIN_WEBVIZ_METADATA_KEY])
    return webviz_meta[_PER_VECTOR_MIN_MAX_KEY]


def find_intersection_of_realization_dates(table: pa.Table) -> np.ndarray:
    """Find the intersection of dates present in all the realizations.
    The input table must contain both REAL and DATE columns, but this function makes
    no assumptions about sorting of either column.
    The returned array of dates will always be sorted.
    """

    unique_reals = table.column("REAL").unique().to_numpy()

    date_intersection = None
    for real in unique_reals:
        # pylint: disable=no-member
        real_mask = pc.is_in(table["REAL"], value_set=pa.array([real]))
        dates_in_real = table.filter(real_mask).column("DATE").unique().to_numpy()
        if date_intersection is None:
            date_intersection = np.sort(dates_in_real)
        else:
            # The intersection returned by intersect1d() is sorted
            date_intersection = np.intersect1d(
                date_intersection, dates_in_real, assume_unique=True
            )

    if date_intersection is not None:
        return date_intersection

    return np.empty(0, dtype=np.datetime64)


def find_union_of_realization_dates(table: pa.Table) -> np.ndarray:
    """Find the union of dates in all the realizations.
    The input table must contain a DATE column, but no previous sorting is required.
    The returned array of dates is always sorted.
    """

    unique_dates = table.column("DATE").unique().to_numpy()
    return np.sort(unique_dates)


def find_min_max_date_per_realization(
    table: pa.Table,
) -> List[Tuple[np.datetime64, np.datetime64]]:
    """Find the min and max dates within each realization in the table."""

    unique_reals = table.column("REAL").unique().to_numpy()

    minmax_np_list: List[Tuple[np.datetime64, np.datetime64]] = []

    for real in unique_reals:
        # pylint: disable=no-member
        real_table = table.filter(pc.equal(table["REAL"], real))
        minmax = pc.min_max(real_table["DATE"])

        # Make sure we have pa.timestamp("ms") as datatype for the actual scalar values
        # in the returned StructScalar before we convert to numpy
        minmax_np_list.append(
            (
                np.datetime64(minmax.get("min").cast(pa.timestamp("ms")).value, "ms"),
                np.datetime64(minmax.get("max").cast(pa.timestamp("ms")).value, "ms"),
            ),
        )

    return minmax_np_list

from typing import Dict
import json

import pyarrow as pa
import pyarrow.compute as pc

_MAIN_WEBVIZ_METADATA_KEY = b"webviz"
_PER_VECTOR_MIN_MAX_KEY = "per_vector_min_max"


# -------------------------------------------------------------------------
def find_min_max_for_numeric_table_columns(
    table: pa.Table,
) -> Dict[str, dict]:

    ret_dict = {}
    for field in table.schema:
        if pa.types.is_floating(field.type):
            minmax = pc.min_max(table[field.name])
            ret_dict[field.name] = {
                "min": minmax.get("min").as_py(),
                "max": minmax.get("max").as_py(),
            }

    return ret_dict


# -------------------------------------------------------------------------
def add_per_vector_min_max_to_table_schema_metadata(
    table: pa.Table, per_vector_min_max: Dict[str, dict]
) -> pa.Table:
    webviz_meta = {_PER_VECTOR_MIN_MAX_KEY: per_vector_min_max}
    new_combined_meta = {}
    if table.schema.metadata is not None:
        new_combined_meta.update(table.schema.metadata)
    new_combined_meta.update({_MAIN_WEBVIZ_METADATA_KEY: json.dumps(webviz_meta)})
    table = table.replace_schema_metadata(new_combined_meta)
    return table


# -------------------------------------------------------------------------
def get_per_vector_min_max_from_schema_metadata(schema: pa.Schema) -> Dict[str, dict]:
    webviz_meta = json.loads(schema.metadata[_MAIN_WEBVIZ_METADATA_KEY])
    return webviz_meta[_PER_VECTOR_MIN_MAX_KEY]

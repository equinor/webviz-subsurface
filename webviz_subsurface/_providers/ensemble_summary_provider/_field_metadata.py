import json
from typing import Any, Dict, Optional

import pyarrow as pa


def is_rate_from_field_meta(field: pa.Field) -> bool:
    """Determine if the field is a rate by querying for the "is_rate" keyword in the
    field's metadata
    """
    # This is expensive wrt performance. Should avoid JSON parsing here
    if field.metadata:
        meta_as_str = field.metadata.get(b"smry_meta")
        if meta_as_str:
            meta_dict = json.loads(meta_as_str)
            if meta_dict.get("is_rate") is True:
                return True

    return False


def create_vector_metadata_dict_from_field_meta(
    field: pa.Field,
) -> Optional[Dict[str, Any]]:
    """Create dictionary with vector metadata from data in the field's metadata"""
    if field.metadata:
        meta_as_str = field.metadata.get(b"smry_meta")
        if meta_as_str:
            return json.loads(meta_as_str)

    return None

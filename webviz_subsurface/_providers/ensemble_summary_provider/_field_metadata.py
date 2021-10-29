import json
from typing import Any, Dict, Optional

import pyarrow as pa

from .ensemble_summary_provider import VectorMetadata


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


def create_vector_metadata_from_field_meta(field: pa.Field) -> Optional[VectorMetadata]:
    """Create VectorMetadata from keywords stored in the field's metadata"""

    meta_dict = create_vector_metadata_dict_from_field_meta(field)
    if not meta_dict:
        return None

    try:
        unit = str(meta_dict["unit"])
        is_total = bool(meta_dict["is_total"])
        is_rate = bool(meta_dict["is_rate"])
        is_historical = bool(meta_dict["is_historical"])
        keyword = str(meta_dict["keyword"])
    except KeyError:
        return None

    wgname = meta_dict.get("wgname")
    get_num = meta_dict.get("get_num")

    return VectorMetadata(
        unit=unit,
        is_total=is_total,
        is_rate=is_rate,
        is_historical=is_historical,
        keyword=keyword,
        wgname=wgname,
        get_num=get_num,
    )

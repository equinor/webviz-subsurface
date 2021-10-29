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


def is_rate_from_field_meta_FLAT_PROPS(field: pa.Field) -> bool:
    """Determine if the field is a rate by querying for the "is_rate" keyword in the
    field's metadata
    """

    # What should be done here if the is_rate key is not found?
    # Just assume that it is not a rate or throw an exception?

    meta_dict = field.metadata
    if meta_dict is not None:
        return bool(meta_dict.get(b"is_rate") == b"True")
    else:
        return False

    # meta_dict = field.metadata
    # if meta_dict is None:
    #     raise ValueError("Field has no metadata")
    # is_rate_bytestr = meta_dict.get(b"is_rate")
    # if is_rate_bytestr is None:
    #     raise KeyError("is_rate key not found in field's metadata")
    # return bool(is_rate_bytestr == b"True")

    # try:
    #     return bool(field.metadata[b"is_rate"] == b"True")
    # except (TypeError, KeyError) as e:
    #     raise ValueError(
    #         "Field is missing metadata or 'is_rate' key was not found"
    #     ) from e

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


def create_vector_metadata_from_field_meta_FLAT_PROPS(
    field: pa.Field,
) -> Optional[VectorMetadata]:
    """Create VectorMetadata from keywords stored in the field's metadata"""

    # Note that when we query the values in the field.metadata we always get byte strings
    # back from pyarrow. Further, ecl2df writes all the values as strings, so we must
    # convert these to the correct types before creating the VectorMetadata instance.
    # See also ecl2df code:
    #   https://github.com/equinor/ecl2df/blob/0e30fb8046bf17fd338bb468584985c5d816e2f6/ecl2df/summary.py#L441

    # Currently, based on the ecl2df code, we assume that all keys except for 'get_num'
    # must be present in order to return a valid metadata object
    # https://github.com/equinor/ecl2df/blob/0e30fb8046bf17fd338bb468584985c5d816e2f6/ecl2df/summary.py#L541-L552

    meta_dict = field.metadata
    if not meta_dict:
        return None

    try:
        unit_bytestr = meta_dict[b"unit"]
        is_total_bytestr = meta_dict[b"is_total"]
        is_rate_bytestr = meta_dict[b"is_rate"]
        is_historical_bytestr = meta_dict[b"is_historical"]
        keyword_bytestr = meta_dict[b"keyword"]
    except KeyError:
        return None

    wgname_bytestr = meta_dict.get(b"wgname")
    get_num_bytestr = meta_dict.get(b"get_num")
    wgname = str(wgname_bytestr) if wgname_bytestr else None
    get_num = int(get_num_bytestr) if get_num_bytestr else None

    return VectorMetadata(
        unit=str(unit_bytestr),
        is_total=bool(is_total_bytestr == b"True"),
        is_rate=bool(is_rate_bytestr == b"True"),
        is_historical=bool(is_historical_bytestr == b"True"),
        keyword=str(keyword_bytestr),
        wgname=str(wgname_bytestr),
        get_num=get_num,
    )

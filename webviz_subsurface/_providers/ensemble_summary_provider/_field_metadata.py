from typing import Optional

import pyarrow as pa

from .ensemble_summary_provider import VectorMetadata


def is_rate_from_field_meta(field: pa.Field) -> bool:
    """Determine if the field is a rate by querying for the "is_rate" keyword in the
    field's metadata.
    Will silently return False if no metadata exists for the field, but will raise an
    exception if the field HAS metadata but the 'is_rate' key is missing.
    """
    # What should be done here if the is_rate key is not found?
    # Should we just assume that it is not a rate or throw an exception?

    meta_dict = field.metadata
    if meta_dict is not None:
        try:
            is_rate_bytestr = meta_dict[b"is_rate"]
            return bool(is_rate_bytestr == b"True")
        except KeyError as exc:
            raise KeyError(
                f"Field {field.name} has metadata, but the is_rate key was not found"
            ) from exc
    return False

    # meta_dict = field.metadata
    # if meta_dict is None:
    #     raise ValueError(f"Field {field.name} has no metadata")
    # is_rate_bytestr = meta_dict.get(b"is_rate")
    # if is_rate_bytestr is None:
    #     raise KeyError(f"is_rate key not found in metadata for field {field.name}")
    # return bool(is_rate_bytestr == b"True")

    # try:
    #     return bool(field.metadata[b"is_rate"] == b"True")
    # except (TypeError, KeyError) as e:
    #     raise ValueError(
    #         "Field is missing metadata or 'is_rate' key was not found"
    #     ) from e


def create_vector_metadata_from_field_meta(
    field: pa.Field,
) -> Optional[VectorMetadata]:
    """Create VectorMetadata from keywords stored in the field's metadata"""

    # Note that when we query the values in the field.metadata we always get byte strings
    # back from pyarrow. Further, ecl2df writes all the values as strings, so we must
    # convert these to the correct types before creating the VectorMetadata instance.
    # See also ecl2df code:
    # https://github.com/equinor/ecl2df/blob/0e30fb8046bf17fd338bb468584985c5d816e2f6/ecl2df/summary.py#L441

    # Currently, based on the ecl2df code, we assume that all keys except for 'get_num'
    # and 'wgname' must be present in order to return a valid metadata object
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

    # print(f"unit_bytestr:  |{unit_bytestr}|")
    # print(f"is_total_bytestr:  |{is_total_bytestr}|")
    # print(f"is_rate_bytestr:  |{is_rate_bytestr}|")
    # print(f"is_historical_bytestr:  |{is_historical_bytestr}|")
    # print(f"keyword_bytestr:  |{keyword_bytestr}|")
    # print(f"wgname_bytestr:  |{wgname_bytestr}|")
    # print(f"get_num_bytestr:  |{get_num_bytestr}|")

    wgname: Optional[str] = None
    if wgname_bytestr and wgname_bytestr != b"None":
        wgname = wgname_bytestr.decode("ascii")

    get_num: Optional[int] = None
    if get_num_bytestr and get_num_bytestr != b"None":
        get_num = int(get_num_bytestr.decode("ascii"))

    return VectorMetadata(
        unit=unit_bytestr.decode("ascii"),
        is_total=bool(is_total_bytestr == b"True"),
        is_rate=bool(is_rate_bytestr == b"True"),
        is_historical=bool(is_historical_bytestr == b"True"),
        keyword=keyword_bytestr.decode("ascii"),
        wgname=wgname,
        get_num=get_num,
    )

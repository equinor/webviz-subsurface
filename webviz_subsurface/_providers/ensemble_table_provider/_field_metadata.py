from typing import Optional

import pyarrow as pa

from .ensemble_table_provider import TableVectorMetadata


def create_vector_metadata_from_field_meta(
    field: pa.Field,
) -> Optional[TableVectorMetadata]:
    """Create VectorMetadata from keywords stored in the field's metadata"""

    meta_dict = field.metadata
    if not meta_dict:
        return None

    try:
        unit_bytestr = meta_dict[b"unit"]
    except KeyError:
        return None

    return TableVectorMetadata(
        unit=unit_bytestr.decode("ascii"),
    )

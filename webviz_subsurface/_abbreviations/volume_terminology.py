import json
import pathlib
from typing import Optional

_DATA_PATH = pathlib.Path(__file__).parent.absolute() / "abbreviation_data"

VOLUME_TERMINOLOGY = json.loads((_DATA_PATH / "volume_terminology.json").read_text())


def volume_description(column: str, metadata: Optional[dict] = None):
    """Return description for the column if defined"""
    if metadata is not None:
        try:
            return metadata[column]["description"]
        except KeyError:
            pass
    try:
        description = VOLUME_TERMINOLOGY[column]["description"]
    except KeyError:
        description = column
    return description


def volume_unit(column: str, metadata: Optional[dict] = None):
    """Return unit for the column if defined"""
    if metadata is not None:
        try:
            return metadata[column]["unit"]
        except KeyError:
            pass
    return ""


def column_title(response: str, metadata: dict):
    unit = volume_unit(response, metadata)
    return f"{volume_description(response, metadata)}" + (f" [{unit}]" if unit else "")

import json
import pathlib
from typing import Optional, Union

_DATA_PATH = pathlib.Path(__file__).parent.absolute() / "abbreviation_data"

VOLUME_TERMINOLOGY = json.loads((_DATA_PATH / "volume_terminology.json").read_text())
VOLUME_TERMINOLOGY_METRIC = json.loads(
    (_DATA_PATH / "volume_terminology_metric.json").read_text()
)


def volume_description(column: str, metadata: Optional[Union[dict, str]] = None):
    """Return description for the column if defined"""
    if metadata is not None:
        try:
            if isinstance(metadata, dict):
                return metadata[column]["description"]
            if isinstance(metadata, str) and metadata.lower() == "metric":
                return VOLUME_TERMINOLOGY_METRIC[column]["description"]
        except KeyError:
            pass
    try:
        description = VOLUME_TERMINOLOGY[column]["description"]
    except KeyError:
        description = column
    return description


def volume_unit(column: str, metadata: Optional[Union[dict, str]] = None):
    """Return unit for the column if defined"""
    if metadata is not None:
        try:
            if isinstance(metadata, dict):
                return metadata[column]["unit"]
            if isinstance(metadata, str) and metadata.lower() == "metric":
                return VOLUME_TERMINOLOGY_METRIC[column]["unit"]
        except KeyError:
            pass
    return ""


def column_title(response: str, metadata: Union[dict, str]):
    unit = volume_unit(response, metadata)
    return f"{volume_description(response, metadata)}" + (f" [{unit}]" if unit else "")

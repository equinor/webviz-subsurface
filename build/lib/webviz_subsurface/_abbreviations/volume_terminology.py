import json
import pathlib

_DATA_PATH = pathlib.Path(__file__).parent.absolute() / "abbreviation_data"

VOLUME_TERMINOLOGY = json.loads((_DATA_PATH / "volume_terminology.json").read_text())


def volume_description(column: str) -> str:
    """Return description for the column if defined"""
    try:
        label = VOLUME_TERMINOLOGY[column]["label"]
    except KeyError:
        label = column
    return label


def volume_unit(column: str) -> str:
    """Return unit for the column if defined"""
    try:
        unit = VOLUME_TERMINOLOGY[column]["unit"]
    except KeyError:
        unit = ""
    return unit


def volume_simulation_vector_match(column: str) -> list:
    """Return a list of simulation vectors that match the column
    Useful to verify/propose data to compare.
    """
    try:
        vectors = VOLUME_TERMINOLOGY[column]["eclsum"]
    except KeyError:
        vectors = []
    return vectors if isinstance(vectors, list) else [vectors]

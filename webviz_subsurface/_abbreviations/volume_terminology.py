import json
import pathlib


_DATA_PATH = pathlib.Path(__file__).parent.absolute() / "abbreviation_data"

VOLUME_TERMINOLOGY = json.loads((_DATA_PATH / "volume_terminology.json").read_text())


def volume_description(column_key: str):
    """Return description for the column_key if defined"""
    try:
        label = VOLUME_TERMINOLOGY[column_key]["label"]
    except KeyError:
        label = column_key
    return label


def volume_unit(column_key: str):
    """Return unit for the column_key if defined"""
    try:
        unit = VOLUME_TERMINOLOGY[column_key]["unit"]
    except KeyError:
        unit = ""
    return unit


def volume_recoverable(column_key: str):
    """Check if the column_key is defined as recoverable"""
    try:
        recoverable = VOLUME_TERMINOLOGY[column_key]["recoverable"].lower() == "true"
    except KeyError:
        recoverable = False
    return recoverable


def volume_simulation_vector_match(column_key: str):
    """Return a list of simulation vectors that match the column_key
    Useful to verify/propose data to compare.
    """
    try:
        vectors = VOLUME_TERMINOLOGY[column_key]["eclsum"]
        vectors = [vectors] if not isinstance(vectors, list) else vectors
    except KeyError:
        vectors = []
    return vectors if isinstance(vectors, list) else [vectors]


def simulation_vector_column_match(vector: str):
    """Return a column_key (str) that match the simulation vector
    If not match: return None
    Useful to verify/propose data to compare.
    """
    for column_key, metadata in VOLUME_TERMINOLOGY.items():
        if vector in metadata.get("eclsum", ""):
            return column_key
    return None

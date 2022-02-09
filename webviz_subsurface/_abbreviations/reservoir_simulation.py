import json
import pathlib
import warnings
from typing import Dict, Optional, Tuple, cast

import pandas as pd
from webviz_subsurface_components import VectorDefinition, VectorDefinitions

_DATA_PATH = pathlib.Path(__file__).parent.absolute() / "abbreviation_data"

SIMULATION_VECTOR_TERMINOLOGY = VectorDefinitions

RESERVOIR_SIMULATION_UNIT_TERMINOLOGY = json.loads(
    (_DATA_PATH / "reservoir_simulation_unit_terminology.json").read_text()
)


def simulation_unit_reformat(ecl_unit: str, unit_set: str = "METRIC") -> str:
    """Returns the simulation unit in a different, more human friendly, format if possible,
    otherwise returns the simulation unit.
    * `ecl_unit`: Reservoir simulation vector unit to reformat
    * `unit_set`: Currently only valid option is the default "METRIC" (defined as in Eclipse E100)
    """
    return RESERVOIR_SIMULATION_UNIT_TERMINOLOGY[unit_set].get(ecl_unit, ecl_unit)


def simulation_vector_base(vector: str) -> str:
    """Returns base name of a simulation vector on Eclipse format.
    E.g. WOPR for WOPR:OP_1 and ROIP for ROIP_REG:1.
    Some description: If a vector contains a :, the first up to 5 characters describe the vector
    base. In that case, if the vector base name is shorter than 5 characters, _ is used to fill
    up the first five characters. Therefore splitting on first _ and limiting to max five
    characters to identify the base name.
    """
    return vector.split(":", 1)[0].split("_", 1)[0][:5] if ":" in vector else vector


def simulation_vector_description(
    vector: str,
    user_defined_vector_definitions: Optional[Dict[str, VectorDefinition]] = None,
) -> str:
    """Returns a more human friendly description of the simulation vector if possible,
    otherwise returns the input as is.

    # TODO: Remove support for "AVG_" and "INTVL_" when all usage is deprecated.
    """
    prefix = ""
    suffix = ""
    if vector.startswith("AVG_"):
        prefix = "Average "
        vector = vector[4:]
    elif vector.startswith("PER_DAY_"):
        prefix = "Average "
        suffix = " Per day"
        vector = vector[8:]
    elif vector.startswith("INTVL_"):
        prefix = "Interval "
        vector = vector[6:]
    elif vector.startswith("PER_INTVL_"):
        prefix = "Interval "
        vector = vector[10:]

    vector_name: str
    node: Optional[str]
    if ":" in vector:
        [vector_name, node] = vector.split(":", 1)
    else:
        vector_name = vector
        node = None

    def _get_vector_definition(vector: str) -> Optional[VectorDefinition]:
        """Get vector definition. Fetch user defined if existing"""
        if (
            user_defined_vector_definitions
            and vector in user_defined_vector_definitions
        ):
            return user_defined_vector_definitions[vector]
        if vector in SIMULATION_VECTOR_TERMINOLOGY:
            return SIMULATION_VECTOR_TERMINOLOGY[vector]
        return None

    if len(vector_name) == 8:
        if vector_name[0] == "R":
            # Region vectors for other FIP regions than FIPNUM are written on a special form:
            # 8 signs, with the last 3 defining the region.
            # E.g.: For an array "FIPREG": ROIP is ROIP_REG, RPR is RPR__REG and ROIPL is ROIPLREG
            # Underscores _ are always used to fill
            [vector_base_name, fip] = [vector_name[0:5].rstrip("_"), vector_name[5:]]

            _definition = _get_vector_definition(vector_base_name)
            if _definition and _definition["type"] == "region":
                return (
                    f"{prefix}{_definition['description']}{suffix}, region {fip} {node}"
                )
        elif vector_name.startswith("W") and vector_name[4] == "L":
            # These are completion vectors, e.g. WWCTL:__1:OP_1 and WOPRL_10:OP_1 for
            # water-cut in OP_1 completion 1 and oil production rate in OP_1 completion 10
            [vector_base_name, comp] = [vector_name[0:5], vector_name[5:].lstrip("_")]

            _definition = _get_vector_definition(vector_base_name)
            if _definition and _definition["type"] == "completion":
                return (
                    f"{prefix}{_definition['description']}"
                    f"{suffix}, well {node} completion {comp}"
                )

    _definition = _get_vector_definition(vector_name)
    if _definition:
        if node is None:
            return prefix + _definition["description"] + suffix
        return (
            f"{prefix}{_definition['description']}{suffix}, "
            f"{_definition['type'].replace('_', ' ')} {node}"
        )

    if not vector.startswith(
        ("AU", "BU", "CU", "FU", "GU", "RU", "SU", "WU", "Recovery Factor of")
    ):
        # Vectors starting with AU, BU, CU, FU, GU, RU, SU and WU are user defined vectors.
        # Currently not providing descriptions for these, but migth come later (see:
        # https://github.com/equinor/webviz-subsurface/issues/321)
        warnings.warn(
            (
                f"Could not find description for vector {vector_name}. Consider adding"
                " it in the GitHub repo https://github.com/equinor/webviz-subsurface-components?"
            ),
            UserWarning,
        )
    return prefix + vector + suffix


def historical_vector(
    vector: str,
    smry_meta: Optional[pd.DataFrame] = None,
    return_historical: Optional[bool] = True,
) -> Optional[str]:
    """This function is trying to make a best guess on converting between historical and
    non-historical vector names.

    `vector`: An Eclipse-format vector string
    `smry_meta`: Note: Not activate avaiting https://github.com/equinor/libecl/issues/708
                 A pandas DataFrame with vector metadata on the format returned by
                 `load_smry_meta` in `../_datainput/fmu_input.py`. Here the field is_historical is
                 used to check if a vector is a historical vector.
    `return_historical`: If return_historical is `True`, the corresponding guessed historical
                         vector name is returned if the guessed vector is thought to be a
                         historical vector, else None is returned. If `False` the corresponding
                         non-historical vector name is returned, if the input vector is thought to
                         be a historical vector, else None is returned.
    """
    smry_meta = None  # Temp deactivation waiting on https://github.com/equinor/libecl/issues/708
    parts = vector.split(":", 1)
    if return_historical:
        parts[0] += "H"
        hist_vec = ":".join(parts)
        return (
            None
            if historical_vector(hist_vec, smry_meta=smry_meta, return_historical=False)
            is None
            else hist_vec
        )

    if smry_meta is None:
        if parts[0].endswith("H") and parts[0].startswith(("F", "G", "W")):
            parts[0] = parts[0][:-1]
            return ":".join(parts)
        return None

    try:
        is_hist = smry_meta.is_historical[vector]
    except KeyError:
        is_hist = False
    return parts[0][:-1] if is_hist else None


def simulation_region_vector_breakdown(
    vector: str,
) -> Tuple[str, Optional[str], Optional[str]]:
    [vector_base_name, node, fip] = _vector_breakdown(vector)
    if fip is not None and len(fip) == 3:
        fiparray = f"FIP{fip}"
    elif fip is not None:
        fiparray = cast(str, fip)
    else:
        fiparray = ""
    return vector_base_name, fiparray, node


def simulation_region_vector_recompose(
    vector_base_name: str, fiparray: str, node: str
) -> str:
    return (
        vector_base_name
        + (
            "_" * (5 - len(vector_base_name)) + fiparray[-3:]
            if fiparray != "FIPNUM"
            else ""
        )
        + f":{node}"
    )


def _vector_breakdown(vector: str) -> Tuple[str, Optional[str], Optional[str]]:
    vector_name: str
    node: Optional[str]
    fip: Optional[str]
    if ":" in vector:
        [vector_name, node] = vector.split(":", 1)
    else:
        vector_name = vector
        node = None
    if len(vector_name) == 8:
        # Region vectors for other FIP regions than FIPNUM are written on a special form:
        # 8 signs, with the last 3 defining the region.
        # E.g.: For an array "FIPREG": ROIP is ROIP_REG, RPR is RPR__REG and ROIPL is ROIPLREG
        # Underscores _ are always used to fill
        [vector_base_name, fip] = [vector_name[0:5].rstrip("_"), vector_name[5:]]
        try:
            if SIMULATION_VECTOR_TERMINOLOGY[vector_base_name]["type"] == "region":
                vector_name = vector_base_name
            else:
                fip = None
        except KeyError:
            fip = None
    else:
        try:
            fip = (
                "NUM"
                if SIMULATION_VECTOR_TERMINOLOGY[vector_name]["type"] == "region"
                else "FIELD"
                if SIMULATION_VECTOR_TERMINOLOGY[vector_name]["type"] == "field"
                else None
            )

        except KeyError:
            fip = None
    return vector_name, node, fip

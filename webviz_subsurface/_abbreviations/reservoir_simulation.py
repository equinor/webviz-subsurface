import json
import pathlib
import warnings


_DATA_PATH = pathlib.Path(__file__).parent.absolute() / "abbreviation_data"

SIMULATION_VECTOR_TERMINOLOGY = json.loads(
    (_DATA_PATH / "reservoir_simulation_vectors.json").read_text()
)

RESERVOIR_SIMULATION_UNIT_TERMINOLOGY = json.loads(
    (_DATA_PATH / "reservoir_simulation_unit_terminology.json").read_text()
)


def simulation_unit_reformat(ecl_unit: str, unit_set: str = "METRIC"):
    """Returns the simulation unit in a different, more human friendly, format if possible,
    otherwise returns the simulation unit.
    * `ecl_unit`: Reservoir simulation vector unit to reformat
    * `unit_set`: Currently only valid option is the default "METRIC" (defined as in Eclipse E100)
    """
    return RESERVOIR_SIMULATION_UNIT_TERMINOLOGY[unit_set].get(ecl_unit, ecl_unit)


def simulation_vector_base(vector: str):
    """Returns base name of simulation vector
    E.g. WOPR for WOPR:OP_1 and ROIP for ROIP_REG:1
    """

    return vector.split(":", 1)[0].split("_", 1)[0]


def simulation_vector_description(vector: str):
    """Returns a more human friendly description of the simulation vector if possible,
     otherwise returns the input as is.
    """
    [vector_name, node] = vector.split(":", 1) if ":" in vector else [vector, None]
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
        fip = None
    if vector_name in SIMULATION_VECTOR_TERMINOLOGY:
        metadata = SIMULATION_VECTOR_TERMINOLOGY[vector_name]
        description = metadata["description"]
        if node is not None:
            description += (
                f", {metadata['type'].replace('_', ' ')} {fip} {node}"
                if fip is not None
                else f", {metadata['type'].replace('_', ' ')} {node}"
            )
    else:
        description = vector_name
        warnings.warn(
            (
                f"Could not find description for vector {vector_name}. Consider adding"
                " it in the GitHub repo https://github.com/equinor/webviz-subsurface?"
            ),
            UserWarning,
        )

    return description

import json
import pathlib
import warnings

_MODULE_PATH = pathlib.Path(__file__).parent.absolute()

VOLUME_TERMINOLOGY = json.loads((_MODULE_PATH / "volume_terminology.json").read_text())
SIMULATION_VECTOR_TERMINOLOGY = json.loads(
    (_MODULE_PATH / "reservoir_simulation_vectors.json").read_text()
)


def simulation_vector_description(vector):
    [vector_name, node] = vector.split(":", 1) if ":" in vector else [vector, None]

    if vector_name in SIMULATION_VECTOR_TERMINOLOGY:
        metadata = SIMULATION_VECTOR_TERMINOLOGY[vector_name]
        description = metadata["description"]
        if node is not None:
            description += f", {metadata['type'].replace('_', ' ')} {node}"
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

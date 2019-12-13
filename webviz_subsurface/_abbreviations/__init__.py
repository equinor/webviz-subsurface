import json
import pathlib

_MODULE_PATH = pathlib.Path(__file__).parent.absolute()

VOLUME_TERMINOLOGY = json.loads((_MODULE_PATH / "volume_terminology.json").read_text())
SIMULATION_VECTOR_TERMINOLOGY = json.loads((_MODULE_PATH / "reservoir_simulation_vectors.json").read_text())
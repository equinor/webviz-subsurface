import sys
from pathlib import Path
from typing import Dict, Optional

import yaml
from webviz_subsurface_components import VectorDefinition

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# JSON Schema for user defined vector definitions
# Used as schema input for json_schema.validate()
USER_DEFINED_VECTOR_DEFINITIONS_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["description"],
        "properties": {
            "description": {
                "type": "string",
                "maxLength": 50,
            },
            "type": {
                "type": "string",
                "maxLength": 15,
            },
        },
        "additionalProperties": False,
    },
}


class ConfigRequiredUserDefinedVectorDefinition(TypedDict):
    """Definition of required user defined vector definition data

    `Description:`
    Data type to represent required user defined data for a vector definition

    `Required keys`:
    * description: str - User defined description for vector
    """

    description: str


class ConfigUserDefinedVectorDefinition(
    ConfigRequiredUserDefinedVectorDefinition, total=False
):
    """Definition of user defined vector definition data

    Contains both required and non-required keys.

    `Description:`
    Data type to represent user defined data for a vector definition

    `Required keys`:
    * description: str - User defined description for vector

    `Non-required keys`:
    * type: str - Vector type used for VectorSelector category type
    """

    type: str


def create_user_defined_vector_descriptions_from_config(
    user_defined_vector_data_path: Optional[Path],
) -> Dict[str, VectorDefinition]:
    """Create user defined vector definitions from config

    `Input:`
    Path for yaml-file containing user defined vector definitions

    `Return:`
    Dict with vector as name, and user defined vector definition object as value.
    """
    output: Dict[str, VectorDefinition] = {}

    if user_defined_vector_data_path is None:
        return output

    vector_data_dict: Dict[str, ConfigUserDefinedVectorDefinition] = yaml.safe_load(
        user_defined_vector_data_path.read_text()
    )

    for vector, vector_data in vector_data_dict.items():
        _description = vector_data.get("description", "")
        _type = vector_data.get("type", "others")
        output[vector] = VectorDefinition(description=_description, type=_type)

    return output

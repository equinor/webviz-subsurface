import sys

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml

if sys.version_info >= (3, 8):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

# JSON Schema for user defined vector description
# Used as schema input for json_schema.validate()
USER_DEFINED_VECTOR_DESCRIPTION_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["description"],
        "properties": {
            "description": {
                "type": "string",
                "maxLength": 40,
            },
        },
        "additionalProperties": False,
    },
}

USER_DEFINED_VECTOR_DESCRIPTION_JSON_SCHEMA_2 = {
    "type": "object",
    "additionalProperties": {
        "type": "object",
        "required": ["description"],
        "properties": {
            "description": {
                "type": "string",
                "maxLength": 30,
            },
            "type": {
                "type": "string",
                "maxLength": 15,
            },
        },
        "additionalProperties": False,
    },
}


class ConfigRequiredUserDefinedVectorDescription(TypedDict):
    """Definition of required user defined vector description data

    `Description:`
    Data type to represent required user defined description for a vector

    `Required keys`:
    * description: str - User defined description for vector
    """

    description: str


class ConfigUserDefinedVectorDescription(
    ConfigRequiredUserDefinedVectorDescription, total=False
):
    """Definition of user defined vector description data

    Contains both required and non-required keys.

    `Description:`
    Data type to represent user defined description for a vector

    `Required keys`:
    * description: str - User defined description for vector

    `Non-required keys`:
    * type: str - Vector type used for VectorSelector category type
    """

    type: str


@dataclass(frozen=True)
class UserDefinedVectorDescriptionData:
    description: str
    type: Optional[str]


def create_user_defined_vector_descriptions_dict_from_config_2(
    user_defined_vector_descriptions_path: Optional[Path],
) -> Dict[str, UserDefinedVectorDescriptionData]:
    """Create user defined vector descriptions from config

    `Input:`
    Path for yaml-file containing user defined vector descriptions

    `Return:`
    Dict with vector as name, and user defined description dataclass as value.
    """
    output: Dict[str, UserDefinedVectorDescriptionData] = {}

    if user_defined_vector_descriptions_path is None:
        return output

    vector_descriptions_dict: Dict[
        str, ConfigUserDefinedVectorDescription
    ] = yaml.safe_load(user_defined_vector_descriptions_path.read_text())

    for vector, description_data in vector_descriptions_dict.items():
        _description = description_data.get("description", "")
        _type = description_data.get("type", None)
        output[vector] = UserDefinedVectorDescriptionData(
            description=_description, type=_type
        )

    return output


def create_user_defined_vector_descriptions_dict_from_config(
    user_defined_vector_descriptions_path: Optional[Path],
) -> Dict[str, str]:
    """Create user defined vector descriptions from config

    `Input:`
    Path for yaml-file containing user defined vector descriptions

    `Return:`
    Dict with vector as name, and user defined description as value.
    """
    output: Dict[str, str] = {}
    if user_defined_vector_descriptions_path is None:
        return output

    vector_description_dict: Dict[str, dict] = yaml.safe_load(
        user_defined_vector_descriptions_path.read_text()
    )

    for vector, description in vector_description_dict.items():
        _description = description["description"]
        output[vector] = _description
    return output

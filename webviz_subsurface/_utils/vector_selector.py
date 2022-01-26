from typing import Dict, Optional

from webviz_subsurface._utils.user_defined_vector_definitions import (
    UserDefinedVectorDefinition,
)


def add_vector_to_vector_selector_data(
    vector_selector_data: list,
    vector: str,
    description: Optional[str] = None,
    description_at_last_node: bool = False,
) -> None:
    nodes = vector.split(":")
    current_child_list = vector_selector_data
    for index, node in enumerate(nodes):
        found = False
        for child in current_child_list:
            if child["name"] == node:
                children = child["children"]
                current_child_list = children if children is not None else []
                found = True
                break
        if not found:
            node_data: dict = {
                "name": node,
                "children": [] if index < len(nodes) - 1 else None,
            }
            if not description_at_last_node and description and index == 0:
                node_data["description"] = description
            if description_at_last_node and description and (index == len(nodes) - 1):
                node_data["description"] = description

            current_child_list.append(node_data)

            children = current_child_list[-1]["children"]
            current_child_list = children if children is not None else []


def is_vector_name_in_vector_selector_data(
    name: str, vector_selector_data: list
) -> bool:
    nodes = name.split(":")
    current_child_list = vector_selector_data
    for node in nodes:
        found = False
        for child in current_child_list:
            if child["name"] == node:
                children = child["children"]
                current_child_list = children if children is not None else []
                found = True
                break
        if not found:
            return False
    return found


def create_custom_vector_definition_from_user_defined_vector_data(
    user_defined_vector_data: Dict[str, UserDefinedVectorDefinition]
) -> dict:
    output: dict = {}
    for elm in user_defined_vector_data:
        _type = user_defined_vector_data[elm].type
        output[elm] = {
            "description": user_defined_vector_data[elm].description,
            "type": _type if _type is not None else "others",
        }
    return output

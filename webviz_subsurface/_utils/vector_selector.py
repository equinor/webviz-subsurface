def add_vector_to_vector_selector_data(
    vector_selector_data: list,
    vector: str,
    description: str,
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
            description_text = description if index == 0 else ""
            if description_at_last_node:
                description_text = description if index == len(nodes) - 1 else ""
            current_child_list.append(
                {
                    "name": node,
                    "description": description_text,
                    "children": [] if index < len(nodes) - 1 else None,
                }
            )
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

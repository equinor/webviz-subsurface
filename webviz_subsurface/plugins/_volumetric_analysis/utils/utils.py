from typing import List
import dash


def create_range_string(real_list: list) -> str:
    idx = 0
    ranges = [[real_list[0], real_list[0]]]
    for real in list(real_list):
        if ranges[idx][1] in (real, real - 1):
            ranges[idx][1] = real
        else:
            ranges.append([real, real])
            idx += 1

    return ", ".join(
        map(lambda p: f"{p[0]}-{p[1]}" if p[0] != p[1] else str(p[0]), ranges)
    )


def update_relevant_components(id_list: list, update_info: List[dict]) -> list:
    output_id_list = [dash.no_update] * len(id_list)
    for elm in update_info:
        for idx, x in enumerate(id_list):
            if all(x[key] == value for key, value in elm["conditions"].items()):
                output_id_list[idx] = elm["new_value"]
                break
    return output_id_list


def move_to_end_of_list(element: str, list_of_elements: list) -> list:
    return [x for x in list_of_elements if x != element] + [element]

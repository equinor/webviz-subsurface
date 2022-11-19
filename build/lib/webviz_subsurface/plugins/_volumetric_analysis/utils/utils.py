import itertools
from typing import List, Tuple

import dash


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


def to_ranges(list_of_integers: List[int]) -> List[Tuple[int, int]]:
    """Return list of tuples with ranges from list of integers"""
    ranges = []
    for _, group in itertools.groupby(
        enumerate(sorted(list_of_integers)), lambda t: t[1] - t[0]
    ):
        int_range = list(group)
        ranges.append((int_range[0][1], int_range[-1][1]))
    return ranges

from typing import List, Optional


def printable_int_list(integer_list: Optional[List[int]]) -> str:
    """Creates a string out of a list of integers.
    The string gives a range x-y if all the integers between and
    including x and y are in the list, otherwise separated by commas.
    Example: the list [0, 1, 2, 4, 5, 8, 10] becomes '0-2, 4-5, 8, 10'
    If the input is `None` or the list is empty, the string 'None' is returned.
    """
    if not integer_list:
        return "None"

    sorted_list = sorted(integer_list)
    prev_number = sorted_list[0]
    string = str(prev_number)

    for next_number in sorted_list[1:]:
        if next_number > prev_number + 1:
            string += (
                f"{prev_number}" if string.endswith("-") else ""
            ) + f", {next_number}"
        elif not string.endswith("-"):
            string += "-"
        prev_number = next_number

    if not string.endswith(f", {prev_number}") and string != str(prev_number):
        string += str(prev_number)
    return string

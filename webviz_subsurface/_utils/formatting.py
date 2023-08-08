from typing import List, Optional, Union


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


# function copied from fmu.ensemble to get identical result when
# extracting ensemble parameters as a DataFrame
def parse_number_from_string(value: str) -> Union[int, float, str]:
    """Try to parse the string first as an integer, then as float,
    if both fails, return the original string.

    Caveats: Know your Python numbers:
    https://stackoverflow.com/questions/379906/how-do-i-parse-a-string-to-a-float-or-int-in-python

    Beware, this is a minefield.

    Args:
        value (str)

    Returns:
        int, float or string
    """
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        # int(afloat) fails on some, e.g. NaN
        try:
            if int(value) == value:
                return int(value)
            return value
        except ValueError:
            return value  # return float
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value

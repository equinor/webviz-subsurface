from typing import Tuple


def find_intermediate_color_rgba(
    lowcolor_rgbastr: str, highcolor_rgbastr: str, intermed: float
) -> str:
    """
    Returns the color at a given distance between two colors
    This function takes two RGBA colors along with a value 0 < intermed < 1 and
    returns an RGBA color that is interpolated between the two input colors.
    The RGBA colors are assumed to be JavaScript color strings in the
    format 'rgba(r, g, b, a)' where r,g and b are intenisties between 0 and 255
    and a is opacity in the range 0.0 to 1.0
    """

    # convert to tuple color
    lowcolor = _unlabel_rgba(lowcolor_rgbastr)
    highcolor = _unlabel_rgba(highcolor_rgbastr)

    diff_0 = float(highcolor[0] - lowcolor[0])
    diff_1 = float(highcolor[1] - lowcolor[1])
    diff_2 = float(highcolor[2] - lowcolor[2])
    diff_3 = float(highcolor[3] - lowcolor[3])

    inter_med_tuple = (
        lowcolor[0] + intermed * diff_0,
        lowcolor[1] + intermed * diff_1,
        lowcolor[2] + intermed * diff_2,
        lowcolor[3] + intermed * diff_3,
    )

    # back to an rgba string, e.g. rgba(30, 20, 10)
    inter_med_rgba = _label_rgba(inter_med_tuple)
    return inter_med_rgba


def _label_rgba(colors: Tuple[float, float, float, float]) -> str:
    """
    Takes tuple (a, b, c, d) and returns an rgba color 'rgba(a, b, c, d)'
    """
    return f"rgba({colors[0]}, {colors[1]}, {colors[2]}, {colors[3]})"


def _unlabel_rgba(colors: str) -> Tuple[float, ...]:
    """
    Takes rgba color(s) 'rgba(a, b, c, d)' and returns tuple(s) (a, b, c, d)
    This function takes either an 'rgba(a, b, c, d)' color or a list of
    such colors and returns the color tuples in tuple(s) (a, b, c, d)
    """
    str_vals = ""
    for index, _col in enumerate(colors):
        try:
            float(colors[index])
            str_vals = str_vals + colors[index]
        except ValueError:
            if colors[index] == "," or colors[index] == ".":
                str_vals = str_vals + colors[index]

    str_vals = str_vals + ","
    numbers = []
    str_num = ""
    for char in str_vals:
        if char != ",":
            str_num = str_num + char
        else:
            numbers.append(float(str_num))
            str_num = ""
    return tuple(numbers)

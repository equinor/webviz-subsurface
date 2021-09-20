from typing import Tuple


def hex_to_rgb(hex_string: str, opacity: float = 1) -> str:
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"


def rgb_to_hex(color):
    """Converts a rgb color to hex"""
    color = color.strip("rgb()")
    color = color.split(",")
    return "#" + "".join(f"{int(i):02x}" for i in color)


def find_intermediate_color(
    lowcolor: str, highcolor: str, intermed: float, colortype: str = "tuple"
) -> str:
    """
    Returns the color at a given distance between two colors
    This function takes two color tuples, where each element is between 0
    and 1, along with a value 0 < intermed < 1 and returns a color that is
    intermed-percent from lowcolor to highcolor. If colortype is set to 'rgb',
    the function will automatically convert the rgb type to a tuple, find the
    intermediate color and return it as an rgb color.
    """

    if colortype == "rgba":
        # convert to tuple color, eg. (1, 0.45, 0.7)
        lowcolor = unlabel_rgba(lowcolor)
        highcolor = unlabel_rgba(highcolor)

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

    if colortype == "rgba":
        # back to an rgba string, e.g. rgba(30, 20, 10)
        inter_med_rgba = label_rgba(inter_med_tuple)
        return inter_med_rgba

    return inter_med_tuple


def label_rgba(colors: str) -> str:
    """
    Takes tuple (a, b, c, d) and returns an rgba color 'rgba(a, b, c, d)'
    """
    return f"rgba({colors[0]}, {colors[1]}, {colors[2]}, {colors[3]})"


def unlabel_rgba(colors: str) -> Tuple[float, float, float, float]:
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

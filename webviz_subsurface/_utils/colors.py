<<<<<<< HEAD
import colorsys
from typing import Tuple


def hex_to_rgb(hex_string: str) -> Tuple[float, float, float]:
    """Converts the given hex color to rgb tuple with floating point byte color values.

    Byte color channels: 0-255

    `Return:`
    RGB color on tuple format Tuple[float, float, float] with r-, g- and b-channel
    on index 0, 1 and 2, respectively. With floating point byte color value 0-255.
    """
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    return float(rgb[0]), float(rgb[1]), float(rgb[2])


def hex_to_rgba(
    hex_string: str, opacity: float = 1.0
) -> Tuple[float, float, float, float]:
    """Converts the given hex color to rgba tuple with floating point byte color values
    and alpha channel as opacity.

    Byte color channels: 0-255
    alpha: 0-1

    `Return:`
    RGBA color on tuple format Tuple[float,float,float,float] with r-, g-, b- and alpha-channel
    on index 0, 1, 2 and 3, respectively. With floating point byte color value 0-255.
    """
    rgb = hex_to_rgb(hex_string)
    alpha = max(0.0, min(1.0, opacity))
    return rgb[0], rgb[1], rgb[2], alpha


def hex_to_rgb_str(hex_string: str) -> str:
    """Converts the given hex color to rgb string

    Byte color channels: 0-255

    `Return:`
    RGB color on string format "rgb(r,g,b)" where, channels r, g and b are
    represented with byte color value 0-255.
    """
    rgb = hex_to_rgb(hex_string)
    return f"rgb({round(rgb[0])}, {round(rgb[1])}, {round(rgb[2])})"


def hex_to_rgba_str(hex_string: str, opacity: float = 1.0) -> str:
    """Converts the given hex color to rgba string

    Byte color channels: 0-255

    `Return:`
    RGB color on string format "rgba(r,g,b,alpha)" where, channels r, g and b are
    represented with byte color value 0-255.
    """
    rgba = hex_to_rgba(hex_string, opacity)
    return f"rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {rgba[3]})"


def rgb_to_str(rgb: Tuple[float, float, float]) -> str:
    """Convert rgb tuple with floating point byte color values to string

    `Input:`
    * rgb - Tuple[float,float,float] - RGB color on tuple format, r-, g- and b-channel
    is index 0, 1 and 2, respectively. Byte color values 0-255

    `Return:`
    RGB color on string format "rgb(r,g,b)" where, channels r, g and b are
    represented with byte color integer value 0-255.
    """
    return f"rgb({round(rgb[0])}, {round(rgb[1])}, {round(rgb[2])})"


def scale_rgb_lightness(
    rgb: Tuple[float, float, float],
    scale_percentage: float,
    min_lightness_percentage: float = 10.0,
    max_lightness_percentage: float = 90.0,
) -> Tuple[float, float, float]:
    """Scale lightness of rgb tuple with byte color values, in percentage

    Method utilizes HLS color space, and adjust lightness of color
    where larger percentage is lighther, and lower percentage is darker.

    `Input:`
    * rgb - Tuple[float,float,float] - RGB color on tuple format, r-, g- and b-channel
    is index 0, 1 and 2, respectively. Byte color values 0-255
    * scale_percentage: float - Color scaling in percentage
    * min_lightness_percentage: float - Minimum percent lightness, to prevent black color
    * max_lightness_percentage: float - Maximum percent lightness, to prevent white color
    """
    # Convert scale to scalar
    l_scale = scale_percentage / 100.0

    # Convert min and max lightness from percentage to scalar 0-1
    l_min = max(0.0, min_lightness_percentage / 100.0)
    l_max = min(1.0, max_lightness_percentage / 100.0)

    # Convert rgb to hls
    hls = colorsys.rgb_to_hls(
        float(rgb[0]) / 255.0, float(rgb[1]) / 255.0, float(rgb[2]) / 255.0
    )

    # Scale lightness within min and max
    l_scaled = min(l_max, max(l_min, hls[1] * l_scale))

    # Convert lightness scaled hls to rgb
    rgb = colorsys.hls_to_rgb(hls[0], l_scaled, s=hls[2])
    return 255.0 * rgb[0], 255.0 * rgb[1], 255.0 * rgb[2]
=======
from typing import Tuple


def hex_to_rgba(hex_string: str, opacity: float = 1.0) -> str:
    """Converts the given hex color to rgba"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb = [int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)]
    return f"rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {opacity})"


def rgba_to_hex(color):
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
>>>>>>> correlation bar chart implemented. some functionality generalized

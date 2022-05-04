import colorsys
from enum import Enum
from typing import Tuple


class StandardColors(Enum):
    OIL_GREEN = "#2ca02c"
    WATER_BLUE = "#1f77b4"
    GAS_RED = "#d62728"


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


def rgba_to_str(rgba: Tuple[float, float, float, float]) -> str:
    """Convert rgba tuple with floating point byte color values to string

    `Input:`
    * rgb - Tuple[float,float,float,float] - RGBA color on tuple format

    `Return:`
    RGBA color on string format "rgba(r,g,b,a)" where, channels r, g and b are
    represented with byte color integer value 0-255, and a is represented by a
    decimal number 0-1"""
    return f"rgba({round(rgba[0])}, {round(rgba[1])}, {round(rgba[2])}, {rgba[3]})"


def rgba_to_tuple(rgba: str) -> Tuple[float, float, float, float]:
    """
    Takes rgba color 'rgba(a, b, c, d)' and returns a tuple (a, b, c, d)
    """
    numbers = [float(value) for value in rgba.strip("rbga()").split(",")]
    return numbers[0], numbers[1], numbers[2], numbers[3]


def rgba_to_hex(color: str) -> str:
    """Converts a rgba color to hex"""
    color_list = color.strip("rgba()").split(",")
    return "#" + "".join(f"{int(i):02x}" for i in color_list)


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


def find_intermediate_color(lowcolor: str, highcolor: str, intermed: float) -> str:
    """
    Returns the color at a given distance between two colors
    This function takes two color tuples, where each element is between 0
    and 1, along with a value 0 < intermed < 1 and returns a color that is
    intermed-percent from lowcolor to highcolor.
    """

    # convert to tuple color, eg. (1, 0.45, 0.7)
    lowcolor_tuple = rgba_to_tuple(lowcolor)
    highcolor_tuple = rgba_to_tuple(highcolor)

    diff_0 = float(highcolor_tuple[0] - lowcolor_tuple[0])
    diff_1 = float(highcolor_tuple[1] - lowcolor_tuple[1])
    diff_2 = float(highcolor_tuple[2] - lowcolor_tuple[2])
    diff_3 = float(highcolor_tuple[3] - lowcolor_tuple[3])

    inter_med_tuple = (
        lowcolor_tuple[0] + intermed * diff_0,
        lowcolor_tuple[1] + intermed * diff_1,
        lowcolor_tuple[2] + intermed * diff_2,
        lowcolor_tuple[3] + intermed * diff_3,
    )

    # back to an rgba string, e.g. rgba(30, 20, 10)
    return rgba_to_str(inter_med_tuple)

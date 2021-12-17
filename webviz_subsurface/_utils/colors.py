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

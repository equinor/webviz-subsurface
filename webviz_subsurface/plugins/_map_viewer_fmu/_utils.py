import base64
import io
import math
from typing import List

from PIL import Image, ImageDraw


def round_to_significant(val: float, sig: int = 4) -> float:
    """Roud a number to a specified number of significant digits."""
    if val == 0:
        return 0
    return round(val, sig - int(math.floor(math.log10(abs(val)))) - 1)


def rgb_to_hex(color: List[int]) -> str:
    """Convert an RGB color to a hex string."""
    return f"#{color[1]:02x}{color[2]:02x}{color[3]:02x}"


def image_to_base64(img: Image) -> str:
    """Convert an image to a base64 string."""
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def create_colormap_image_string(
    colors: List, width: int = 100, height: int = 20
) -> str:
    """Create a colormap image and return it as a base64 string."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    for i, color in enumerate(colors):
        x_0 = int(i / len(colors) * width)
        x_1 = int((i + 1) / len(colors) * width)
        draw.rectangle([(x_0, 0), (x_1, height)], fill=rgb_to_hex(color))

    return f"data:image/png;base64,{image_to_base64(img)}"

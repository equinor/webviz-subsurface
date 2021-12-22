import io

import numpy as np
import xtgeo
from PIL import Image

# !!!!!!!
# This is basically a copy of surface_to_rgba() from _ensemble_surface_plugin._make_rgba.py
# with a slight change in signature


def surface_to_png_bytes(surface: xtgeo.RegularSurface) -> bytes:
    """Converts a xtgeo Surface to RGBA array. Used to set the image when used in a
    DeckGLMap component"""
    surface.unrotate()
    surface.fill(np.nan)
    values = surface.values
    values = np.flip(values.transpose(), axis=0)

    # If all values are masked set to zero
    if values.mask.all():
        values = np.zeros(values.shape)

    min_val = np.nanmin(surface.values)
    max_val = np.nanmax(surface.values)
    if min_val == 0.0 and max_val == 0.0:
        scale_factor = 1.0
    else:
        scale_factor = (256 * 256 * 256 - 1) / (max_val - min_val)

    z_array = (values.copy() - min_val) * scale_factor
    z_array = z_array.copy()
    shape = z_array.shape

    z_array = np.repeat(z_array, 4)  # This will flatten the array

    z_array[0::4][np.isnan(z_array[0::4])] = 0  # Red
    z_array[1::4][np.isnan(z_array[1::4])] = 0  # Green
    z_array[2::4][np.isnan(z_array[2::4])] = 0  # Blue

    z_array[0::4] = np.floor((z_array[0::4] / (256 * 256)) % 256)  # Red
    z_array[1::4] = np.floor((z_array[1::4] / 256) % 256)  # Green
    z_array[2::4] = np.floor(z_array[2::4] % 256)  # Blue
    z_array[3::4] = np.where(np.isnan(z_array[3::4]), 0, 255)  # Alpha

    # Back to 2d shape + 1 dimension for the rgba values.

    z_array = z_array.reshape((shape[0], shape[1], 4))

    image = Image.fromarray(np.uint8(z_array), "RGBA")
    byte_io = io.BytesIO()
    image.save(byte_io, format="png")
    byte_io.seek(0)

    return byte_io.read()

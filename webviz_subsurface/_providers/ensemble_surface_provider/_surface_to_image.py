import io
import logging

import numpy as np
import xtgeo
from PIL import Image

from webviz_subsurface._utils.perf_timer import PerfTimer

# !!!!!!!
# This is basically a copy of surface_to_rgba() from _ensemble_surface_plugin._make_rgba.py
# with a slight change in signature

LOGGER = logging.getLogger(__name__)


def surface_to_png_bytes(surface: xtgeo.RegularSurface) -> bytes:
    """Converts a xtgeo Surface to RGBA array. Used to set the image when used in a
    DeckGLMap component"""

    timer = PerfTimer()

    # surface.unrotate()
    LOGGER.debug(f"unrotate: {timer.lap_s():.2f}s")

    surface.fill(np.nan)
    values = surface.values
    values = np.flip(values.transpose(), axis=0)

    # If all values are masked set to zero
    if values.mask.all():
        values = np.zeros(values.shape)

    LOGGER.debug(f"fill/flip/mask: {timer.lap_s():.2f}s")

    min_val = np.nanmin(surface.values)
    max_val = np.nanmax(surface.values)
    if min_val == 0.0 and max_val == 0.0:
        scale_factor = 1.0
    else:
        scale_factor = (256 * 256 * 256 - 1) / (max_val - min_val)

    LOGGER.debug(f"minmax: {timer.lap_s():.2f}s")

    z_array = (values.copy() - min_val) * scale_factor
    z_array = z_array.copy()
    shape = z_array.shape

    LOGGER.debug(f"scale and copy: {timer.lap_s():.2f}s")

    z_array = np.repeat(z_array, 4)  # This will flatten the array

    z_array[0::4][np.isnan(z_array[0::4])] = 0  # Red
    z_array[1::4][np.isnan(z_array[1::4])] = 0  # Green
    z_array[2::4][np.isnan(z_array[2::4])] = 0  # Blue

    z_array[0::4] = np.floor((z_array[0::4] / (256 * 256)) % 256)  # Red
    z_array[1::4] = np.floor((z_array[1::4] / 256) % 256)  # Green
    z_array[2::4] = np.floor(z_array[2::4] % 256)  # Blue
    z_array[3::4] = np.where(np.isnan(z_array[3::4]), 0, 255)  # Alpha

    LOGGER.debug(f"bytestuff: {timer.lap_s():.2f}s")

    # Back to 2d shape + 1 dimension for the rgba values.

    z_array = z_array.reshape((shape[0], shape[1], 4))

    image = Image.fromarray(np.uint8(z_array), "RGBA")
    LOGGER.debug(f"create: {timer.lap_s():.2f}s")

    byte_io = io.BytesIO()
    # Huge speed benefit from reducing compression level
    image.save(byte_io, format="png", compress_level=1)
    LOGGER.debug(f"save png to bytes: {timer.lap_s():.2f}s")

    byte_io.seek(0)
    ret_bytes = byte_io.read()
    LOGGER.debug(f"read bytes: {timer.lap_s():.2f}s")

    LOGGER.debug(f"Total time: {timer.elapsed_s():.2f}s")

    return ret_bytes


# pylint: disable=too-many-locals
def surface_to_png_bytes_optimized(surface: xtgeo.RegularSurface) -> bytes:

    timer = PerfTimer()
    # Note that returned values array is a 2d masked array
    surf_values_ma: np.ma.MaskedArray = surface.values

    surf_values_ma = np.flip(surf_values_ma.transpose(), axis=0)  # type: ignore
    LOGGER.debug(f"flip/transpose: {timer.lap_s():.2f}s")

    # This will be a flat bool array with true for all valid entries
    valid_arr = np.invert(np.ma.getmaskarray(surf_values_ma).flatten())
    LOGGER.debug(f"get valid_arr: {timer.lap_s():.2f}s")

    shape = surf_values_ma.shape
    min_val = surf_values_ma.min()
    max_val = surf_values_ma.max()
    LOGGER.debug(f"minmax: {timer.lap_s():.2f}s")

    if min_val == 0.0 and max_val == 0.0:
        scale_factor = 1.0
    else:
        scale_factor = (256 * 256 * 256 - 1) / (max_val - min_val)

    # Scale the values into the wanted range
    scaled_values_ma = (surf_values_ma - min_val) * scale_factor

    # Get a NON-masked array with all undefined entries filled with 0
    scaled_values = scaled_values_ma.filled(0)

    LOGGER.debug(f"scale and fill: {timer.lap_s():.2f}s")

    val_arr = scaled_values.astype(np.uint32).ravel()
    LOGGER.debug(f"cast and flatten: {timer.lap_s():.2f}s")

    val = val_arr.view(dtype=np.uint8)
    rgba_arr = np.empty(4 * len(val_arr), dtype=np.uint8)
    rgba_arr[0::4] = val[2::4]
    rgba_arr[1::4] = val[1::4]
    rgba_arr[2::4] = val[0::4]
    rgba_arr[3::4] = np.multiply(valid_arr, 255).astype(np.uint8)

    LOGGER.debug(f"rgba combine: {timer.lap_s():.2f}s")

    # Back to 2d shape + 1 dimension for the rgba values.
    rgba_arr_reshaped = rgba_arr.reshape((shape[0], shape[1], 4))

    image = Image.fromarray(rgba_arr_reshaped, "RGBA")
    LOGGER.debug(f"create: {timer.lap_s():.2f}s")

    byte_io = io.BytesIO()
    image.save(byte_io, format="png", compress_level=1)
    LOGGER.debug(f"save png to bytes: {timer.lap_s():.2f}s")

    byte_io.seek(0)
    ret_bytes = byte_io.read()
    LOGGER.debug(f"read bytes: {timer.lap_s():.2f}s")

    LOGGER.debug(f"Total time: {timer.elapsed_s():.2f}s")

    return ret_bytes

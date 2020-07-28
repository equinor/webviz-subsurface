import numpy as np
from xtgeo import RegularSurface
from webviz_config.common_cache import CACHE
from .image_processing import array_to_png, get_colormap
import base64
from PIL import Image
import io


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def load_surface(surface_path):
    return RegularSurface(surface_path)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_arr(surface, unrotate=True, flip=True):
    if unrotate:
        surface.unrotate()
    x, y, z = surface.get_xyz_values()
    if flip:
        x = np.flip(x.transpose(), axis=0)
        y = np.flip(y.transpose(), axis=0)
        z = np.flip(z.transpose(), axis=0)
    z.filled(np.nan)
    return [x, y, z]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_fence(fence, surface):
    return surface.get_fence(fence)


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_surface_layer(
    surface,
    name="surface",
    min_val=None,
    max_val=None,
    color="viridis",
    hillshading=False,
    unit="",
):
    """Make LayeredMap surface image base layer"""
    zvalues = get_surface_arr(surface)[2]
    bounds = [[surface.xmin, surface.ymin], [surface.xmax, surface.ymax]]
    min_val = min_val if min_val is not None else np.nanmin(zvalues)
    max_val = max_val if max_val is not None else np.nanmax(zvalues)
    return {
        "name": name,
        "checked": True,
        "base_layer": True,
        "data": [
            {
                "type": "image",
                "url": array_to_png(zvalues.copy()),
                "colormap": get_colormap(color),
                "bounds": bounds,
                "allowHillshading": hillshading,
                "minvalue": f"{min_val:.2f}" if min_val is not None else None,
                "maxvalue": f"{max_val:.2f}" if max_val is not None else None,
                "unit": str(unit),
            }
        ],
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def new_make_surface_layer(
    surface,
    name="surface",
    min_val=None,
    max_val=None,
    color=[
        "#0d0887",
        "#46039f",
        "#7201a8",
        "#9c179e",
        "#bd3786",
        "#d8576b",
        "#ed7953",
        "#fb9f3a",
        "#fdca26",
        "#f0f921",
    ],
    shader_type="hillshading",
    unit="",
):
    """Make NewLayeredMap surface image base layer"""
    zvalues = get_surface_arr(surface)[2]
    bounds = [[surface.xmin, surface.ymin], [surface.xmax, surface.ymax]]
    min_val = min_val if min_val is not None else np.nanmin(zvalues)
    max_val = max_val if max_val is not None else np.nanmax(zvalues)
    image = base64.b64decode(array_to_png(zvalues.copy())[22:])
    img = Image.open(io.BytesIO(image))
    width, height = img.size
    if width * height >= 300 * 300:
        scale = 1.0
    else:
        ratio = (1000 ** 2) / (width * height)
        scale = np.sqrt(ratio).round(2)
    return {
        "name": name,
        "checked": True,
        "baseLayer": True,
        "data": [
            {
                "type": "image",
                "url": array_to_png(zvalues.copy()),
                "colorScale": {
                    "colors": color,
                    "prefixZeroAlpha": False,
                    "scaleType": "linear",
                    "cutPointMin": min_val,
                    "cutPointMax": max_val,
                },
                "bounds": bounds,
                "shader": {
                    "type": shader_type,
                    "shadows": False,
                    "shadowIterations": 2,
                    "elevationScale": 0.05,
                    "pixelScale": 1000,
                    "setBlackToAlpha": True,
                },
                "minvalue": min_val.round(2),
                "maxvalue": max_val.round(2),
                "unit": str(unit),
                "imageScale": scale,
            }
        ],
    }


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def get_surface_layers(switch, surface_name, surfaces):
    """ Creates layers in map from all surfaces with new_make_surface_layer in surface.py
    Args:
        switch: Toggle hillshading on/off
        surface_name: Name of surface
        surfaces: List containing a single surface with corresponding depth error, depth trend etc.
    Returns:
        layers: List of all surface layers
    """
    min_val = None
    max_val = None
    shader_type = "hillshading" if switch["value"] is True else None
    depth_list = [
        "Depth",
        "Depth uncertainty",
        "Depth residual",
        "Depth residual uncertainty",
        "Depth trend",
        "Depth trend uncertainty",
    ]
    layers = []
    for i, sfc in enumerate(surfaces):
        if sfc is not None:
            s_layer = new_make_surface_layer(
                sfc,
                name=depth_list[i],
                min_val=min_val,
                max_val=max_val,
                color=[
                    "#0d0887",
                    "#46039f",
                    "#7201a8",
                    "#9c179e",
                    "#bd3786",
                    "#d8576b",
                    "#ed7953",
                    "#fb9f3a",
                    "#fdca26",
                    "#f0f921",
                ],
                shader_type=shader_type,
            )
            s_layer["id"] = surface_name + " " + depth_list[i] + "-id"
            s_layer["action"] = "add"
            layers.append(s_layer)
    return layers

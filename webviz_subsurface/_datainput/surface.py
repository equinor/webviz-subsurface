import io
import base64
import numpy as np
from xtgeo import RegularSurface
from webviz_config.common_cache import CACHE
from PIL import Image

from .image_processing import array_to_png, get_colormap


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
    color=None,
    shader_type="hillshading",
    unit="",
):
    """Make NewLayeredMap surface image base layer
    Args:
        surface: an xtgeo surface object
        name: name of the surface object
        min_val: minimum value to be plotted in map
        max_val: maximum value to be plotted in map
        color: an array with colors as strings
        shader_type: determines shader in map
        unit: determines unit on the map axes
    Returns:
        A surface layer that can be plotted in NewLayeredMap
    """
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
                    "colors": [
                        "#440154",
                        "#482878",
                        "#3e4989",
                        "#31688e",
                        "#26828e",
                        "#1f9e89",
                        "#35b779",
                        "#6ece58",
                        "#b5de2b",
                        "#fde725",
                    ]
                    if color is None
                    else color,
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
def get_surface_layers(switch, surface_name, surfaces, min_val=None, max_val=None):
    """ Creates layers in map view from all surfaces
    Args:
        switch: Toggle hillshading on/off
        surface_name: Name of surface
        surfaces: List containing a single surface with corresponding depth error, depth trend etc.
        min_val: Minimum z-value of surface
        max_val: Maximum z-value of surface
    Returns:
        layers: List of all surface layers
    """
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
    for i, surface in enumerate(surfaces):
        if surface is not None:
            s_layer = new_make_surface_layer(
                surface,
                name=depth_list[i],
                min_val=min_val,
                max_val=max_val,
                color=[
                    "#440154",
                    "#482878",
                    "#3e4989",
                    "#31688e",
                    "#26828e",
                    "#1f9e89",
                    "#35b779",
                    "#6ece58",
                    "#b5de2b",
                    "#fde725",
                ],
                shader_type=shader_type,
            )
            s_layer["id"] = surface_name + " " + depth_list[i] + "-id"
            s_layer["action"] = "add"
            layers.append(s_layer)
    return layers

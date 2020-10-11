from typing import Optional
import io
import base64
from PIL import Image
import numpy as np
import xtgeo

from webviz_subsurface._datainput.image_processing import array_to_png


class SurfaceLeafletModel:
    """Class to make a wcc.LeafletMap layer from a Xtgeo RegularSurface"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        surface: xtgeo.RegularSurface,
        name: Optional[str] = None,
        clip_min: Optional[float] = None,
        clip_max: Optional[float] = None,
        unit: str = " ",
        shader_type: str = "soft-hillshading",
        shadows: bool = False,
        colors: Optional[list] = None,
        updatemode: str = "update",
    ):
        self.name = name if name is not None else surface.name
        self.surface = surface
        self.shadows = True if shader_type == "hillshading_shadows" else shadows
        self.shader_type = (
            "hillshading" if shader_type == "hillshading_shadows" else shader_type
        )
        self.updatemode = updatemode
        self.bounds = [[surface.xmin, surface.ymin], [surface.xmax, surface.ymax]]
        self.zvalues = self.filled_z(clip_min=clip_min, clip_max=clip_max)
        self.unit = unit
        self.colors = self.set_colors(colors)

    @property
    def img_url(self) -> str:
        return array_to_png(self.zvalues.copy())

    @property
    def img_scale(self) -> float:
        img = Image.open(
            io.BytesIO(base64.b64decode(array_to_png(self.zvalues.copy())[22:]))
        )
        width, height = img.size
        if width * height >= 300 * 300:
            return 1.0
        ratio = (1000 ** 2) / (width * height)
        return np.sqrt(ratio).round(2)

    @property
    def min_val(self) -> float:
        return round(np.nanmin(self.zvalues), 4)

    @property
    def max_val(self) -> float:
        return round(np.nanmax(self.zvalues), 4)

    def filled_z(
        self,
        unrotate: bool = True,
        flip: bool = True,
        clip_min: float = None,
        clip_max: float = None,
    ) -> np.ndarray:
        surface = self.surface.copy()
        if clip_min or clip_max:
            np.ma.clip(surface.values, clip_min, clip_max, out=surface.values)
        if unrotate:
            surface.unrotate()

        x, y, z = surface.get_xyz_values()
        if flip:
            x = np.flip(x.transpose(), axis=0)
            y = np.flip(y.transpose(), axis=0)
            z = np.flip(z.transpose(), axis=0)
        return z.filled(np.nan)

    @staticmethod
    def set_colors(colors: list = None) -> list:
        return (
            [
                "#fde725",
                "#b5de2b",
                "#6ece58",
                "#35b779",
                "#1f9e89",
                "#26828e",
                "#31688e",
                "#3e4989",
                "#482878",
                "#440154",
            ]
            if colors is None
            else colors
        )

    @property
    def layer(self) -> dict:
        return {
            "name": self.name,
            "checked": True,
            "id": self.name,
            "action": self.updatemode,
            "baseLayer": True,
            "data": [
                {
                    "type": "image",
                    "url": self.img_url,
                    "colorScale": {
                        "colors": self.colors,
                        "prefixZeroAlpha": False,
                        "scaleType": "linear",
                    },
                    "shader": {
                        "type": self.shader_type,
                        "shadows": self.shadows,
                        "shadowIterations": 128,
                        "elevationScale": -1.0,
                        "pixelScale": 11000,
                        "setBlackToAlpha": True,
                    },
                    "bounds": self.bounds,
                    "minvalue": self.min_val,
                    "maxvalue": self.max_val,
                    "unit": self.unit,
                    "imageScale": self.img_scale,
                }
            ],
        }

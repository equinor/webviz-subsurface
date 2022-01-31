import base64
import io
from typing import Optional

import numpy as np
import xtgeo
from PIL import Image

from webviz_subsurface._datainput.image_processing import array2d_to_png


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
        apply_shading: bool = False,
        colors: Optional[list] = None,
        updatemode: str = "update",
    ):
        self.name = name if name is not None else surface.name
        self.surface = surface
        self.apply_shading = apply_shading
        self.updatemode = updatemode
        self.bounds = [[surface.xmin, surface.ymin], [surface.xmax, surface.ymax]]
        self.zvalues = self.get_zvalues(clip_min=clip_min, clip_max=clip_max)
        self.unit = unit
        self.colors = self.set_colors(colors)

    @property
    def img_url(self) -> str:
        return array2d_to_png(self.scaled_zvalues.copy())

    @property
    def min_val(self) -> float:
        return np.nanmin(self.zvalues)

    @property
    def max_val(self) -> float:
        return np.nanmax(self.zvalues)

    @property
    def scale_factor(self) -> float:
        if self.min_val == 0.0 and self.max_val == 0.0:
            return 1.0
        return (256 * 256 * 256 - 1) / (self.max_val - self.min_val)

    @property
    def map_scale(self) -> float:
        img = Image.open(
            io.BytesIO(
                base64.b64decode(array2d_to_png(self.scaled_zvalues.copy())[22:])
            )
        )
        width, height = img.size
        if width * height >= 300 * 300:
            return 1.0
        ratio = (1000**2) / (width * height)
        return np.sqrt(ratio).round(2)

    def get_zvalues(
        self,
        unrotate: bool = True,
        flip: bool = True,
        clip_min: float = None,
        clip_max: float = None,
    ) -> np.ndarray:
        surface = self.surface.copy()
        if clip_min or clip_max:
            np.ma.clip(surface.values, clip_min, clip_max, out=surface.values)  # type: ignore
        if unrotate:
            surface.unrotate()
        surface.fill(np.nan)
        values = surface.values
        if flip:
            values = np.flip(values.transpose(), axis=0)
        # If all values are masked set to zero
        if values.mask.all():
            values = np.zeros(values.shape)
        return values

    @property
    def scaled_zvalues(self) -> np.ndarray:
        return (self.zvalues - self.min_val) * self.scale_factor

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
                        "scaleType": "linear",
                    },
                    "shader": {
                        "applyHillshading": self.apply_shading,
                    },
                    "bounds": self.bounds,
                    "minvalue": self.min_val,
                    "maxvalue": self.max_val,
                    "unit": self.unit,
                    "imageScale": self.map_scale,
                }
            ],
        }

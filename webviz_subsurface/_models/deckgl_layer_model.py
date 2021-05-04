from typing import Optional
import io
import base64

from PIL import Image
import numpy as np
import xtgeo

# from webviz_subsurface._datainput.image_processing import array2d_to_png


class DeckGlLayerModel:
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
        self._bounds = [surface.xmin, surface.ymin, surface.xmax, surface.ymax]
        self.zvalues = self.get_zvalues(clip_min=clip_min, clip_max=clip_max)
        self.unit = unit
        # self.colors = self.set_colors(colors)

    @property
    def bounds(self) -> list:
        return self._bounds

    @property
    def target(self) -> list:
        return [
            self.surface.xmin + (self.surface.ymax - self.surface.ymin) / 2,
            self.surface.ymin + (self.surface.xmax - self.surface.xmin) / 2,
            0,
        ]

    def get_zvalues(
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
        surface.fill(np.nan)
        values = surface.values
        if flip:
            values = np.flip(values.transpose(), axis=0)
        # If all values are masked set to zero
        if values.mask.all():
            values = np.zeros(values.shape)
        return values

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
    def scaled_zvalues(self) -> np.ndarray:
        return (self.zvalues - self.min_val) * self.scale_factor

    @property
    def img_url(self) -> str:
        return array2d_to_png(self.scaled_zvalues.copy())

    @property
    def hillshading_layer(self) -> dict:
        return {
            "@@type": "Hillshading2DLayer",
            "id": "hillshading-layer",
            "bounds": self.bounds,
            "opacity": 1.0,
            "valueRange": [self.min_val, self.max_val],
            "image": self.img_url,
        }

    @property
    def colormap_layer(self) -> dict:
        return (
            {
                "@@type": "ColormapLayer",
                "id": "colormap-layer",
                "bounds": self.bounds,
                "image": self.img_url,
                "colormap": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAAKCAYAAABbnoC0AAAA8UlEQVR42u2UUW4DIQxE3ziV+tNz59hxPwLGS0gO0M6TEGYG22i1sn6+7/mFuGUQiNtYgYgc+2kll7MQwdLUfLHF+byryh9x0uqsWHnQRk2VTvXftdrVzgKRY6ftiTTvPuOpRYDUtZG/aYoW797Mq1qzztVXzHe88z6sWH0/+/vi4nPM5YOXsPXk8B6OPRj5p1xKJ1592rt549H6rXj17P7SuJ5bTVoe47v0My/3ml/x0rJ+4KwfNi/x+pGza3VW3clQ6XWnvFn3QcaDwBjzb/EAMMYDwBjjAWCM8QAwxngAGGM8AIwxHgDGGA8AY8zf4RdE8p8bK5sxUgAAAABJRU5ErkJggg==",
                "valueRange": [self.min_val, self.max_val],
                "pickable": True,
            },
        )


def array2d_to_png(z_array):
    """The DeckGL map dash component takes in pictures as base64 data
    (or as a link to an existing hosted image). I.e. for containers wanting
    to create pictures on-the-fly from numpy arrays, they have to be converted
    to base64. This is an example function of how that can be done.

    This function encodes the numpy array to a RGBA png.
    The array is encoded as a heightmap, in a format similar to Mapbox TerrainRGB
    (https://docs.mapbox.com/help/troubleshooting/access-elevation-data/),
    but without the -10000 offset and the 0.1 scale.
    The undefined values are set as having alpha = 0. The height values are
    shifted to start from 0.
    """

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

    # image.save("debug_image.png")

    base64_data = base64.b64encode(byte_io.read()).decode("ascii")
    return f"data:image/png;base64,{base64_data}"

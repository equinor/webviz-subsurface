import numpy as np
from ._image_processing import get_colormap, array_to_png
from xtgeo.surface import RegularSurface


class LayeredSurface():
    '''### LayeredSurface

    Class to generate input for a LayeredMap component
    to visualize regular surfaces in a top-down perspective.
    An XTgeo regular surface is used as input and converted
    to a bitmap image with a provided color mapping.


    * `name: Name of the layer
    * `surface: XTGeo RegularSurface
    * `colormap: Matplotlib colormap to use
    '''

    def __init__(self, name, surface: RegularSurface, colormap='viridis'):
        self.name = name
        self.get_surface_array(surface)
        self.colormap = get_colormap(colormap)

    def get_surface_array(self, surface):
        s = surface.copy()
        s.unrotate()
        xi, yi, zi = s.get_xyz_values()
        xi = np.flip(xi.transpose(), axis=0)
        yi = np.flip(yi.transpose(), axis=0)
        zi = np.flip(zi.transpose(), axis=0)
        self.arr = [xi, yi, zi]
        self.min = s.values.min()
        self.max = s.values.max()

    @property
    def bounds(self):
        return [[np.min(self.arr[0]), np.min(self.arr[1])],
                [np.max(self.arr[0]), np.max(self.arr[1])]]

    @property
    def center(self):
        return [np.mean(self.arr[0]), np.mean(self.arr[1])]

    @property
    def z_arr(self):
        return self.arr[2].filled(np.nan)

    @property
    def as_png(self):
        return array_to_png(self.z_arr)

    @property
    def layer(self):
        return {'name': self.name,
                'checked': True,
                'base_layer': True,
                'data': [{'type': 'image',
                          'url': self.as_png,
                          'colormap': self.colormap,
                          'bounds': self.bounds,
                          'minvalue': f'{self.min:.2f}',
                          'maxvalue': f'{self.max:.2f}',
                          'unit': 'm'
                          }]
                }

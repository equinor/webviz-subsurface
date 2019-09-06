import numpy as np
from ._image_processing import get_colormap, array_to_png


class LeafletSurface():

    def __init__(self, name, surface):
        self.name = name
        self.surface = surface
        self.get_surface_array()
        self.colormap = self.set_colormap('viridis')

    def get_surface_array(self):
        s = self.surface.copy()
        s.unrotate()
        xi, yi, zi = s.get_xyz_values()
        xi = np.flip(xi.transpose(), axis=0)
        yi = np.flip(yi.transpose(), axis=0)
        zi = np.flip(zi.transpose(), axis=0)
        self.arr = [xi, yi, zi]
        self.min = s.values.min()
        self.max = s.values.max()

    def set_colormap(self, colormap):
        return get_colormap(colormap)

    @property
    def bounds(self):
        return [[np.min(self.arr[0]), np.min(self.arr[1])],
                [np.max(self.arr[0]), np.max(self.arr[1])]]

    @property
    def center(self):
        return [np.mean(self.arr[0]), np.mean(self.arr[1])]

    @property
    def z_arr(self):
        # np.savetxt('test.txt', self.arr[2].filled(np.nan))
        return self.arr[2].filled(np.nan)

    @property
    def as_png(self):
        return array_to_png(self.z_arr)

    @property
    def leaflet_layer(self):
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

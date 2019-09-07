import numpy as np
from xtgeo.surface import RegularSurface


class LeafletCrossSection:
    '''### LeafletCrossSection

    Class to generate input for a Leaflet component
    to visualize subsurface data in a cross-section


    * `polyspec: 2D Numpy array with fence specification

    '''

    def __init__(self, fencespec):

        self.fencespec = fencespec
        self._surface_layers = []
        self._base_layer = None
        self._bounds = [[0, 0], [0, 0]]
        self._center = [0, 0]

    @property
    def bounds(self):
        '''Bounds of the leaflet component'''
        return self._bounds

    @property
    def center(self):
        '''Center of the leaflet component'''
        return self._center

    def set_bounds_and_center(self, data):
        '''Set bounds and center from data'''
        if isinstance(data, RegularSurface):
            x, y = self.slice_surface(data.copy())
        else:
            raise TypeError('Input must be a surface')

        self._bounds = [[np.nanmin(x), np.nanmin(y)], [
            np.nanmax(x), np.nanmax(y)]]
        self._center = [np.mean(x), np.mean(y)]

    def slice_surface(self, surface, invert_y=True):
        '''Extract line along the fencespec for the surface'''
        s = surface.copy()
        values = s.get_randomline(self.fencespec)
        x = values[:, 0]
        y = values[:, 1]
        if invert_y:
            y *= -1
        return x, y

    def add_surface_layer(
        self,
        surface: RegularSurface,
        name: str,
        tooltip: str = None,
        color: str = "blue",
        checked: bool = True,
    ):
        '''Adds a Leaflet polyline overlay layer 
        for a given XTGeo surface'''
        x, y = self.slice_surface(surface.copy())
        positions = [[a, b] for a, b in zip(x, y)]

        self._surface_layers.append(
            {
                "name": name,
                "checked": checked,
                "base_layer": False,
                "data": [
                    {
                        "type": "polyline",
                        "positions": positions,
                        "color": color,
                        "tooltip": tooltip if tooltip else name,
                    }
                ],
            }
        )

    def set_cube_base(self, cube):

        self._cube = cube

    def get_layers(self):
        '''Returns all Leaflet layers'''
        layers = self._surface_layers
        return layers

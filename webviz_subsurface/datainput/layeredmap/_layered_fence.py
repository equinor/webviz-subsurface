import numpy as np
from ._image_processing import get_colormap, array_to_png
from xtgeo import RegularSurface, Cube, Grid, GridProperty


class LayeredFence:
    '''### LayeredFence

    Class to generate input for a LayeredMap component
    to visualize subsurface data in a fence/cross-section perspective.
    Xtgeo is used to slice regular surface grids along a given
    polyline.


    * `polyspec: 2D Numpy array for fence specification.

    '''

    def __init__(self, fencespec, hinc: int = 5):

        self.fencespec = fencespec
        self.hinc = hinc
        self._surface_layers = []
        self._base_layer = None
        self._bounds = [[0, 0], [0, 0]]
        self._center = [0, 0]
        self._well_layer = None

    @property
    def bounds(self):
        '''Bounds of the component'''
        return self._bounds

    @property
    def center(self):
        '''Center of the component'''
        return self._center

    def set_bounds_and_center(self, data: [RegularSurface, Cube, tuple]):
        '''Set bounds and center from data'''
        if isinstance(data, RegularSurface):
            x, y = self.slice_surface(data.copy())
            self._bounds = [
                [np.nanmin(x), np.nanmin(y)],
                [np.nanmax(x), np.nanmax(y)]
            ]
            self._center = [np.mean(x), np.mean(y)]

        elif isinstance(data, Cube):

            cubefence = self.slice_cube(data)
            self._bounds = cubefence['bounds']
            self._center = cubefence['center']

        elif (isinstance(data[0], Grid) and
              isinstance(data[1], GridProperty)):
            grid = data[0]
            prop = data[1]
            gridfence = self.slice_grid(grid, prop)
            self._bounds = gridfence['bounds']
            self._center = gridfence['center']

        else:
            raise TypeError(
                'Input must be a Xtgeo surface, cube or grid/grid property')

    def slice_grid(self, grid, prop, invert_y=True):
        '''Extract line along the fencespec for the grid property'''

        hmin, hmax, vmin, vmax, values = grid.get_randomline(
            self.fencespec, prop, hincrement=self.hinc
        )
        if invert_y:
            ymin = -vmax
            ymax = -vmin
        else:
            ymin = vmin
            ymax = vmax
        bounds = [[hmin, ymin], [hmax, ymax]]
        center = [(hmin+hmax)/2, (ymax+ymin)/2]

        return {'values': values, 'bounds': bounds, 'center': center}

    def slice_cube(self, cube, invert_y=True):
        '''Extract line along the fencespec for the cube'''
        hmin, hmax, vmin, vmax, values = cube.get_randomline(
            self.fencespec, hincrement=self.hinc
        )
        if invert_y:
            ymin = -vmax
            ymax = -vmin
        else:
            ymin = vmin
            ymax = vmax
        bounds = [[hmin, ymin], [hmax, ymax]]
        center = [(hmin+hmax)/2, (ymax+ymin)/2]

        return {'values': values, 'bounds': bounds, 'center': center}

    def slice_surface(self, surface, invert_y=True):
        '''Extract line along the fencespec for the surface'''
        s = surface.copy()
        values = s.get_randomline(self.fencespec, hincrement=self.hinc)
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
        '''Adds a polyline overlay layer
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

    def set_cube_base_layer(self, cube: Cube, name: str,
                            colormap: str = 'RdBu'):
        '''Slices a Xtgeo seismic cube along the fencespec
        and visualizes as a bitmap image with the given colormap.

        * `name: Name of the layer
        * `cube: XTGeo Cube
        * `colormap: Matplotlib colormap to use
        '''
        cubefence = self.slice_cube(cube)
        bounds = cubefence['bounds']
        values = cubefence['values']
        url = array_to_png(values)
        colormap = get_colormap(colormap)
        self._base_layer = {'name': name,
                            'checked': True,
                            'base_layer': True,
                            'hill_shading': False,
                            'data': [{'type': 'image',
                                      'url': url,
                                      'colormap': colormap,
                                      'bounds': bounds,
                                      }]
                            }

    def set_grid_prop_base_layer(self, grid: Grid, prop: GridProperty,
                                 name: str, colormap: str = 'RdBu'):
        '''Slices a Xtgeo grid property along the fencespec
        and visualizes as a bitmap image with the given colormap.

        * `name: Name of the layer
        * `grid: XTGeo Grid
        * `prop: XTGeo Grid Property
        * `colormap: Matplotlib colormap to use
        '''
        gridfence = self.slice_grid(grid, prop)
        bounds = gridfence['bounds']
        values = gridfence['values']
        url = array_to_png(values)
        colormap = get_colormap(colormap)
        self._base_layer = {'name': name,
                            'checked': True,
                            'base_layer': True,
                            'hill_shading': False,
                            'data': [{'type': 'image',
                                      'url': url,
                                      'colormap': colormap,
                                      'bounds': bounds,
                                      }]
                            }

    def set_well_layer(self, name):
        '''Adds a polyline for the well'''
        values = self.fencespec
        x = values[:, 3]
        y = values[:, 2]
        y *= -1
        positions = [[a, b] for a, b in zip(x, y)]
        data = [{'type': 'polyline',
                 'color': 'black',
                 'tooltip': name,
                 'metadata': {'type': 'well', 'name': name},
                 'positions': positions}]
        self._well_layer = {'name': name,
                            'checked': True,
                            'base_layer': False,
                            'data': data}

    @property
    def layers(self):
        '''Returns all layers'''
        layers = []
        if self._surface_layers:
            layers.extend(self._surface_layers)
        if self._base_layer:
            layers.append(self._base_layer)
        if self._well_layer:
            layers.append(self._well_layer)
        return layers

import numpy as np
from xtgeo import RegularSurface, Cube, Grid, GridProperty
from webviz_subsurface.datainput.layeredmap._layered_fence import (
    LayeredFence,
)

SURFACE = RegularSurface("tests/data/surface.gri")
CUBE = Cube("tests/data/seismic.segy")
FENCESPEC = np.loadtxt("tests/data/polyline.np.gz")
S_SLICE = np.loadtxt("tests/data/surface_slice.np.gz")
with open("tests/data/seismic_png.txt", "r") as f:
    SEISMIC_IMG = f.read()
GRID = Grid('tests/data/grid.roff')
GRIDPROP = GridProperty('tests/data/prop.roff')
with open("tests/data/gridprop_png.txt", "r") as f:
    GRIDPROP_IMG = f.read()


def test_layered_fence_init():
    fence = LayeredFence(FENCESPEC)
    assert np.array_equal(fence.fencespec, FENCESPEC)
    assert fence._surface_layers == []
    assert fence.bounds == [[0, 0], [0, 0]]
    assert fence.center == [0, 0]


def test_slice_surface():
    fence = LayeredFence(FENCESPEC)
    assert np.array_equal(fence.slice_surface(SURFACE.copy()), S_SLICE)


def test_set_surface_bounds_and_center():
    fence = LayeredFence(FENCESPEC)
    fence.set_bounds_and_center(SURFACE)
    assert fence.bounds == [
        [-40.260988980909914, -1653.468683917269],
        [4489.7725603388635, -1586.0012876253734],
    ]
    assert fence.center == [2225.2178792970494, -1618.0241894694848]


def test_set_seismic_bounds_and_center():
    fence = LayeredFence(FENCESPEC)
    fence.set_bounds_and_center(CUBE)
    assert fence.bounds == [
        [-40.260988980909914, -1845.0],
        [4489.7725603388635, -1550]
    ]
    assert fence.center == [2224.7557856789767, -1697.5]


def test_set_grid_prop_bounds_and_center():
    fence = LayeredFence(FENCESPEC)
    fence.set_bounds_and_center((GRID, GRIDPROP))
    assert fence.bounds == [
        [-40.260988980909914, -3500.000000000071],
        [4489.7725603388635, -1499.9999999999648]
    ]

    assert fence.center == [2224.7557856789767, -2500.0000000000177]


def test_add_surface_layer():
    fence = LayeredFence(FENCESPEC)
    fence.add_surface_layer(SURFACE, "test", "tada", "red", False)

    assert len(fence._surface_layers) == 1
    layer = fence._surface_layers[0]
    assert layer["name"] == "test"
    assert layer["checked"] is False
    assert isinstance(layer["data"], list)
    assert len(layer["data"]) == 1
    data = layer["data"][0]

    assert data["tooltip"] == "tada"
    assert data["color"] == "red"
    positions = [[a, b] for a, b in zip(S_SLICE[0], S_SLICE[1])]
    assert data["positions"] == positions
    assert data["type"] == "polyline"


def test_set_cube_base_layer():
    fence = LayeredFence(FENCESPEC)
    assert fence._base_layer is None
    c = CUBE.copy()
    fence.set_cube_base_layer(c, 'test')
    assert (fence._base_layer)
    layer = fence._base_layer
    assert isinstance(layer, dict)
    assert layer['name'] == 'test'
    assert layer['checked'] is True
    assert layer['base_layer'] is True
    data = layer['data'][0]
    assert data['type'] == 'image'
    assert data['url'] == SEISMIC_IMG


def test_set_grid_prop_base_layer():
    fence = LayeredFence(FENCESPEC)
    fence.set_grid_prop_base_layer(GRID, GRIDPROP, 'test')
    assert (fence._base_layer)
    layer = fence._base_layer
    assert isinstance(layer, dict)
    assert layer['name'] == 'test'
    assert layer['checked'] is True
    assert layer['base_layer'] is True
    data = layer['data'][0]
    assert data['type'] == 'image'
    assert data['url'] == GRIDPROP_IMG


def test_layers():
    fence = LayeredFence(FENCESPEC)
    assert fence.layers == []
    fence.add_surface_layer(SURFACE, 'test')
    assert len(fence.layers) == 1
    fence.set_cube_base_layer(CUBE, 'test')
    assert len(fence.layers) == 2

import numpy as np
from xtgeo import RegularSurface
from webviz_subsurface.datainput.layeredmap._layered_fence import (
    LayeredFence,
)

s = RegularSurface("tests/data/surface.gri")
fencespec = np.loadtxt("tests/data/polyline.np.gz")
s_slice = np.loadtxt("tests/data/surface_slice.np.gz")


def test_layered_fence_init():
    fence = LayeredFence(fencespec)
    assert np.array_equal(fence.fencespec, fencespec)
    assert fence._surface_layers == []
    assert fence.bounds == [[0, 0], [0, 0]]
    assert fence.center == [0, 0]


def test_slice_surface():
    fence = LayeredFence(fencespec)
    assert np.array_equal(fence.slice_surface(s.copy()), s_slice)


def test_set_bounds_and_center():
    fence = LayeredFence(fencespec)
    fence.set_bounds_and_center(s)
    assert fence.bounds == [
        [-40.260988980909914, -1653.468683917269],
        [4489.7725603388635, -1586.0012876253734],
    ]
    assert fence.center == [2225.2178792970494, -1618.0241894694848]


def test_add_surface_layer():
    fence = LayeredFence(fencespec)
    fence.add_surface_layer(s, "test", "tada", "red", False)

    assert len(fence._surface_layers) == 1
    layer = fence._surface_layers[0]
    assert layer["name"] == "test"
    assert layer["checked"] is False
    assert isinstance(layer["data"], list)
    assert len(layer["data"]) == 1
    data = layer["data"][0]

    assert data["tooltip"] == "tada"
    assert data["color"] == "red"
    positions = [[a, b] for a, b in zip(s_slice[0], s_slice[1])]
    assert data["positions"] == positions
    assert data["type"] == "polyline"

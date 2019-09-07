import numpy as np
from xtgeo import RegularSurface
from webviz_subsurface.datainput.leaflet._leaflet_cross_section import (
    LeafletCrossSection,
)

s = RegularSurface("tests/data/surface.gri")
fencespec = np.loadtxt("tests/data/polyline.np.gz")
s_slice = np.loadtxt("tests/data/surface_slice.np.gz")


def test_leafletcross_section_init():
    leaf = LeafletCrossSection(fencespec)
    assert np.array_equal(leaf.fencespec, fencespec)
    assert leaf._surface_layers == []
    assert leaf._base_layer is None
    assert leaf.bounds == [[0, 0], [0, 0]]
    assert leaf.center == [0, 0]


def test_slice_surface():
    leaf = LeafletCrossSection(fencespec)
    assert np.array_equal(leaf.slice_surface(s.copy()), s_slice)


def test_set_bounds_and_center():
    leaf = LeafletCrossSection(fencespec)
    leaf.set_bounds_and_center(s)
    assert leaf.bounds == [
        [-40.260988980909914, -1653.468683917269],
        [4489.7725603388635, -1586.0012876253734],
    ]
    assert leaf.center == [2225.2178792970494, -1618.0241894694848]


def test_add_surface_layer():
    leaf = LeafletCrossSection(fencespec)
    leaf.add_surface_layer(s, "test", "tada", "red", False)

    assert len(leaf._surface_layers) == 1
    layer = leaf._surface_layers[0]
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

import numpy as np
from xtgeo import RegularSurface
from webviz_subsurface.datainput.leaflet._leaflet_surface import LeafletSurface

SURFACE = RegularSurface("tests/data/surface.gri")
Z_ARR = np.loadtxt("tests/data/surface_zarr.np.gz")
with open("tests/data/surface_png.txt", "r") as f:
    BASE64_IMG = f.read()


def test_leafletsurface_init():
    s = SURFACE.copy()
    s.unrotate()
    xi, yi, zi = s.get_xyz_values()
    xi = np.flip(xi.transpose(), axis=0)
    yi = np.flip(yi.transpose(), axis=0)
    zi = np.flip(zi.transpose(), axis=0)
    leaf = LeafletSurface("test", s)
    assert leaf.min == s.values.min()
    assert leaf.max == s.values.max()
    assert np.array_equal(leaf.arr, [xi, yi, zi])


def test_leaflet_zarr():
    leaf = LeafletSurface("test", SURFACE)
    # assert(np.array_equal(leaf.z_arr, Z_ARR))


def test_bounds():
    leaf = LeafletSurface("test", SURFACE)
    assert leaf.bounds == [
        [456950.7443767242, 5927337.164084819],
        [466655.3381886231, 5938639.3915624125],
    ]


def test_center():
    leaf = LeafletSurface("test", SURFACE)
    assert leaf.center == [461803.04128267366, 5932988.277823616]


def test_leaflet_layer():
    leaf = LeafletSurface("test", SURFACE)
    layer = leaf.leaflet_layer
    assert layer["name"] == "test"
    assert layer["checked"] == True
    assert layer["base_layer"] == True
    assert isinstance(layer["data"], list)
    assert len(layer["data"]) == 1
    assert layer["data"][0]["type"] == "image"
    assert layer["data"][0]["minvalue"] == f"{1576.45:.2f}"
    assert layer["data"][0]["maxvalue"] == f"{1933.12:.2f}"
    assert layer["data"][0]["unit"] == "m"
    assert (
        layer["data"][0]["url"]
        == BASE64_IMG
    )

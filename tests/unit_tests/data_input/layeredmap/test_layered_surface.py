import numpy as np
from xtgeo import RegularSurface
from webviz_subsurface.datainput.layeredmap._layered_surface import (
    LayeredSurface
)

SURFACE = RegularSurface("tests/data/surface.gri")
Z_ARR = np.loadtxt("tests/data/surface_zarr.np.gz")
with open("tests/data/surface_png.txt", "r") as f:
    BASE64_IMG = f.read()


def test_layered_surface_init():
    s = SURFACE.copy()
    s.unrotate()
    xi, yi, zi = s.get_xyz_values()
    xi = np.flip(xi.transpose(), axis=0)
    yi = np.flip(yi.transpose(), axis=0)
    zi = np.flip(zi.transpose(), axis=0)
    layered_surface = LayeredSurface("test", s)
    assert layered_surface.min == s.values.min()
    assert layered_surface.max == s.values.max()
    assert np.array_equal(layered_surface.arr, [xi, yi, zi])


def test_layered_surface_zarr():
    layered_surface = LayeredSurface("test", SURFACE)
    assert(np.allclose(layered_surface.z_arr, Z_ARR, equal_nan=True))


def test_bounds():
    layered_surface = LayeredSurface("test", SURFACE)
    assert layered_surface.bounds == [
        [456950.7443767242, 5927337.164084819],
        [466655.3381886231, 5938639.3915624125],
    ]


def test_center():
    layered_surface = LayeredSurface("test", SURFACE)
    assert layered_surface.center == [461803.04128267366, 5932988.277823616]


def test_layered_surfacelet_layer():
    layered_surface = LayeredSurface("test", SURFACE)
    layers = layered_surface.layers
    assert len(layers) == 1
    layer = layers[0]
    assert layer["name"] == "test"
    assert layer["checked"] is True
    assert layer["base_layer"] is True
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

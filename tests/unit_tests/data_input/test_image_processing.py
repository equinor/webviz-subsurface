import numpy as np
from webviz_subsurface._datainput.image_processing import (
    array_to_png,
    get_colormap,
)

with open("tests/data/surface_png.txt", "r") as f:
    BASE64_SURFACE = f.read()
with open("tests/data/colormap.txt", "r") as f:
    BASE64_COLORMAP = f.read()


def test_array_to_png():
    data = np.loadtxt("tests/data/surface_zarr.np.gz")
    assert array_to_png(data) == BASE64_SURFACE


def test_colormap():
    assert get_colormap("viridis") == BASE64_COLORMAP

import numpy as np

from webviz_subsurface._datainput.image_processing import array_to_png

with open("tests/data/surface_png.txt", "r") as f:
    BASE64_SURFACE = f.read()


def test_array_to_png():
    data = np.loadtxt("tests/data/surface_zarr.np.gz")
    assert array_to_png(data) == BASE64_SURFACE

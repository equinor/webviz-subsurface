import numpy as np

from webviz_subsurface._datainput.image_processing import array_to_png

with open("tests/data/surface_png.txt", "r") as file:
    BASE64_SURFACE = file.read()


def test_array_to_png() -> None:
    data = np.loadtxt("tests/data/surface_zarr.np.gz")
    assert array_to_png(data) == BASE64_SURFACE

import numpy as np
from webviz_subsurface.datainput.leaflet._image_processing import (
    array_to_png,
    get_colormap,
)


def test_array_to_png():
    data = np.loadtxt("tests/data/surface_zarr.np.gz")
    assert (
        array_to_png(data)
        == "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAsCAAAAABTHIflAAACUUlEQVR4nI2Uy2pUQRCG/6rucxtnJpmEREHMWnwR167cuNCdG0ERMSISdSFeli7FJ1CEQFZ5Cp/BhcRoJmbOmXPtrnIhTp8xBFKrLr7+qujuooFzx6xeSrmffG38mfATAe4M+EbE0pJp/y1e+a6oWo2UTsOdWvRwXG+15rT5uPGdq+pBuzLswb9FHqnWjbdGrl5ek+tL5rZAXNV6a/13LWnJ3BZAmgPnRyzZxojcs2A+7ADVtv6pNu1MUXrtlfVKUGpm39bbqCJufTg6w3vvxHWlq5u8+l3M8qNbAb53Xec6dq4oy2Z2eFRpHSDEifPK1M27pp7+KkXvBqhEYLESO3FtWeTWmAA/EEhJV2M4rcquEOjLcAmePQaT1seCtvXzYq0pFiY+zqvKTdYvDQWmayUv2x7EbJ7PL0xGw4gS9c3xdJrfCa/SKihLCams5CdV8qOULJj7ZNxcDWySrI9jdzw9OLkZ3jOGNio2IT9BVFJTDpqFiT026JooSaN4vLExSg1zgICJuHNxmthkOMlGWRLfDmMizMa7iMDwJJE1ysHcUyLjO7VZmq6usHdi7vVGU2G818hkLsOs8GxN6LmrMKwOdjgabF65yKSmP/EkqkzJcBxla1vjTO1OgF+gCoqTJItNtnVtE2RCT5AXxGkUUYskifMGUa+sKtiysc6TZSIjT3rwM4jYGAAMC3Vve0cBFFCQikKVn/evD8CuqIhAyJG7j/8gCAQRUsMPcAoqMzMA83Sxuxc3huNRXL1b5Eu/iRCUAluGuyB6gTMgCK9x3vgDYDkpfxsK59MAAAAASUVORK5CYII="
    )


def test_colormap():
    assert (
        get_colormap("viridis")
        == "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAABCAYAAAAxWXB3AAAAuElEQVR4nI2NyxUDIQwDR6K0lJD+W1nnABgvIZ8DT7JGNnroieRAQjJYMFQ2SDBUk0mrl16odGce05de9Z2zzStLLhEuvurIZzeZOedizd7mT70f7JOe7v7XA/jBBaH4ztn3462z37l1c7/ys1f6QFNZuUZ+1+JZ3oVN79FxctLvLB/XIQuslbe3+eSv7LVyd/KmC9O13Vjf63zt7r3kW7dR/iVuvv/H8NBE1/SiIayhiCZjhDFN5gX8UYgJzVykqAAAAABJRU5ErkJggg=="
    )

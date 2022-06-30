import numpy as np
from typing import List

import scipy.ndimage
import geojson
import xtgeo


def plume_polygon(
    surfaces: List[xtgeo.RegularSurface],
    threshold: float,
    smoothing: float = 10.0,  # TODO: expose to user?
) -> geojson.FeatureCollection:
    binary = [
        (
            np.where(np.isnan(s.values) | s.values.mask, 0.0, s.values) > threshold
        ).astype(float)
        for s in surfaces
    ]
    fraction = sum(binary) / len(binary)
    fraction = scipy.ndimage.gaussian_filter(fraction, sigma=smoothing, mode="nearest")
    ref = surfaces[0]
    x = ref.xori + np.arange(0, ref.ncol) * ref.xinc
    y = ref.yori + np.arange(0, ref.nrow) * ref.yinc
    contours = _find_all_contours(x, y, fraction, [0.1, 0.5, 0.9])
    return geojson.FeatureCollection(
        features=[
            geojson.Feature(
                id=f"P{level * 100}",
                geometry=geojson.Polygon([poly]),
            )
            for level, polys in zip(*contours)
            for poly in polys
        ]
    )


def _find_all_contours(x, y, zz, levels):
    xx, yy = np.meshgrid(x, y, indexing="ij")
    res = np.mean([abs(x[1] - x[0]), abs(y[1] - y[0])])
    polys = [
        [
            _simplify(poly, res)
            for poly in _find_contours(xx, yy, zz >= level)
        ]
        for level in levels
    ]
    return levels, polys


def _find_contours(xx, yy, zz):
    # Use _contour from MPL. Under the hood, this is the same functionality pyplot is
    # using. Direct use is preferred over pyplot.contour to avoid the overhead related to
    # figure/axis creation in MPL.
    from matplotlib import _contour
    return _contour.QuadContourGenerator(
        xx, yy, zz, np.zeros_like(zz, dtype=bool), False, 0
    ).create_contour(0.5)[0]


def _simplify(poly, resolution, factor: float = 1.2):
    # TODO: expose simplification factor?
    import shapely.geometry  # TODO: not project requirement. How to handle?
    ls = shapely.geometry.LineString(poly).simplify(factor * resolution)
    return np.array(ls.coords).tolist()

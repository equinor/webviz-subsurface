import numpy as np
from typing import List

import scipy.ndimage
import geojson
import xtgeo


def plume_polygon(
    surfaces: List[xtgeo.RegularSurface],
    threshold: float,
    smoothing: float = 10.0,
    simplify_factor: float = 1.2,
) -> geojson.FeatureCollection:
    binary = [
        (
            np.where(np.isnan(s.values) | s.values.mask, 0.0, s.values) > threshold
        ).astype(float)
        for s in surfaces
    ]
    fraction = sum(binary) / len(binary)
    fraction = scipy.ndimage.gaussian_filter(fraction, sigma=smoothing, mode="nearest")
    levels = [0.1]
    if len(surfaces) > 2:
        levels.append(0.5)
    if len(surfaces) > 1:
        levels.append(0.9)
    contours = _extract_fraction_contours(fraction, surfaces[0], simplify_factor, levels)
    return geojson.FeatureCollection(
        features=[
            geojson.Feature(
                id=f"P{level * 100}",
                geometry=geojson.LineString(poly),
            )
            for level, polys in zip(*contours)
            for poly in polys
        ]
    )


def _extract_fraction_contours(
    fraction: np.ndarray,
    ref_surface: xtgeo.RegularSurface,
    simplify_factor: float,
    levels: List[float],
):
    x = ref_surface.xori + np.arange(0, ref_surface.ncol) * ref_surface.xinc
    y = ref_surface.yori + np.arange(0, ref_surface.nrow) * ref_surface.yinc
    res = np.mean([abs(x[1] - x[0]), abs(y[1] - y[0])])
    simplify_dist = simplify_factor * res
    return _find_all_contours(x, y, fraction, levels, simplify_dist)


def _find_all_contours(x, y, zz, levels, simplify_dist: float):
    xx, yy = np.meshgrid(x, y, indexing="ij")
    polys = [
        [
            _simplify(poly, simplify_dist)
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
    from matplotlib import __version__ as mpl_ver
    contour_output = _contour.QuadContourGenerator(
        xx, yy, zz, np.zeros_like(zz, dtype=bool), False, 0
    ).create_contour(0.5)
    if int(mpl_ver[0]) >= 3 and int(mpl_ver[2]) >= 5:
        contour_output = contour_output[0]
    return contour_output


def _simplify(poly, simplify_dist: float):
    import shapely.geometry  # TODO: not project requirement. How to handle?
    ls = shapely.geometry.LineString(poly).simplify(simplify_dist)
    return np.array(ls.coords).tolist()

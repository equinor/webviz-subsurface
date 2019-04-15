import os
import numpy as np
import pandas as pd
from struct import unpack
from scipy.interpolate import RegularGridInterpolator, interp1d
from webviz_config.common_cache import cache
from webviz_config.webviz_store import webvizstore
try:
    import xtgeo
except ImportError:
    pass


def xy_to_ij(s, xy):
        """
        xy : m xy coordinates (m, 2), x values in column 0 and y in 1
        """
        # subtract xyorigin
        xy0 = xy - np.array([s.xori,s.yori])

        theta = np.radians(s.rotation)
        rmat = np.array([
            [np.cos(theta), -np.sin(theta)],
            [np.sin(theta), np.cos(theta)]])
        # unrotated
        xyr = np.dot(xy0, rmat)
        # divide by increments to get ij
        ij = xyr / np.array([s.xinc, s.yinc])
        return ij

def interp(s, ij):
    iv = np.arange(s.nx)
    jv = np.arange(s.ny)
    vals = np.reshape(s.npvalues1d, [s.nx, s.ny])
    return RegularGridInterpolator(points = (iv, jv), values=vals,
                                  bounds_error=False, fill_value= np.nan, method='linear')(ij)

@cache.memoize(timeout=cache.TIMEOUT)
def load_cube(cube_path):
    return xtgeo.cube.Cube(cube_path)

@cache.memoize(timeout=cache.TIMEOUT)
def slice_seismic(surface_path, cube_path):
    surface = xtgeo.surface.RegularSurface(surface_path)
    cube = load_cube(cube_path)
    surface.slice_cube(cube)
    return surface


def slice_grid(surface_path, grid_path, grid_prop_path):
    surface = xtgeo.surface.RegularSurface(surface_path)
    grd = xtgeo.grid_from_file(grid_path)
    prop = xtgeo.gridproperty_from_file(grid_prop_path,  grid=grd)
    surface.slice_grid3d(grd, prp)
    return surface


def fill_nans(padata, pkind='nearest'):
    """
    Interpolates data to fill nan values
    Parameters:
    padata : nd array
    source data with np.NaN values
    Returns:
    nd array
    resulting data with interpolated values instead of nans
    """
    aindexes = np.arange(padata.shape[0])
    agood_indexes, = np.where(np.isfinite(padata))
    f = interp1d(
                agood_indexes, padata[agood_indexes],
                bounds_error=False,
                copy=False,
                fill_value="extrapolate",
                kind=pkind)
    return f(aindexes)

@cache.memoize(timeout=cache.TIMEOUT)
def create_coords(center_x, center_y, extent=4000, inc=25):
    x = np.arange(center_x-extent, center_x+extent, inc)
    y = np.arange(center_y-extent, center_y+extent, inc)
    coords = []
    for ycc in y:
        for xcc in np.flip(x):
            coords.append([xcc, ycc])
    return coords

@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def generate_surface(path, x, y, extent, inc) -> pd.DataFrame:
    coords = create_coords(x, y, extent, inc)
    s = xtgeo.RegularSurface(path)
    ij = xy_to_ij(s, coords)
    values = interp(s, ij)
    values_filled = fill_nans(values)
    df = pd.DataFrame(values_filled, columns=['values'])
    return df

@cache.memoize(timeout=cache.TIMEOUT)
@webvizstore
def generate_well_path(path, downsample=None) -> pd.DataFrame:
    w = xtgeo.well.Well(path)
    if downsample:
        w.downsample(downsample)
    return w.dataframe[['X_UTME', 'Y_UTMN', 'Z_TVDSS']].copy()

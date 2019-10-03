import numpy as np
from xtgeo import Surfaces
from webviz_config.common_cache import CACHE


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def unrotate_and_transpose_surface(surface):
    surface.unrotate()
    x, y, z = surface.get_xyz_values()
    x = np.flip(x.transpose(), axis=0)
    y = np.flip(y.transpose(), axis=0)
    z = np.flip(z.transpose(), axis=0)
    return [x, y, z]


def apply(surfaces, func, *args, **kwargs):
    template = surfaces[0].copy()
    slist = []
    for surf in surfaces:
        status = template.compare_topology(surf, strict=False)
        if not status:
            continue
        slist.append(np.ma.filled(surf.values, fill_value=np.nan))
    xlist = np.array(slist)
    template.values = func(xlist, *args, **kwargs)
    return template.copy()


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calculate_surface_statistics(fns):
    surfaces = Surfaces(fns).surfaces
    return {
        "template": unrotate_and_transpose_surface(surfaces[0]),
        "mean": unrotate_and_transpose_surface(apply(surfaces, np.mean, axis=0)),
        "max": unrotate_and_transpose_surface(apply(surfaces, np.max, axis=0)),
        "min": unrotate_and_transpose_surface(apply(surfaces, np.min, axis=0)),
        "stddev": unrotate_and_transpose_surface(apply(surfaces, np.std, axis=0)),
    }

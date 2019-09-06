from collections import OrderedDict
import numpy as np
from xtgeo.surface.surfaces import Surfaces as XSurfaces


class SurfaceCollection(object):
    '''An ordered collection of lists of surfaces
    E.g. a stratigraphal column with an ensemble of surfaces'''

    def __init__(self, *args):
        self._surface_collection = OrderedDict()
        if args:
            self.append(args[0])

    @property
    def surface_collection(self):
        """Get or set a surface collection"""
        return self._surface_collection

    @surface_collection.setter
    def surface_collection(self, sdict):
        if not isinstance(sdict, OrderedDict):
            raise ValueError("Input not a list")

        for elem in sdict.values():
            if not isinstance(elem, XSurfaces):
                raise ValueError(
                    "Element in object not a valid list of Surfaces")

        self._surface_collection = sdict

    def append(self, ensemble):
        """ Append an ensemble to the collection"""
        for name, ensemble in ensemble.items():
            self._surface_collection[name] = XSurfaces(ensemble)

    def apply(self, cat, func, *args, **kwargs):
        return self._surface_collection[cat].apply(func, *args, **kwargs)

    def apply_and_subtract(self, cat, cat2, func, *args, **kwargs):
        arr1 = self._surface_collection[cat].apply(func, *args, **kwargs)
        arr2 = self._surface_collection[cat2].apply(func, *args, **kwargs)
        arr1.values = np.diff([arr1.values, arr2.values], axis=0)
        return arr1

    def subtract_and_apply(self, cat, cat2, func, *args, **kwargs):
        slist = self._surface_collection[cat].surfaces
        slist2 = self._surface_collection[cat2].surfaces
        template = slist[0]
        slist_diff = []
        for s, s2 in zip(slist, slist2):
            diff = np.diff([s.values, s2.values], axis=0)
            template.values = diff.copy()
            slist_diff.append(template.copy())
        return XSurfaces(slist_diff).apply(func, *args, **kwargs)

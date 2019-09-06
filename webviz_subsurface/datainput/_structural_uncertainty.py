import os
import io
import base64
from collections import OrderedDict
from PIL import Image
from PIL import ImageFilter
from matplotlib import cm
import glob
import numpy as np
import pandas as pd
from fmu.ensemble import ScratchEnsemble
import xtgeo
from webviz_config.common_cache import cache

def array_to_png(Z, shift=True, colormap=False):
    '''The layered map dash component takes in pictures as base64 data
    (or as a link to an existing hosted image). I.e. for containers wanting
    to create pictures on-the-fly from numpy arrays, they have to be converted
    to base64. This is an example function of how that can be done.

    1) Scale the input array (Z) to the range 0-255.
    2) If shift=True and colormap=False, the 0 value in the scaled range
       is reserved for np.nan (while the actual data points utilize the
       range 1-255.

       If shift=True and colormap=True, the 0 value in the colormap range
       has alpha value equal to 0.0 (i.e. full transparency). This makes it
       possible for np.nan values in the actual map becoming transparent in
       the image.
    3) If the array is two-dimensional, the picture is stored as greyscale.
       Otherwise it is either stored as RGB or RGBA (depending on if the size
       of the third dimension is three or four, respectively).
    '''
    
    Z -= np.nanmin(Z)

    if shift:
        Z *= 254.0/np.nanmax(Z)
        Z += 1.0
    else:
        Z *= 255.0/np.nanmax(Z)

    Z[np.isnan(Z)] = 0

    if colormap:
        if Z.shape[0] != 1:
            raise ValueError('The first dimension of a '
                             'colormap array should be 1')
        if Z.shape[1] != 256:
            raise ValueError('The second dimension of a '
                             'colormap array should be 256')
        if Z.shape[2] not in [3, 4]:
            raise ValueError('The third dimension of a colormap '
                             'array should be either 3 or 4')
        if shift:
            if Z.shape[2] != 4:
                raise ValueError('Can not shift a colormap which '
                                 'is not utilizing alpha channel')
            else:
                Z[0][0][3] = 0.0  # Make first color channel transparent

    if Z.ndim == 2:
        image = Image.fromarray(np.uint8(Z), 'L')
    elif Z.ndim == 3:
        if Z.shape[2] == 3:
            image = Image.fromarray(np.uint8(Z), 'RGB')
        elif Z.shape[2] == 4:
            image = Image.fromarray(np.uint8(Z), 'RGBA')
        else:
            raise ValueError('Third dimension of array must '
                             'have length 3 (RGB) or 4 (RGBA)')
    else:
        raise ValueError('Incorrect number of dimensions in array')
    # image = image.filter(ImageFilter.SMOOTH)
    byte_io = io.BytesIO()
    image.save(byte_io, format='png')
    # image.save('out.png', format='png')
    byte_io.seek(0)

    base64_data = base64.b64encode(byte_io.read()).decode('ascii')
    
    return f'data:image/png;base64,{base64_data}'

# @cache.memoize(timeout=cache.TIMEOUT)
def get_colormap(colormap):
    return array_to_png(cm.get_cmap(colormap, 256)
                            ([np.linspace(0, 1, 256)]), colormap=True)

class LeafletSurface():

    def __init__(self, name, surface):
        self.name = name
        self.surface = surface
        self.get_surface_array()
        self.colormap = self.set_colormap('viridis')

    def get_surface_array(self):
        s = self.surface.copy()
        s.unrotate()
        xi, yi, zi = s.get_xyz_values()
        xi = np.flip(xi.transpose(), axis=0)
        yi = np.flip(yi.transpose(), axis=0)
        zi = np.flip(zi.transpose(), axis=0)
        self.arr = [xi, yi, zi]
        self.min = s.values.min()
        self.max = s.values.max()

    def set_colormap(self, colormap):
        return get_colormap(colormap)

    @property
    def bounds(self):
        return [[np.min(self.arr[0]), np.min(self.arr[1])],
                [np.max(self.arr[0]), np.max(self.arr[1])]]

    @property
    def center(self):
        return [np.mean(self.arr[0]), np.mean(self.arr[1])]

    @property
    def z_arr(self):
        return self.arr[2].filled(np.nan)

    @property
    def as_png(self):
        return array_to_png(self.z_arr)

    @property
    def leaflet_layer(self):
        return {'name': self.name,
                'checked': True,
                'base_layer': True,
                'data':[{'type': 'image',
                         'url': self.as_png,
                         'colormap': self.colormap,
                         'bounds': self.bounds,
                         'minvalue': f'{self.min:.2f}',
                         'maxvalue': f'{self.max:.2f}',
                         'unit':'m'
                        }]
                }

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
            if not isinstance(elem, xtgeo.surface.surfaces.Surfaces):
                raise ValueError("Element in object not a valid list of Surfaces")

        self._surface_collection = sdict

    def append(self, ensemble):
        """ Append an ensemble to the collection"""
        for name, ensemble in ensemble.items():
            self._surface_collection[name] = xtgeo.surface.surfaces.Surfaces(ensemble)
            
    @cache.memoize(timeout=cache.TIMEOUT)
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
        return xtgeo.surface.surfaces.Surfaces(slist_diff).apply(func, *args, **kwargs)


class StructuralUncertaintyData():

    def __init__(self, ensembles, well_folder, surface_names,
                 surface_categories, surface_folder='share/results/maps',
                 surface_suffix='.gri', separator='--', well_suffix='.w'):

        self.ensembles = [ScratchEnsemble(e[0], e[1]) for e in ensembles]
        print(ensembles)
        self.well_folder = well_folder
        self.well_suffix = well_suffix
        self.surface_suffix = surface_suffix
        self.ens_path = ens_path
        self.separator = separator
        self.well_names = self._get_well_names()
        self.surface_names = surface_names
        self.surface_categories = surface_categories
        self.surface_folder = surface_folder

    @property
    def wells(self):
        return self._wells

    def _get_well_names(self):
        well_folder = os.path.join(self.well_folder, f'*{self.well_suffix}')
        return sorted([os.path.basename(os.path.splitext(well)[0]) for well in glob.glob(well_folder)])
    
    def _get_surface_name(self, s_name, s_cat):
        
        return f'{s_name}{self.separator}{s_cat}{self.surface_suffix}'

    def _get_surface_path(self, real, iteration, s_name, s_cat):
        n = self._get_surface_name(s_name, s_cat)
        return os.path.join(self.ens_path, f'realization-{str(real)}',
                            iteration, self.surface_folder, n)

    # @cache.memoize(timeout=cache.TIMEOUT)
    def _get_xtgeo_surface(self, real, iteration, s_name, s_cat):
        path = self._get_surface_path(real, iteration, s_name, s_cat)
        # print(path)
        try:
            return xtgeo.surface.RegularSurface(path)
        except IOError:
            raise IOError

    def _load_well(self, well_name):
        return xtgeo.well.Well(
            os.path.join(
                self.well_folder, f'{well_name}{self.well_suffix}'))

    # @cache.memoize(timeout=cache.TIMEOUT)
    def _get_wfence(self, well_name, nextend=200, tvdmin=0):
        well = self._load_well(well_name)
        data = well.get_fence_polyline(sampling=20, nextend=nextend, tvdmin=tvdmin)
        df = pd.DataFrame(data)
        df.columns = df.columns.astype(str)
        return df

    # @cache.memoize(timeout=cache.TIMEOUT)
    def _get_hfence(self, well_name, surface):
        # surface = self._get_xtgeo_surface(real, iteration, s_name, s_cat)
        values = surface.get_fence(self._get_wfence(well_name).values.copy())
        x = values[:,3].compressed()
        y = values[:,2].compressed()
        return [[a, -b] for a, b in zip(x,y)]
        # return x,y
    def _get_well_layer(self, well_name):
        x = [trace[3] for trace in self._get_wfence(well_name, nextend=0).values]
        y = [trace[2] for trace in self._get_wfence(well_name, nextend=0).values]
        # Filter out elements less than tvdmin
        # https://stackoverflow.com/questions/17995302/filtering-two-lists-simultaneously
        
        y, x = zip(*((y_el, x) for y_el, x in zip(y, x) if y_el >= 0))
        data = [[a, -b] for a, b in zip(x,y)]
        # print(data)
        return {
                    'name': 'well',
                    'checked': True,
                    'base_layer': False,
                    'data': [{'type': 'polyline',
                            'positions': [data],
                            'color': 'black',
                            'tooltip': 'test'}]
                }

    # @cache.memoize(timeout=cache.TIMEOUT)
    def _get_surface_statistics(self, fns):
            surfs = xtgeo.surface.surfaces.Surfaces(fns)  # mylist is a collection of files
            stats = surfs.statistics()
            # export the mean surface
            return stats["mean"]

    # @cache.memoize(timeout=cache.TIMEOUT)
    def get_leaflet_layer(self, well_name, real, iteration, s_name, s_cat):
        layers = []
        colors=['red', 'blue', 'green', 'yellow']
        for i, z in enumerate(self.surface_names):
            print([self._get_surface_path(r, iteration, z, s_cat) for r in range(0,80)])
            fns = [self._get_surface_path(r, iteration, z, s_cat) for r in range(0,80)]
            mean = self._get_surface_statistics(fns)
            values =self._get_hfence(well_name, mean)

            layers.append({
                    'name': z,
                    'checked': True,
                    'base_layer': False,
                    'data': [{'type': 'polyline',
                            'positions': [values],
                            'color': colors[i],
                            'tooltip': 'test'}]
                })
        layers.append(self._get_well_layer(well_name))
        bounds = self.get_leaflet_bounds(values)
        center = self.get_leaflet_center(values)
        return layers, bounds, center

    def get_leaflet_bounds(self, arr):
        x = arr[0]
        y = arr[1]
        return [[np.min(y), np.min(x)],[np.max(y), np.max(x)]]

    def get_leaflet_center(self, arr):
        x = arr[0]
        y = arr[1]
        return [np.mean(y), np.mean(x)]
        

# data = StructuralUncertaintyData('/mnt/raid/scratch/3_r001_reek', '/mnt/raid/webviz/xtgeo-testdata/wells/reek/1/',
#                                  ['topupperreek', 'topmiddlereek', 'toplowerreek', 'baselowerreek'],
#                                 ['ds_extracted_horizons'])




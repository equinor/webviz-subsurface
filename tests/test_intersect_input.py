
from mock import patch
from functools import wraps


def mock_decorator(*args, **kwargs):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        return decorated_function
    return decorator

patch('webviz_config.common_cache.cache.memoize', lambda *x, **y: lambda f: f).start()
patch('webviz_config.webviz_store.webvizstore', lambda *x, **y: lambda f: f).start()
import webviz_subsurface.datainput._intersect as intersect
def test_get_wfence():
	assert intersect.get_wfence('/scratch/fmu/hakal/reek_wells/OP_1.rmswell')[0].mean() == 0

def test_surface_to_df():
    df = intersect.surface_to_df('base_hugin',
                                 '/scratch/fmu/hakal/volve/volve_example3/realization-0/iter-0',
                                 'depthsurface')
    for col in list(df.columns):
        assert col in ['ncol',
                       'nrow',
                       'xori',
                       'yori',
                       'xinc',
                       'yinc',
                       'rotation',
                       'values']


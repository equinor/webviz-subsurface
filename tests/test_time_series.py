import sys
sys.path.append('../')
import pandas as pd
from mock import patch
# patch out flask.app instance related decorators
patch('webviz_config.common_cache.cache.memoize',
      lambda *x, **y: lambda f: f).start()
from webviz_subsurface.datainput import load_ensemble_set, get_time_series_data, \
    get_time_series_statistics, get_time_series_fielgains
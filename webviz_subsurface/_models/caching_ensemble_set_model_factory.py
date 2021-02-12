import json
from typing import Union, Optional, Dict

import inspect
import os
import threading

from .ensemble_set_model import EnsembleSetModel


# Module globals
# Do we actually need to consider locking here or will this access always be single threaded?
_cache_lock = threading.Lock()
_ensemble_set_model_cache: Dict[str, EnsembleSetModel] = {}


def get_or_create_model(
    ensemble_paths: dict,
    time_index: Optional[Union[list, str]] = None,
    column_keys: Optional[list] = None,
) -> EnsembleSetModel:

    stack = inspect.stack()
    dbg_calling_class = stack[1][0].f_locals["self"].__class__.__name__
    dbg_calling_method = stack[1][0].f_code.co_name

    tmp_dict = {
        "ensemble_paths": ensemble_paths,
        "time_index": time_index,
        "column_keys": column_keys,
    }
    modelkey = json.dumps(tmp_dict)

    with _cache_lock:
        if modelkey in _ensemble_set_model_cache:
            # Just return existing model from cache
            print(
                f"==== get_or_create_model() pid={os.getpid()} tid={threading.get_native_id()}"
                f" -- returning cached EnsembleSetModel"
                f" -- called by: {dbg_calling_class}.{dbg_calling_method}()"
            )
            return _ensemble_set_model_cache[modelkey]

        # Nothing in cache -> create a new ensemble set model and insert in cache
        print(
            f"==== get_or_create_model() pid={os.getpid()} tid={threading.get_native_id()}"
            f" -- creating NEW EnsembleSetModel"
            f" -- called by: {dbg_calling_class}.{dbg_calling_method}()"
        )

        new_model = EnsembleSetModel(
            ensemble_paths=ensemble_paths,
            smry_time_index=time_index,
            smry_column_keys=column_keys,
        )
        _ensemble_set_model_cache[modelkey] = new_model

        return new_model

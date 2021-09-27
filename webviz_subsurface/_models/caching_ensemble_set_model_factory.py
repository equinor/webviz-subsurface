import json
import threading
from typing import Dict, Optional, Union

from .ensemble_set_model import EnsembleSetModel

# Module level globals
# Do we actually need to consider locking here or will this access always be single threaded?
_cache_lock = threading.Lock()
_ensemble_set_model_cache: Dict[str, EnsembleSetModel] = {}


def get_or_create_model(
    ensemble_paths: dict,
    time_index: Optional[Union[list, str]] = None,
    column_keys: Optional[list] = None,
) -> EnsembleSetModel:

    modelkey = json.dumps(
        {
            "ensemble_paths": ensemble_paths,
            "time_index": time_index,
            "column_keys": column_keys,
        }
    )

    with _cache_lock:
        if modelkey in _ensemble_set_model_cache:
            # Just return existing model from cache
            return _ensemble_set_model_cache[modelkey]

        # No matching model in cache -> create a new ensemble set model and insert in cache
        new_model = EnsembleSetModel(
            ensemble_paths=ensemble_paths,
            smry_time_index=time_index,
            smry_column_keys=column_keys,
        )
        _ensemble_set_model_cache[modelkey] = new_model

        return new_model

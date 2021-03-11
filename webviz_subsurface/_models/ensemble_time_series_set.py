from typing import List, Dict

from .ensemble_time_series import EnsembleTimeSeries


class EnsembleTimeSeriesSet:
    def __init__(self, ensembles_dict: Dict[str, EnsembleTimeSeries]) -> None:
        self._ensembles_dict = ensembles_dict.copy()

    def ensemble_names(self) -> List[str]:
        return list(self._ensembles_dict.keys())

    def ensemble(self, ensemble_name: str) -> EnsembleTimeSeries:
        return self._ensembles_dict[ensemble_name]

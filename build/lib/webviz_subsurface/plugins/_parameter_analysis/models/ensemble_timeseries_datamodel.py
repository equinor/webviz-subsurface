import datetime
import fnmatch
import re
from typing import List, Optional, Set

import pandas as pd

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._providers import EnsembleSummaryProvider
from webviz_subsurface._utils.simulation_timeseries import (
    set_simulation_line_shape_fallback,
)
from webviz_subsurface._utils.vector_selector import add_vector_to_vector_selector_data


class ProviderTimeSeriesDataModel:
    """Class to process and and visualize ensemble timeseries"""

    def __init__(self, provider_set: dict, column_keys: Optional[list] = None) -> None:

        self._provider_set = provider_set
        self.line_shape_fallback = set_simulation_line_shape_fallback("linear")
        all_vector_names = self._create_union_of_vector_names_from_providers(
            list(provider_set.values())
        )
        self._vector_names = (
            self.filter_vectorlist_on_column_keys(column_keys, all_vector_names)
            if column_keys is not None
            else all_vector_names
        )
        if not self._vector_names:
            raise ValueError("No vectors match the selected 'column_keys' criteria")

        self._dates = self.all_dates()

        # add vectors to vector selector
        self.vector_selector_data: list = []
        for vector in self.get_non_historical_vector_names():
            add_vector_to_vector_selector_data(self.vector_selector_data, vector)

    @property
    def vectors(self) -> List[str]:
        return self._vector_names

    @property
    def dates(self) -> List[datetime.datetime]:
        return self._dates

    def get_non_historical_vector_names(self) -> list:
        return [
            vector
            for vector in self._vector_names
            if historical_vector(vector, None, False) not in self._vector_names
        ]

    def all_dates(self) -> List[datetime.datetime]:
        """List with the union of dates among providers"""
        # TODO: Adjust when providers are updated!
        dates_union: Set[datetime.datetime] = set()
        for provider in list(self._provider_set.values()):
            _dates = set(provider.dates(None))
            dates_union.update(_dates)
        return list(sorted(dates_union))

    @staticmethod
    def _create_union_of_vector_names_from_providers(
        providers: List[EnsembleSummaryProvider],
    ) -> List[str]:
        """Create list with the union of vector names among providers"""
        vector_names = []
        for provider in providers:
            vector_names.extend(
                provider.vector_names_filtered_by_value(
                    exclude_all_values_zero=True, exclude_constant_values=True
                )
            )
        vector_names = list(sorted(set(vector_names)))
        return vector_names

    def filter_vectors(self, column_keys: str) -> list:
        """Filter vector list used for correlation"""
        column_key_list = "".join(column_keys.split()).split(",")
        return self.filter_vectorlist_on_column_keys(column_key_list, self.vectors)

    @staticmethod
    def filter_vectorlist_on_column_keys(
        column_key_list: list, vectorlist: list
    ) -> list:
        """Filter vectors using list of unix shell wildcards"""
        try:
            regex = re.compile(
                "|".join([fnmatch.translate(col) for col in column_key_list]),
                flags=re.IGNORECASE,
            )
            return [v for v in vectorlist if regex.fullmatch(v)]
        except re.error:
            return []

    def get_historical_vector_df(
        self, vector: str, ensemble: str
    ) -> Optional[pd.DataFrame]:
        hist_vecname = historical_vector(vector, smry_meta=None)

        if hist_vecname and hist_vecname in self.vectors:
            provider = self._provider_set[ensemble]
            return provider.get_vectors_df(
                [hist_vecname], None, realizations=provider.realizations()[:1]
            ).rename(columns={hist_vecname: vector})
        return None

    def get_vector_df(
        self,
        ensemble: str,
        realizations: List[int],
        vectors: List[str],
    ) -> pd.DataFrame:
        provider = self._provider_set[ensemble]
        ens_vectors = [vec for vec in vectors if vec in provider.vector_names()]
        return provider.get_vectors_df(ens_vectors, None, realizations)

    def get_last_date(self, ensemble: str) -> str:
        return max(self._provider_set[ensemble].dates(None))

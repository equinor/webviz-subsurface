from typing import Dict, ItemsView, List, Optional, Sequence, Set

import pandas as pd

from webviz_subsurface._providers import EnsembleTableProvider


class EnsembleTableProviderSet:
    """
    Class to create a set of ensemble table providers with unique names
    """

    def __init__(self, provider_dict: Dict[str, EnsembleTableProvider]) -> None:
        self._provider_dict = provider_dict.copy()
        self._names = list(self._provider_dict.keys())
        self._all_column_names = self._create_union_of_column_names_from_providers(
            list(self._provider_dict.values())
        )
        self._all_realizations = self._create_union_of_realizations_from_providers(
            list(self._provider_dict.values())
        )

    def get_aggregated_dataframe(
        self, column_names: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """Get aggregated dataframe from all providers"""
        dfs = []
        for ens, provider in self.items():
            df = provider.get_column_data(
                column_names=column_names
                if column_names is not None
                else provider.column_names()
            )
            df["ENSEMBLE"] = ens
            dfs.append(df)
        return pd.concat(dfs)

    @staticmethod
    def _create_union_of_column_names_from_providers(
        providers: List[EnsembleTableProvider],
    ) -> List[str]:
        """Create list with the union of vector names among providers"""
        column_names = []
        for provider in providers:
            column_names.extend(provider.column_names())
        column_names = list(sorted(set(column_names)))
        return column_names

    @staticmethod
    def _create_union_of_realizations_from_providers(
        providers: Sequence[EnsembleTableProvider],
    ) -> List[int]:
        """Create list with the union of realizations among providers"""
        realizations: Set[int] = set()
        for provider in providers:
            realizations.update(provider.realizations())
        output = list(sorted(realizations))
        return output

    def items(self) -> ItemsView[str, EnsembleTableProvider]:
        return self._provider_dict.items()

    def provider_names(self) -> List[str]:
        return self._names

    def provider(self, name: str) -> EnsembleTableProvider:
        if name not in self._provider_dict.keys():
            raise ValueError(f'Provider with name "{name}" not present in set!')
        return self._provider_dict[name]

    def all_providers(self) -> List[EnsembleTableProvider]:
        return list(self._provider_dict.values())

    def all_realizations(self) -> List[int]:
        """List with the union of realizations among providers"""
        return self._all_realizations

    def all_column_names(self) -> List[str]:
        """List with the union of vector names among providers"""
        return self._all_column_names

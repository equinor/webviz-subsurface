from typing import Any, Dict, List, Optional

from webviz_config._theme_class import WebvizConfigTheme
from webviz_subsurface._providers import EnsembleSummaryProvider
from webviz_subsurface._utils.unique_theming import unique_colors

from .types import DeltaEnsemble, DeltaEnsembleNamePair, delta_ensemble_name

from ..._abbreviations.reservoir_simulation import (
    simulation_vector_description,
    simulation_unit_reformat,
)

# TODO: Check if one single model for graph and settings is good enough?
# TODO: See if higher level abstraction can be given -  set-functions for attributes and
#  one single getter-function for graph figure?
# NOTE:
# - Should handle data - e.g. provider, delta ensemble, statistics etc. Create data,
# do not handle any plotting/traces
class DataModel:
    __ensemble_providers: Dict[str, EnsembleSummaryProvider]
    __delta_ensemble_providers: Dict[str, DeltaEnsemble]
    __theme: WebvizConfigTheme

    def __init__(
        self,
        ensemble_providers: Dict[str, EnsembleSummaryProvider],
        delta_ensembles: List[DeltaEnsembleNamePair],
        theme: WebvizConfigTheme,
    ) -> None:
        self.__ensemble_providers = ensemble_providers
        self.__delta_ensemble_providers = self.__create_delta_ensemble_providers(
            delta_ensembles
        )
        self.__theme = theme

    def __create_delta_ensemble_providers(
        self, delta_ensembles: List[DeltaEnsembleNamePair]
    ) -> Dict[str, DeltaEnsemble]:
        delta_ensemble_providers: Dict[str, DeltaEnsemble] = {}
        for delta_ensemble in delta_ensembles:
            ensemble_a = delta_ensemble["ensemble_a"]
            ensemble_b = delta_ensemble["ensemble_b"]
            ensemble_name = delta_ensemble_name(delta_ensemble)
            if (
                ensemble_a in self.__ensemble_providers
                and ensemble_b in self.__ensemble_providers
            ):
                delta_ensemble_providers[ensemble_name] = DeltaEnsemble(
                    self.__ensemble_providers[ensemble_a],
                    self.__ensemble_providers[ensemble_b],
                )
            else:
                raise ValueError(
                    f"Request delta ensemble with ensemble {ensemble_a}"
                    f" and ensemble {ensemble_b}. Ensemble {ensemble_a} exists: "
                    f"{ensemble_a in self.__ensemble_providers}, ensemble {ensemble_b} exists: "
                    f"{ensemble_b in self.__ensemble_providers}."
                )
        return delta_ensemble_providers

    def get_selected_ensemble_providers(
        self, selected_ensembles: List[str]
    ) -> Dict[str, EnsembleSummaryProvider]:
        # Ensemble providers
        selected_providers = {
            name: provider
            for name, provider in self.__ensemble_providers.items()
            if name in selected_ensembles
        }

        # Delta ensemble providers - not overwriting existing providers
        for name, provider in self.__delta_ensemble_providers.items():
            if name in selected_ensembles and name not in selected_providers:
                selected_providers.update({name: provider})

        return selected_providers

    def create_vector_plot_title(self, vector: str) -> str:
        # Get first provider containing vector metadata
        metadata: Optional[Dict[str, Any]] = next(
            (
                provider.vector_metadata(vector)
                for provider in self.__ensemble_providers.values()
                if vector in provider.vector_names()
                and provider.vector_metadata(vector)
            ),
            None,
        )

        if metadata is None:
            return simulation_vector_description(vector)

        unit = metadata["unit"]
        return (
            f"{simulation_vector_description(vector)}"
            f" [{simulation_unit_reformat(unit)}]"
        )

    # TODO: Verify if method should be a part of data model
    def get_unique_ensemble_colors(self) -> dict:
        ensembles = list(self.__ensemble_providers.keys())
        # for elm in self.__delta_ensembles:
        #     ensembles.append(delta_ensemble_name(elm))
        for name in self.__delta_ensemble_providers:
            ensembles.append(name)
        return unique_colors(ensembles, self.__theme)

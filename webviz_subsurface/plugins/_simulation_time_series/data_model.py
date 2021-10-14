from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from webviz_config._theme_class import WebvizConfigTheme
from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._providers import EnsembleSummaryProvider, Frequency
from webviz_subsurface._utils.unique_theming import unique_colors

from .types import (
    DeltaEnsemble,
    DeltaEnsembleNamePair,
    delta_ensemble_name,
    StatisticsOptions,
)

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
        # TODO: Raise ValueError if selected ensemble elm does not exist?

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

    # TODO: Consider if function should be a part of model, or change function interface?
    def create_statistics_df(
        self,
        ensemble: str,
        vectors: List[str],
        resampling_frequency: Optional[Frequency],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """
        Create vectors statistics dataframe for given vectors in an ensemble

        Calculate min, max, mean, p10, p90 and p50 for each rquested vector

        `Returns:`
        * Dataframe with double column level:\n
          [            vector1,                        ... vectorN
            "DATE",    mean, min, max, p10, p90, p50   ... mean, min, max, p10, p90, p50]

        `Input:`
        * vectors: List[str] - List of vector names
        """
        if (
            ensemble not in self.__ensemble_providers
            and ensemble not in self.__delta_ensemble_providers
        ):
            raise ValueError(
                f'Ensemble "{ensemble}" not among ensembles in data model!'
            )

        provider = self.get_selected_ensemble_providers([ensemble])[ensemble]

        # TODO: Verify that all vectors exist for provider - raise exception on fail
        vectors_df = provider.get_vectors_df(
            vectors, resampling_frequency, realizations
        )

        # Invert p10 and p90 due to oil industry convention.
        def p10(x: List[float]) -> List[float]:
            return np.nanpercentile(x, q=90)

        def p90(x: List[float]) -> List[float]:
            return np.nanpercentile(x, q=10)

        def p50(x: List[float]) -> List[float]:
            return np.nanpercentile(x, q=50)

        # Calculate statistics, ignoring NaNs
        # statistics_df: pd.DataFrame = (
        #     vectors_df[["DATE"] + vectors]
        #     .groupby(["DATE"])
        #     .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90, p50])
        #     .reset_index(level=["DATE"], col_level=1)
        # )
        statistics_df: pd.DataFrame = (
            vectors_df[["DATE"] + vectors]
            .groupby(["DATE"])
            .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90, p50])
            .reset_index(level=["DATE"], col_level=0)
        )

        # Rename nanmin, nanmax and nanmean to min, max and mean.
        col_stat_label_map = {
            "nanmin": StatisticsOptions.MIN,
            "nanmax": StatisticsOptions.MAX,
            "nanmean": StatisticsOptions.MEAN,
            "p10": StatisticsOptions.P10,
            "p90": StatisticsOptions.P90,
            "p50": StatisticsOptions.P50,
        }
        statistics_df.rename(columns=col_stat_label_map, level=1, inplace=True)

        return statistics_df

    def create_history_vectors_df(
        self,
        ensemble: str,
        vectors: List[str],
        resampling_frequency: Optional[Frequency],
    ) -> pd.DataFrame:
        """Get dataframe with existing historical vector data for provided vectors.

        The returned dataframe contains columns with name of vector and corresponding historical data

        `Input:`
        * ensenble: str - Ensemble name
        * vectors: List[str] - list of vectors to get historical data for [vector1, ... , vectorN]

        `Output:`
        * dataframe with non-historical vector names in columns and their historical data in rows.
        `Columns` in dataframe: ["DATE", "REAL", vector1, ..., vectorN]

        ---------------------
        `NOTE:`
        * Raise ValueError if vector does not exist for ensemble
        * If historical data does not exist for provided vector, vector is excluded from
        the returned dataframe.
        * Column names are not the historical vector name, but the original vector name,
        i.e. `WOPTH:OP_1` data is placed in colum with name `WOPT:OP_1`
        """
        if (
            ensemble not in self.__ensemble_providers
            and ensemble not in self.__delta_ensemble_providers
        ):
            raise ValueError(
                f'Ensemble "{ensemble}" not among ensembles in data model!'
            )

        if len(vectors) <= 0:
            return pd.DataFrame()

        provider = self.get_selected_ensemble_providers([ensemble])[ensemble]
        provider_vectors = provider.vector_names()

        # Verify for provider
        for elm in vectors:
            if elm not in provider_vectors:
                raise ValueError(
                    f'Vector "{elm}" not present among vectors for ensemble provider '
                    'for ensemble "{ensemble}"'
                )

        # Dict with historical vector name as key, and non-historical vector name as value
        historical_vector_and_vector_name_dict: Dict[str, str] = {}
        for vector in vectors:
            # TODO: Create new historical_vector according to new provider metadata?
            historical_vector_name = historical_vector(vector=vector, smry_meta=None)
            if (
                historical_vector_name
                and historical_vector_name in provider.vector_names()
            ):
                historical_vector_and_vector_name_dict[historical_vector_name] = vector

        if not historical_vector_and_vector_name_dict:
            return pd.DataFrame()

        historical_vector_names = list(historical_vector_and_vector_name_dict.keys())

        # TODO: Ensure realization no 0 is good enough
        historical_vectors_df = provider.get_vectors_df(
            historical_vector_names, resampling_frequency, realizations=[0]
        )
        return historical_vectors_df.rename(
            columns=historical_vector_and_vector_name_dict
        )

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

        unit = metadata.get("unit", "")
        if unit:
            return (
                f"{simulation_vector_description(vector)}"
                f" [{simulation_unit_reformat(unit)}]"
            )
        return f"{simulation_vector_description(vector)}"

    # TODO: Verify if method should be a part of data model
    def get_unique_ensemble_colors(self) -> dict:
        ensembles = list(self.__ensemble_providers.keys())
        # for elm in self.__delta_ensembles:
        #     ensembles.append(delta_ensemble_name(elm))
        for name in self.__delta_ensemble_providers:
            ensembles.append(name)
        return unique_colors(ensembles, self.__theme)

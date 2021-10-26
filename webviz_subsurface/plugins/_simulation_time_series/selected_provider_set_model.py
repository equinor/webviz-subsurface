import sys
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from webviz_subsurface._abbreviations.reservoir_simulation import historical_vector
from webviz_subsurface._providers import EnsembleSummaryProvider
from webviz_subsurface._providers.ensemble_summary_provider.ensemble_summary_provider import (
    Frequency,
)
from webviz_subsurface.plugins._simulation_time_series.provider_set import ProviderSet

from .types import (
    DeltaEnsemble,
    DeltaEnsembleNamePair,
    create_delta_ensemble_name,
    StatisticsOptions,
)

from ..._abbreviations.reservoir_simulation import (
    simulation_vector_description,
    simulation_unit_reformat,
)

# TODO: Ensure resampling frequency is correct?
class SelectedProviderSetModel:
    def __init__(
        self,
        input_provider_set: ProviderSet,
        selected_ensembles: List[str],
        delta_ensembles: List[DeltaEnsembleNamePair],
        resampling_frequency: Optional[Frequency] = None,
    ) -> None:
        _selected_provider_dict: Dict[str, EnsembleSummaryProvider] = {
            name: input_provider_set.provider(name)
            for name in input_provider_set.names()
            if name in selected_ensembles
        }
        for delta_ensemble in delta_ensembles:
            delta_ensemble_name = create_delta_ensemble_name(delta_ensemble)
            if (
                delta_ensemble_name in selected_ensembles
                and delta_ensemble_name not in _selected_provider_dict
            ):
                _selected_provider_dict[
                    delta_ensemble_name
                ] = self._create_delta_ensemble_provider(
                    delta_ensemble, input_provider_set
                )
        self._selected_provider_set = ProviderSet(_selected_provider_dict)
        self._resampling_frequency = resampling_frequency

    @staticmethod
    def _create_delta_ensemble_provider(
        delta_ensemble: DeltaEnsembleNamePair,
        provider_set: ProviderSet,
    ) -> DeltaEnsemble:
        ensemble_a = delta_ensemble["ensemble_a"]
        ensemble_b = delta_ensemble["ensemble_b"]
        provider_set_ensembles = provider_set.names()
        if (
            ensemble_a not in provider_set_ensembles
            or ensemble_b not in provider_set_ensembles
        ):
            raise ValueError(
                f"Request delta ensemble with ensemble {ensemble_a}"
                f" and ensemble {ensemble_b}. Ensemble {ensemble_a} exists: "
                f"{ensemble_a in provider_set_ensembles}, ensemble {ensemble_b} exists: "
                f"{ensemble_b in provider_set_ensembles}."
            )
        return DeltaEnsemble(
            provider_set.provider(ensemble_a),
            provider_set.provider(ensemble_b),
        )

    def provider_set(self) -> ProviderSet:
        return self._selected_provider_set

    # TODO: Consider if function should be a part of model, or change function interface?
    def create_statistics_df(
        self,
        ensemble: str,
        vectors: List[str],
        realizations: Optional[Sequence[int]] = None,
    ) -> pd.DataFrame:
        """
        Create vectors statistics dataframe for given vectors in an ensemble

        Calculate min, max, mean, p10, p90 and p50 for each requested vector

        `Returns:`
        * Dataframe with double column level:\n
          [            vector1,                        ... vectorN
            "DATE",    mean, min, max, p10, p90, p50   ... mean, min, max, p10, p90, p50]

        `Input:`
        * vectors: List[str] - List of vector names
        """
        if ensemble not in self._selected_provider_set.names():
            raise ValueError(
                f'Ensemble "{ensemble}" not among selected ensembles in model!'
            )

        provider = self._selected_provider_set.provider(ensemble)
        resampling_frequency = (
            self._resampling_frequency if provider.supports_resampling() else None
        )

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
    ) -> pd.DataFrame:
        """Get dataframe with existing historical vector data for provided vectors.

        The returned dataframe contains columns with name of vector and corresponding historical
        data

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
        if ensemble not in self._selected_provider_set.names():
            raise ValueError(
                f'Ensemble "{ensemble}" not among selected ensembles in model!'
            )

        if len(vectors) <= 0:
            return pd.DataFrame()

        provider = self._selected_provider_set.provider(ensemble)
        provider_vectors = provider.vector_names()
        resampling_frequency = (
            self._resampling_frequency if provider.supports_resampling() else None
        )

        # Verify for provider
        for elm in vectors:
            if elm not in provider_vectors:
                raise ValueError(
                    f'Vector "{elm}" not present among vectors for ensemble provider '
                    f'"{ensemble}"'
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
        if sys.version_info >= (3, 9):
            vector_filtered = vector.removeprefix("AVG_").removeprefix("INTVL_")
        else:
            vector_filtered = (
                vector[4:]
                if vector.startswith("AVG_")
                else (vector[6:] if vector.startswith("INTVL_") else vector)
            )

        metadata = self._selected_provider_set.vector_metadata(vector_filtered)

        if metadata is None:
            return simulation_vector_description(vector)

        unit = metadata.get("unit", "")
        if unit:
            return (
                f"{simulation_vector_description(vector)}"
                f" [{simulation_unit_reformat(unit)}]"
            )
        return f"{simulation_vector_description(vector)}"

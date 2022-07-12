import datetime
from typing import Dict, List, Optional

from webviz_subsurface_components import ExpressionInfo

from webviz_subsurface._providers import Frequency

from ..types import (
    DeltaEnsemble,
    DerivedDeltaEnsembleVectorsAccessorImpl,
    DerivedEnsembleVectorsAccessorImpl,
    DerivedVectorsAccessor,
    ProviderSet,
)
from .delta_ensemble_utils import (
    create_delta_ensemble_name_dict,
    create_delta_ensemble_provider_pair,
    is_delta_ensemble_providers_in_provider_set,
)


def create_derived_vectors_accessor_dict(
    ensembles: List[str],
    vectors: List[str],
    provider_set: ProviderSet,
    expressions: List[ExpressionInfo],
    delta_ensembles: List[DeltaEnsemble],
    resampling_frequency: Optional[Frequency],
    relative_date: Optional[datetime.datetime],
) -> Dict[str, DerivedVectorsAccessor]:
    """Create dictionary with ensemble name as key and derived vectors accessor
    as key.

    Obtain iterable object with ensemble name and corresponding vector data accessor.

    Creates derived vectors accessor based on ensemble type: Single ensemble or
    Delta ensemble.

    The derived vectors are based on listed vectors and created expressions.

    `Input:`
    * ensembles: List[str] - list of ensemble names
    * vectors List[str] - list of vectors to create accessess for
    * provider_set: ProviderSet - set of EnsembleSummaryProviders to obtain vector data
    * expressions: List[ExpressionInfo] - list of expressions for calculating vectors
    * delta_ensembles: List[DeltaEnsemble] - list of created delta ensembles
    * resampling_frequency: Optional[Frequency] - Resampling frequency setting for
    EnsembleSummaryProviders

    `Return:`
    * Dict[str, DerivedVectorsAccessor] - dictionary with ensemble name as key and
    DerivedVectorsAccessor implementations based on ensemble type - single ensemble
    or delta ensemble.

    TODO: Consider as a factory?
    """
    ensemble_data_accessor_dict: Dict[str, DerivedVectorsAccessor] = {}
    delta_ensemble_name_dict = create_delta_ensemble_name_dict(delta_ensembles)
    provider_names = provider_set.names()
    for ensemble in ensembles:
        if ensemble in provider_names:
            ensemble_data_accessor_dict[ensemble] = DerivedEnsembleVectorsAccessorImpl(
                name=ensemble,
                provider=provider_set.provider(ensemble),
                vectors=vectors,
                expressions=expressions,
                resampling_frequency=resampling_frequency,
                relative_date=relative_date,
            )
        elif (
            ensemble in delta_ensemble_name_dict.keys()
            and is_delta_ensemble_providers_in_provider_set(
                delta_ensemble_name_dict[ensemble], provider_set
            )
        ):
            provider_pair = create_delta_ensemble_provider_pair(
                delta_ensemble_name_dict[ensemble], provider_set
            )
            ensemble_data_accessor_dict[
                ensemble
            ] = DerivedDeltaEnsembleVectorsAccessorImpl(
                name=ensemble,
                provider_pair=provider_pair,
                vectors=vectors,
                expressions=expressions,
                resampling_frequency=resampling_frequency,
                relative_date=relative_date,
            )

    return ensemble_data_accessor_dict

from typing import Dict, List

import pandas as pd

from webviz_subsurface.plugins._simulation_time_series.types import DeltaEnsemble

# pylint: disable = line-too-long
from webviz_subsurface.plugins._simulation_time_series.types.derived_delta_ensemble_vectors_accessor_impl import (
    DerivedDeltaEnsembleVectorsAccessorImpl,
)

# pylint: disable = line-too-long
from webviz_subsurface.plugins._simulation_time_series.types.derived_ensemble_vectors_accessor_impl import (
    DerivedEnsembleVectorsAccessorImpl,
)
from webviz_subsurface.plugins._simulation_time_series.types.derived_vectors_accessor import (
    DerivedVectorsAccessor,
)
from webviz_subsurface.plugins._simulation_time_series.types.provider_set import (
    ProviderSet,
)

# pylint: disable = line-too-long
from webviz_subsurface.plugins._simulation_time_series.utils.derived_ensemble_vectors_accessor_utils import (
    create_derived_vectors_accessor_dict,
)

from ..mocks.derived_vectors_accessor_ensemble_summary_provider_mock import (
    EnsembleSummaryProviderMock,
)


def test_create_derived_vectors_accessor_dict() -> None:
    ensembles = ["ensA", "ensB", "(ensA)-(ensB)", "(ensC)-(ensA)"]
    vectors = ["vector_1", "vector_2"]
    provider_set = ProviderSet(
        {
            "ensA": EnsembleSummaryProviderMock(pd.DataFrame()),
            "ensB": EnsembleSummaryProviderMock(pd.DataFrame()),
            "ensC": EnsembleSummaryProviderMock(pd.DataFrame()),
        }
    )
    delta_ensembles: List[DeltaEnsemble] = [
        DeltaEnsemble(ensemble_a="ensA", ensemble_b="ensB"),
        DeltaEnsemble(ensemble_a="ensC", ensemble_b="ensA"),
    ]

    created_result: Dict[
        str, DerivedVectorsAccessor
    ] = create_derived_vectors_accessor_dict(
        ensembles=ensembles,
        vectors=vectors,
        provider_set=provider_set,
        expressions=[],
        delta_ensembles=delta_ensembles,
        resampling_frequency=None,
        relative_date=None,
    )

    assert len(created_result) == len(ensembles)

    assert created_result.get("ensA", None) is not None
    assert isinstance(created_result["ensA"], DerivedEnsembleVectorsAccessorImpl)

    assert created_result.get("ensB", None) is not None
    assert isinstance(created_result["ensB"], DerivedEnsembleVectorsAccessorImpl)

    assert created_result.get("(ensA)-(ensB)", None) is not None
    assert isinstance(
        created_result["(ensA)-(ensB)"], DerivedDeltaEnsembleVectorsAccessorImpl
    )

    assert created_result.get("(ensC)-(ensA)", None) is not None
    assert isinstance(
        created_result["(ensC)-(ensA)"], DerivedDeltaEnsembleVectorsAccessorImpl
    )

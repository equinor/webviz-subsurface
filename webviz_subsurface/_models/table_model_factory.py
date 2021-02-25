from typing import List, Dict, Optional, Sequence
from pathlib import Path

import pandas as pd
from fmu.ensemble import ScratchEnsemble

from .table_model import EnsembleTableModelSet
from .table_model import EnsembleTableModel
from .table_model_implementations import EnsembleTableModel_dataFrameBacked


def create_model_set_from_aggregated_csv_file(
    aggr_csv_file: Path,
) -> EnsembleTableModelSet:
    df = pd.read_csv(aggr_csv_file)

    models_dict: Dict[str, EnsembleTableModel] = {}

    ensemble_names = df["ENSEMBLE"].unique()
    for ens_name in ensemble_names:
        ensemble_df = df[df["ENSEMBLE"] == ens_name]
        model: EnsembleTableModel = EnsembleTableModel_dataFrameBacked(ensemble_df)
        models_dict[ens_name] = model

    return EnsembleTableModelSet(models_dict)


def create_model_set_from_ensembles_layout(
    ensembles: Dict[str, Path], csv_file: str
) -> EnsembleTableModelSet:

    models_dict: Dict[str, EnsembleTableModel] = {}

    for ens_name, ens_path in ensembles.items():
        scratch_ensemble = ScratchEnsemble(ens_name, ens_path, autodiscovery=False)
        ensemble_df = scratch_ensemble.load_csv(csv_file)
        models_dict[ens_name] = EnsembleTableModel_dataFrameBacked(ensemble_df)

    return EnsembleTableModelSet(models_dict)

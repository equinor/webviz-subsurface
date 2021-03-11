from typing import List, Dict, Optional
from pathlib import Path
import time
import os
import hashlib
from enum import Enum

import pandas as pd

from fmu.ensemble import ScratchEnsemble
from .ensemble_time_series_set import EnsembleTimeSeriesSet
from .ensemble_time_series import EnsembleTimeSeries
from .ensemble_time_series_impl_inmem_dataframe import (
    EnsembleTimeSeriesImplInMemDataFrame,
)
from .ensemble_time_series_impl_naive_parquet import (
    EnsembleTimeSeriesImplNaiveParquet,
)
from .ensemble_time_series_impl_arrow import EnsembleTimeSeriesImplArrow


class BackingType(Enum):
    ARROW = 1
    ARROW_PER_REAL_SMRY_IMPORT = 2
    PARQUET = 3


# =============================================================================
class EnsembleTimeSeriesFactory:

    # -------------------------------------------------------------------------
    def __init__(self, root_storage_folder: Path, backing_type: BackingType) -> None:
        self._storage_dir = Path(root_storage_folder) / __name__
        self._backing_type: BackingType = backing_type

        print("root_storage_folder:", root_storage_folder)
        print("self._storage_dir:", self._storage_dir)
        print("self._backing_type:", self._backing_type)

        # For now, just make sure the storage folder exists
        os.makedirs(self._storage_dir, exist_ok=True)

    # -------------------------------------------------------------------------
    def create_time_series_set_from_aggregated_csv_file(
        self,
        aggr_csv_file: Path,
    ) -> EnsembleTimeSeriesSet:
        aggregated_df = pd.read_csv(aggr_csv_file)
        ensemble_names = aggregated_df["ENSEMBLE"].unique()

        timeseries_obj_dict: Dict[str, EnsembleTimeSeries] = {}

        for ens_name in ensemble_names:
            ensemble_df = aggregated_df[aggregated_df["ENSEMBLE"] == ens_name]
            ens_ts_obj = EnsembleTimeSeriesImplInMemDataFrame(ensemble_df)
            timeseries_obj_dict[ens_name] = ens_ts_obj

        return EnsembleTimeSeriesSet(timeseries_obj_dict)

    # -------------------------------------------------------------------------
    def create_time_series_set_from_per_realization_csv_files(
        self, ensembles: Dict[str, str], csv_file_rel_path: str
    ) -> EnsembleTimeSeriesSet:

        timeseries_obj_dict: Dict[str, EnsembleTimeSeries] = {}
        for ens_name, ens_path in ensembles.items():

            hashval = hashlib.md5((ens_path + csv_file_rel_path).encode()).hexdigest()
            storage_key = f"ens_csv__{hashval}"

            ens_ts_obj = self._create_instance_from_backing_store(storage_key)

            if not ens_ts_obj:
                scratch_ensemble = ScratchEnsemble(
                    ens_name, ens_path, autodiscovery=True
                )
                ensemble_df = scratch_ensemble.load_csv(csv_file_rel_path)
                del scratch_ensemble

                self._write_data_to_backing_store(storage_key, ensemble_df)
                ens_ts_obj = self._create_instance_from_backing_store(storage_key)

            if ens_ts_obj:
                timeseries_obj_dict[ens_name] = ens_ts_obj

        return EnsembleTimeSeriesSet(timeseries_obj_dict)

    # -------------------------------------------------------------------------
    def create_time_series_set_from_ensemble_smry(
        self, ensembles: Dict[str, str], time_index: str
    ) -> EnsembleTimeSeriesSet:

        storage_keys_to_load: Dict[str, str] = {}
        for ens_name, ens_path in ensembles.items():
            hashval = hashlib.md5(ens_path.encode()).hexdigest()
            storage_keys_to_load[ens_name] = f"ens_smry__{hashval}__{time_index}"

        timeseries_obj_dict: Dict[str, EnsembleTimeSeries] = {}

        # Try and create/load from backing store
        for ens_name, ens_storage_key in dict(storage_keys_to_load).items():
            ens_ts_obj = self._create_instance_from_backing_store(ens_storage_key)
            if ens_ts_obj:
                timeseries_obj_dict[ens_name] = ens_ts_obj
                del storage_keys_to_load[ens_name]

        # If there are remaining keys to load, we'll load the smry data, write the
        # data to storage and then try and load again
        if storage_keys_to_load:
            for ens_name, ens_storage_key in dict(storage_keys_to_load).items():
                ens_path = ensembles[ens_name]

                # Experiment with importing smry data per realization instead of whole
                # dataframe for entire ensemble (pyarrow only)
                if self._backing_type is BackingType.ARROW_PER_REAL_SMRY_IMPORT:
                    per_real_dfs = (
                        EnsembleTimeSeriesFactory._load_smry_dataframe_per_realization(
                            ens_path, time_index
                        )
                    )
                    EnsembleTimeSeriesImplArrow.write_backing_store_from_per_realization_dataframes(
                        self._storage_dir, ens_storage_key, per_real_dfs
                    )
                else:
                    ensemble_df = EnsembleTimeSeriesFactory._load_smry_single_dataframe_for_ensemble(
                        ens_path, time_index
                    )
                    self._write_data_to_backing_store(ens_storage_key, ensemble_df)

                ens_ts_obj = self._create_instance_from_backing_store(ens_storage_key)
                if ens_ts_obj:
                    timeseries_obj_dict[ens_name] = ens_ts_obj
                    del storage_keys_to_load[ens_name]

        return EnsembleTimeSeriesSet(timeseries_obj_dict)

    # -------------------------------------------------------------------------
    # Crude solution for creating EnsembleTimeSeries instances from backing store
    # based on the configured backing type. Good enough for testing, but needs a
    # proper solution if we want such functionality in production.
    def _create_instance_from_backing_store(
        self, storage_key: str
    ) -> Optional[EnsembleTimeSeries]:
        if (
            self._backing_type is BackingType.ARROW
            or self._backing_type is BackingType.ARROW_PER_REAL_SMRY_IMPORT
        ):
            return EnsembleTimeSeriesImplArrow.from_backing_store(
                self._storage_dir, storage_key
            )

        elif self._backing_type is BackingType.PARQUET:
            return EnsembleTimeSeriesImplNaiveParquet.from_backing_store(
                self._storage_dir, storage_key
            )

        else:
            raise NotImplementedError()

    # -------------------------------------------------------------------------
    # Crude solution for writing data to backing store according to the configured
    # backing type. Good enough for testing, but needs a proper solution if we
    # want such functionality in production.
    def _write_data_to_backing_store(
        self, storage_key: str, ensemble_df: pd.DataFrame
    ) -> None:
        if (
            self._backing_type is BackingType.ARROW
            or self._backing_type is BackingType.ARROW_PER_REAL_SMRY_IMPORT
        ):
            EnsembleTimeSeriesImplArrow.write_backing_store_from_ensemble_dataframe(
                self._storage_dir, storage_key, ensemble_df
            )

        elif self._backing_type is BackingType.PARQUET:
            EnsembleTimeSeriesImplNaiveParquet.write_backing_store_from_ensemble_dataframe(
                self._storage_dir, storage_key, ensemble_df
            )

        else:
            raise NotImplementedError()

    # -------------------------------------------------------------------------
    @staticmethod
    # @profile
    def _load_smry_single_dataframe_for_ensemble(
        ens_path: str, time_index: str
    ) -> pd.DataFrame:

        print("entering _load_smry_single_dataframe_for_ensemble() ...")
        start_tim = time.perf_counter()

        lap_tim = start_tim
        scratch_ensemble = ScratchEnsemble("tempEnsName", paths=ens_path)
        print(f"  time creating ScratchEnsemble (s): {time.perf_counter() - lap_tim}")

        lap_tim = time.perf_counter()
        ensemble_df = scratch_ensemble.load_smry(time_index=time_index)
        print(f"  time executing load_smry() (s): {time.perf_counter() - lap_tim}")

        print(
            f"total time in _load_smry_single_dataframe_for_ensemble (s): {time.perf_counter() - start_tim}"
        )

        return ensemble_df

    # -------------------------------------------------------------------------
    @staticmethod
    # @profile
    def _load_smry_dataframe_per_realization(
        ens_path: str, time_index: str
    ) -> List[pd.DataFrame]:

        print("entering _load_smry_dataframe_per_realization() ...")
        start_tim = time.perf_counter()

        lap_tim = start_tim
        scratch_ensemble = ScratchEnsemble("tempEnsName", paths=ens_path)
        print(f"  time creating ScratchEnsemble (s): {time.perf_counter() - lap_tim}")

        lap_tim = time.perf_counter()

        real_df_list = []
        for _realidx, realization in scratch_ensemble.realizations.items():
            # Note that caching seems faster even if we're at realization level, but uses more memory
            real_df = realization.load_smry(time_index=time_index, cache_eclsum=True)
            real_df_list.append(real_df)

        print(
            f"  time loading smry pr realization (s): {time.perf_counter() - lap_tim}"
        )

        print(
            f"total time in _load_smry_dataframe_per_realization() (s): {time.perf_counter() - start_tim}"
        )

        return real_df_list

# -*- coding: utf-8 -*-
import sys
import pytest
import pandas as pd
from mock import patch
sys.path.append('../')
sys.path.append('../webviz_subsurface/containers/')
with patch('webviz_config.common_cache.cache.memoize',
           lambda *x, **y: lambda f: f):
    from webviz_subsurface.datainput import \
        load_ensemble_set, \
        get_time_series_statistics, \
        get_time_series_fielgains, \
        get_time_series_data


# define recurring variables
VOVLE_ENSEMBLE_PATHS = [
    ('iter--0', '/scratch/fmu/stcr/volve/realization-*/iter-0'),
    ('iter--1', '/scratch/fmu/stcr/volve/realization-*/iter-1'),
    ('iter--2', '/scratch/fmu/stcr/volve/realization-*/iter-2'),
]
VOLVE_ENSEMBLESET_NAME = 'Volve'
VOLVE_TIME_INDEX = 'yearly'
VOLVE_COLUMN_KEYS = ['FOP*', 'FGP*']
BASE_ENSEMBLES = ['iter--0']
DELTA_ENSEMBLES = ['iter--0', 'iter--1', 'iter--2']


@pytest.mark.skipif('fmu.ensemble' not in sys.modules,
                    reason="Requires fmu.ensemble installed")
def test_load_ensemble_set():

    ensset = load_ensemble_set(
        ensemble_paths=VOVLE_ENSEMBLE_PATHS,
        ensemble_set_name=VOLVE_ENSEMBLESET_NAME
    )
    assert len(ensset) == 3
    assert len(ensset["iter--0"].get_df("STATUS")) == 125
    assert len(ensset["iter--1"].get_df("STATUS")) == 105
    assert len(ensset["iter--2"].get_df("STATUS")) == 85


@pytest.mark.skipif('fmu.ensemble' not in sys.modules,
                    reason="Requires fmu.ensemble installed")
def test_time_series_statistics():

    summary_statistics = get_time_series_statistics(
        ensemble_paths=VOVLE_ENSEMBLE_PATHS,
        time_index=VOLVE_TIME_INDEX,
        column_keys=VOLVE_COLUMN_KEYS
    )
    assert isinstance(summary_statistics, pd.DataFrame)
    assert summary_statistics.shape == (165, 5)


@pytest.mark.skipif('fmu.ensemble' not in sys.modules,
                    reason="Requires fmu.ensemble installed")
def test_time_series_data():

    summary_data = get_time_series_data(
        ensemble_paths=VOVLE_ENSEMBLE_PATHS,
        time_index=VOLVE_TIME_INDEX,
        column_keys=VOLVE_COLUMN_KEYS,
        ensemble_set_name=VOLVE_ENSEMBLESET_NAME
    )
    assert isinstance(summary_data, pd.DataFrame)
    assert summary_data.shape == (693, 7)


@pytest.mark.skipif('fmu.ensemble' not in sys.modules,
                    reason="Requires fmu.ensemble installed")
def test_get_time_series_fielgains():

    field_gains = get_time_series_fielgains(
        ensemble_paths=VOVLE_ENSEMBLE_PATHS,
        time_index=VOLVE_TIME_INDEX,
        column_keys=VOLVE_COLUMN_KEYS,
        base_ensembles=BASE_ENSEMBLES,
        delta_ensembles=DELTA_ENSEMBLES,
        ensemble_set_name=VOLVE_ENSEMBLESET_NAME
    )
    assert isinstance(field_gains, pd.DataFrame)
    assert field_gains.shape == (825, 7)
    assert all([column in field_gains.columns
                for column in ['IROENS - REFENS', 'REAL', 'DATE']])

    iorens, refens = 'iter--0', 'iter--1'
    compared_ensembles = f'{iorens} - {refens}'
    field_gain = field_gains[
        field_gains['IROENS - REFENS'] == compared_ensembles]
    assert isinstance(field_gain, pd.DataFrame)
    assert field_gain.shape == (275, 7)

# -*- coding: utf-8 -*-
import sys
sys.path.append('../')
sys.path.append('../webviz_subsurface/containers/')
import pandas as pd
from mock import patch
# patch out flask.app instance related decorators
patch('webviz_config.common_cache.cache.memoize',
      lambda *x, **y: lambda f: f).start()
from webviz_subsurface.datainput import load_ensemble_set, \
    get_time_series_statistics, get_time_series_fielgains, get_time_series_data
# to avoide "module webviz_subsurface.containers has no attribute 'DiskUsage"
from _summary import trace_group, single_trace


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
DELTA_ENSEMBLES =  ['iter--0', 'iter--1', 'iter--2']


def test_load_ensemble_set():

    ensset = load_ensemble_set(
        ensemble_paths=VOVLE_ENSEMBLE_PATHS,
        ensemble_set_name=VOLVE_ENSEMBLESET_NAME
    )
    assert len(ensset) == 3
    assert len(ensset["iter--0"].get_df("STATUS")) == 120
    assert len(ensset["iter--1"].get_df("STATUS")) == 100
    assert len(ensset["iter--2"].get_df("STATUS")) == 80


def test_time_series_statistics():

    summary_statistics = get_time_series_statistics(
        ensemble_paths=VOVLE_ENSEMBLE_PATHS,
        time_index=VOLVE_TIME_INDEX,
        column_keys=VOLVE_COLUMN_KEYS
    )
    assert isinstance(summary_statistics, pd.DataFrame)
    assert summary_statistics.shape == (165, 5)


def test_time_series_data():

    summary_data = get_time_series_data(
        ensemble_paths=VOVLE_ENSEMBLE_PATHS,
        time_index=VOLVE_TIME_INDEX,
        column_keys=VOLVE_COLUMN_KEYS,
        ensemble_set_name='Volve'
    )
    assert isinstance(summary_data, pd.DataFrame)
    assert summary_data.shape == (660, 7)


def test_get_time_series_fielgains():

    field_gains = get_time_series_fielgains(
        ensemble_paths=VOVLE_ENSEMBLE_PATHS,
        time_index=VOLVE_TIME_INDEX,
        column_keys=VOLVE_COLUMN_KEYS,
        base_ensembles=BASE_ENSEMBLES,
        delta_ensembles=DELTA_ENSEMBLES,
        ensemble_set_name='Volve'
    )
    assert isinstance(field_gains, pd.DataFrame)
    assert field_gains.shape == (792, 7)
    assert all([column in field_gains.columns
                for column in ['IROENS - REFENS', 'REAL', 'DATE']])

    iorens, refens = 'iter--0', 'iter--1'
    compared_ensembles = f'{iorens} - {refens}'
    field_gain = field_gains[
        field_gains['IROENS - REFENS'] == compared_ensembles]
    assert isinstance(field_gain, pd.DataFrame)
    assert field_gain.shape == (264, 7)


def test_trace_group():

    summary_data = pd.read_csv('./data/Iter0_FOPT.csv')
    _trace_group = trace_group(
        ens_smry_data=summary_data,
        ens='Volve--0',
        vector='FOPT',
        color='red'
    )
    assert len(_trace_group) == 24
    assert len(_trace_group[0]) == 7


def test_single_trace():

    summary_data = pd.read_csv('./data/Iter0_FOPT.csv')
    _single_trace = single_trace(
        ens_smry_data=summary_data,
        ens='Volve--0',
        vector='FOPT',
        color='red'
    )
    assert len(_single_trace) == 7

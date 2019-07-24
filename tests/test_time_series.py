# -*- coding: utf-8 -*-


import sys
sys.path.append('../')
import pandas as pd
from mock import patch
# patch out flask.app instance related decorators
patch('webviz_config.common_cache.cache.memoize',
      lambda *x, **y: lambda f: f).start()
from webviz_subsurface.datainput import load_ensemble_set, get_time_series_data, \
    get_time_series_statistics, get_time_series_fielgains


# define recurring variables
volve_ensemble_paths = [
        ('iter--0', '/scratch/fmu/stcr/volve/realization-*/iter-0'),
        ('iter--1', '/scratch/fmu/stcr/volve/realization-*/iter-1'),
        ('iter--2', '/scratch/fmu/stcr/volve/realization-*/iter-2'),
]
volve_ensemble_set_name='Volve'
volve_time_index='yearly'
volve_column_keys=['FOP*', 'FGP*']


def test_load_ensemble_set():

    ensset = load_ensemble_set(
        ensemble_paths=volve_ensemble_paths,
        ensemble_set_name=volve_ensemble_set_name
    )
    assert len(ensset) == 3
    assert len(ensset["iter--0"].get_df("STATUS")) == 120
    assert len(ensset["iter--1"].get_df("STATUS")) == 100
    assert len(ensset["iter--2"].get_df("STATUS")) == 80


def test_time_series_statistics():

    summary_statistics = get_time_series_statistics(
        ensemble_paths=volve_ensemble_paths,
        time_index=volve_time_index,
        column_keys=volve_column_keys
    )
    assert isinstance(summary_statistics, pd.DataFrame)
    assert summary_statistics.shape == (165, 5)


def test_time_series_data():

    summary_data = get_time_series_data(
        ensemble_paths=volve_ensemble_paths,
        time_index=volve_time_index,
        column_keys=volve_column_keys,
        ensemble_set_name='Volve'
    )
    assert isinstance(summary_data, pd.DataFrame)
    assert summary_data.shape == (660, 7)


def test_get_time_series_fielgains():

    field_gains = get_time_series_fielgains(
        ensemble_paths=volve_ensemble_paths,
        time_index=volve_time_index,
        column_keys=volve_column_keys,
        ensemble_set_name='Volve'
    )
    assert isinstance(field_gains, pd.DataFrame)
    assert field_gains.shape == (2156, 7)
    assert all([column in field_gains.columns
                for column in ['IROENS - REFENS', 'REAL', 'DATE']])

    iorens, refens = 'iter--0', 'iter--1'
    compared_ensembles = f'{iorens} - {refens}'
    field_gain = field_gains[
        field_gains['IROENS - REFENS'] == compared_ensembles]
    assert isinstance(field_gain, pd.DataFrame)
    assert field_gain.shape == (264, 7)
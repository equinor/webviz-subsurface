import sys
sys.path.append('../')
import pandas as pd
from mock import patch
# pathing .cache.memoize with a pass through decorator function
# lambda *x, **y: lambda f: f   # takes params
# Important: decorators need to be patched before they are applied within
# a module that uses them. # They get applied when the module is loaded.
# http://alexmarandon.com/articles/python_mock_gotchas/
patch('webviz_config.common_cache.cache.memoize',
      lambda *x, **y: lambda f: f).start()
from webviz_subsurface.datainput import get_summary_data, get_summary_stats, \
    get_fieldgain, gather_fieldgains_combinations


def test_summary_data():

    smry_data = get_summary_data(
        ensemble_paths=[
            ('iter--0', '/scratch/fmu/stcr/volve/realization-*/iter-0'),
            ('iter--1', '/scratch/fmu/stcr/volve/realization-*/iter-1'),
        ],
        ensemble_set_name='Volve',
        time_index='yearly',
        column_keys=['FOP*', 'FGP*'],
    )
    assert smry_data.shape == (484, 7)
    assert isinstance(smry_data, pd.DataFrame)
    assert 'REAL' in smry_data.columns
    assert 'ENSEMBLE' in smry_data.columns

    smry_stats = get_summary_stats(
        ensemble_paths=[
            ('iter--0', '/scratch/fmu/stcr/volve/realization-*/iter-0'),
            ('iter--1', '/scratch/fmu/stcr/volve/realization-*/iter-1'),
        ],
        time_index='yearly',
        column_keys=['FOP*', 'FGP*'],
    )
    assert smry_stats.shape == (110, 5)
    assert isinstance(smry_stats, pd.DataFrame)
    assert 'REAL' not in smry_stats.columns
    assert 'ENSEMBLE' in smry_stats.columns

    fieldgain = get_fieldgain(
        ensemble_paths=[
            ('iter--0', '/scratch/fmu/stcr/volve/realization-*/iter-0'),
            ('iter--1', '/scratch/fmu/stcr/volve/realization-*/iter-1'),
        ],
        time_index='yearly',
        column_keys=['FOP*', 'FGP*'],
        iorens='iter--0',
        refens='iter--1',
        ensemble_set_name='Volve'
    )
    assert fieldgain.shape == (264, 6)
    assert isinstance(fieldgain, pd.DataFrame)
    assert 'REAL' in fieldgain.columns
    assert 'ENSEMBLE' not in fieldgain.columns


def test_gather_fieldgains_combinations():

    gathered_fieldgains = gather_fieldgains_combinations(
        ensemble_paths=[
            ('iter--0', '/scratch/fmu/stcr/volve/realization-*/iter-0'),
            ('iter--1', '/scratch/fmu/stcr/volve/realization-*/iter-1'),
            ('iter--2', '/scratch/fmu/stcr/volve/realization-*/iter-2'),
        ],
        ensemble_set_name='Volve',
        time_index='yearly',
        column_keys=['FOP*', 'FGP*'],
    )

    assert 'iter--0 - iter--1' in gathered_fieldgains.columns
    assert 'iter--1 - iter--0' in gathered_fieldgains.columns
    assert isinstance(gathered_fieldgains, pd.DataFrame)
    assert 'REAL' in gathered_fieldgains.columns
import pytest
from mock import patch
import flask_caching
patch('webviz_config.common_cache.cache.memoize',
      new_callable=None).start()
import sys
sys.path.append('../')
from webviz_subsurface.datainput import get_summary_data


def test_summary_data():

    smry_data = get_summary_data(
        ensemble_paths=[
            ('Volve--0', '/scratch/fmu/stcr/volve/realization-*/iter-0'),
            ('Volve--1', '/scratch/fmu/stcr/volve/realization-*/iter-1'),
        ],
        time_index = 'yearly',
        column_keys = ['FOP*', 'FGP*'],
    )

"""
    Posssible solutions:
        - test on undecorated function but use decorated in app

            @numba.jit
            def f(a, b):
              return f_undecorated(a, b)

            def f_undecorated(a, b):
              return a + b

        - move caching into app itself

        - monkey-patch a decorator:
        https://stackoverflow.com/questions/7667567/ \
        can-i-patch-a-python-decorator-before-it-wraps \
        -a-function

            Import the module that contains it
            Define the mock decorator function
            Set e.g. module.decorator = mymockdecorator
            Import the module(s) that use the decorator, or use it in 
            your own module.
"""

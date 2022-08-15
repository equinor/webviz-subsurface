# isort: skip_file
from unittest import mock

import dash
import pandas as pd
import webviz_core_components as wcc
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE

# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterCorrelation
from webviz_config.themes import default_theme

# pylint: enable=no-name-in-module

# mocked functions
GET_PARAMETERS = "webviz_subsurface.plugins._parameter_correlation.get_parameters"


def test_parameter_corr(webviz_duo: dash.testing.composite.DashComposite) -> None:

    webviz_settings = WebvizSettings(
        shared_settings={"scratch_ensembles": {"iter-0": ""}}, theme=default_theme
    )
    ensembles = ["iter-0"]

    with mock.patch(GET_PARAMETERS) as mock_parameters:
        mock_parameters.return_value = pd.read_csv("tests/data/parameters.csv")

        parameter_correlation = ParameterCorrelation(webviz_settings, ensembles)

        webviz_duo.start_server(parameter_correlation)

        webviz_duo.toggle_webviz_drawer()

        # Using str literals directly, not IDs from the plugin as intended because
        # the run test did not accept the imports

        my_component = webviz_duo.find_view_setting_group_unique_id(
            "paracorr", "settings", "shared-ensemble"
        )
        if not my_component.text.startswith("iter-0"):
            raise AssertionError()

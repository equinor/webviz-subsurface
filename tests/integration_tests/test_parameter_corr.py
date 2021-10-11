from unittest import mock

import dash
import pandas as pd
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE

# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterCorrelation
from webviz_config.themes import default_theme

# pylint: enable=no-name-in-module

# mocked functions
GET_PARAMETERS = "webviz_subsurface.plugins._parameter_correlation.get_parameters"


def test_parameter_corr(dash_duo: dash.testing.composite.DashComposite) -> None:

    app = dash.Dash(__name__)
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True
    app.config.suppress_callback_exceptions = True
    CACHE.init_app(app.server)
    webviz_settings = WebvizSettings(
        shared_settings={"scratch_ensembles": {"iter-0": ""}}, theme=default_theme
    )
    ensembles = ["iter-0"]

    with mock.patch(GET_PARAMETERS) as mock_parameters:
        mock_parameters.return_value = pd.read_csv("tests/data/parameters.csv")

        parameter_correlation = ParameterCorrelation(app, webviz_settings, ensembles)

        app.layout = parameter_correlation.layout
        dash_duo.start_server(app)

        my_component = dash_duo.find_element(
            f"#{parameter_correlation.ids('ensemble-all')}"
        )

        if not my_component.text.startswith("iter-0"):
            raise AssertionError()

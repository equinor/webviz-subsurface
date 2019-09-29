import mock
import dash
import pandas as pd
from webviz_config.common_cache import cache
from webviz_config.containers import ParameterCorrelation # pylint: disable=no-name-in-module


def test_parameter_corr(dash_duo):

    app = dash.Dash(__name__)
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True
    app.config.suppress_callback_exceptions = True
    cache.init_app(app.server)
    container_settings = {"scratch_ensembles": {"iter-0": ""}}
    ensembles = ["iter-0"]

    with mock.patch(
        "webviz_subsurface.containers._parameter_correlation.get_parameters"
    ) as mock_parameters:
        mock_parameters.return_value = pd.read_csv("tests/data/parameters.csv")

        param_corr = ParameterCorrelation(app, container_settings, ensembles)

        app.layout = param_corr.layout
        dash_duo.start_server(app)

        my_component = dash_duo.find_element(f"#{param_corr.ens_matrix_id}")

        if not my_component.text.startswith("iter-0"):
            raise AssertionError()

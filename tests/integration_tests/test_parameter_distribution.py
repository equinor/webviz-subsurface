import mock
import dash
import pandas as pd
from webviz_config.common_cache import cache
from webviz_config.containers import ParameterDistribution

# mocked functions
get_parameters = 'webviz_subsurface.containers'\
                '._parameter_distribution.get_parameters'


def test_parameter_dist(dash_duo):

    app = dash.Dash(__name__)
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True
    app.config.suppress_callback_exceptions = True
    cache.init_app(app.server)
    container_settings = {'scratch_ensembles': {'iter-0': ''}}
    ensembles = ['iter-0']

    with mock.patch(get_parameters) as mock_parameters:
        mock_parameters.return_value = pd.read_csv('tests/data/parameters.csv')

        p = ParameterDistribution(app, container_settings, ensembles)

        app.layout = p.layout
        dash_duo.start_server(app)

        my_component = dash_duo.find_element(f'#{p.ens_matrix_id}')

        if not my_component.text.startswith('iter-0'):
            raise AssertionError()

import mock
import dash
import pandas as pd
from pytest_dash.wait_for import wait_for_element_by_css_selector
from webviz_config.common_cache import cache
from webviz_subsurface.containers import _parameter_distribution


# mocked functions
get_parameters = 'webviz_subsurface.containers'\
                '._parameter_distribution.get_parameters'


def test_parameter_dist(dash_threaded):

    app = dash.Dash(__name__)
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True
    app.config.suppress_callback_exceptions = True
    cache.init_app(app.server)
    driver = dash_threaded.driver
    container_settings = {'scratch_ensembles': {'iter-0': ''}}
    ensemble = 'iter-0'

    with mock.patch(get_parameters) as mock_parameters:
        mock_parameters.return_value = pd.read_csv('tests/data/parameters.csv')

        p = _parameter_distribution.\
            ParameterDistribution(app, container_settings, ensemble)

        app.layout = p.layout
        dash_threaded(app)

        my_component = wait_for_element_by_css_selector(
                           driver,
                           f'#{p.dropdown_vector_id}'
                       )

        if 'REAL' != my_component.text:
            raise AssertionError()

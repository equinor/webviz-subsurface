import mock
import dash
import pandas as pd
from webviz_config.common_cache import cache
from webviz_config.containers import InplaceVolumes

# mocked functions
extract_volumes = 'webviz_subsurface.containers'\
    '._inplace_volumes.extract_volumes'


def test_inplace_volumes(dash_duo):

    app = dash.Dash(__name__)
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True
    app.config.suppress_callback_exceptions = True
    cache.init_app(app.server)
    container_settings = {'scratch_ensembles': {'iter-0': '', 'iter-1': ''}}
    ensembles = ['iter-0', 'iter-1']
    volfiles = {'geogrid': 'geogrid--oil.csv', 'simgrid': 'simgrid--oil.csv'}

    with mock.patch(extract_volumes) as mock_volumes:
        mock_volumes.return_value = pd.read_csv('tests/data/volumes.csv')

        vol = InplaceVolumes(app, container_settings, ensembles, volfiles)

        app.layout = vol.layout
        dash_duo.start_server(app)

        if 'Stock Tank Oil Initially Inplace' not in dash_duo.wait_for_element(
                f'#{vol.response_id}').text:
            raise AssertionError()

        if dash_duo.get_logs() != []:
            raise AssertionError()

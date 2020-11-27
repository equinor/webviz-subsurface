import pathlib

import pytest
import dash
from webviz_config.common_cache import CACHE


def pytest_addoption(parser):
    parser.addoption(
        "--testdata-folder",
        type=pathlib.Path,
        default=pathlib.Path("webviz-subsurface-testdata"),
        help="Path to webviz-subsurface-testdata folder",
    )


@pytest.fixture
def testdata_folder(request):
    return request.config.getoption("--testdata-folder")


@pytest.fixture()
def app():
    dash_app = dash.Dash(__name__)
    dash_app.css.config.serve_locally = True
    dash_app.scripts.config.serve_locally = True
    dash_app.config.suppress_callback_exceptions = True
    CACHE.init_app(dash_app.server)
    yield dash_app

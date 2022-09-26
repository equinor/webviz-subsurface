import pathlib
from typing import Any, Dict

import dash
import pytest
from _pytest.config.argparsing import Parser
from _pytest.fixtures import SubRequest
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE
from webviz_config.themes import default_theme
from webviz_config.webviz_factory_registry import WEBVIZ_FACTORY_REGISTRY
from webviz_config.webviz_instance_info import WEBVIZ_INSTANCE_INFO, WebvizRunMode


def pytest_addoption(parser: Parser) -> None:
    parser.addoption(
        "--testdata-folder",
        type=pathlib.Path,
        default=pathlib.Path("webviz-subsurface-testdata"),
        help="Path to webviz-subsurface-testdata folder",
    )


@pytest.fixture(name="testdata_folder")
def testdata_folder_fixture(request: SubRequest) -> Any:
    return request.config.getoption("--testdata-folder")


@pytest.fixture()
def app() -> dash.Dash:
    dash_app = dash.Dash(__name__)

    WEBVIZ_INSTANCE_INFO.initialize(
        dash_app=dash_app,
        run_mode=WebvizRunMode.NON_PORTABLE,
        theme=default_theme,
        storage_folder=pathlib.Path(__file__).resolve().parent,
    )
    try:
        WEBVIZ_FACTORY_REGISTRY.initialize(None)
    except RuntimeError:
        pass

    dash_app.css.config.serve_locally = True
    dash_app.scripts.config.serve_locally = True
    dash_app.config.suppress_callback_exceptions = True
    CACHE.init_app(dash_app.server)
    yield dash_app


@pytest.fixture()
def shared_settings(testdata_folder: pathlib.Path) -> Dict:
    return {
        "HM_SETTINGS": WebvizSettings(
            theme=default_theme,
            shared_settings={
                "scratch_ensembles": {
                    "iter-0": f"{testdata_folder}/01_drogon_ahm/realization-*/iter-0",
                    "iter-3": f"{testdata_folder}/01_drogon_ahm/realization-*/iter-3",
                }
            },
        ),
        "HM_ENSEMBLES": ["iter-0", "iter-3"],
        "SENS_SETTINGS": WebvizSettings(
            theme=default_theme,
            shared_settings={
                "scratch_ensembles": {
                    "sens_run": f"{testdata_folder}/01_drogon_design/realization-*/iter-0",
                }
            },
        ),
        "SENS_ENSEMBLES": ["sens_run"],
    }

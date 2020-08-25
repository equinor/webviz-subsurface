import pathlib

import pytest


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

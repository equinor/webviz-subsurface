import sys
import subprocess  # nosec
from pathlib import Path

from dash.testing.composite import DashComposite
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)


def test_full_example(
    testdata_folder: Path, dash_duo: DashComposite, tmp_path: Path
) -> None:

    # https://github.com/plotly/dash/issues/1164:
    # We are accessing a private member here which seems to be necessary due to the
    # aforementioned issue. Ignore the respective pylint warning.
    # pylint: disable=protected-access
    dash_duo._wd_wait = WebDriverWait(
        dash_duo.driver,
        timeout=10,
        ignored_exceptions=(NoSuchElementException, StaleElementReferenceException),
    )
    # pylint: enable=protected-access

    # Build a portable webviz from config file
    appdir = tmp_path / "app"
    subprocess.call(  # nosec
        ["webviz", "build", "webviz-raw-data.yml", "--portable", appdir],
        cwd=testdata_folder / "webviz_examples",
    )
    # Remove Talisman
    file_name = appdir / "webviz_app.py"
    with open(file_name, "r") as file:
        lines = file.readlines()
    with open(file_name, "w") as file:
        for line in lines:
            if not line.strip("\n").startswith("Talisman"):
                file.write(line)
    # Import generated app
    sys.path.append(str(appdir))

    # webviz_app was just created, temporarily ignore the import-outside-toplevel warning
    # and the import-error.
    # pylint: disable=import-outside-toplevel
    # pylint: disable=import-error
    from webviz_app import app

    # pylint: enable=import-outside-toplevel
    # pylint: enable=import-error

    # Start and test app
    dash_duo.start_server(app)
    for page in [
        "inplacevolumesonebyone",
        "reservoirsimulationtimeseriesonebyone",
        "inplacevolumes",
        "parameterdistribution",
        "parametercorrelation",
        "reservoirsimulationtimeseries",
    ]:
        dash_duo.wait_for_element(f"#{page}").click()
        logs = [
            log
            for log in dash_duo.get_logs()
            if "TypeError: Cannot read property 'hardwareConcurrency' of undefined"
            not in log["message"]
        ]

        if logs != []:
            raise AssertionError(page, logs)

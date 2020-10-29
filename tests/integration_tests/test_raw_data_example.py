import sys
import subprocess  # nosec

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)


def test_full_example(testdata_folder, dash_duo, tmp_path):

    # https://github.com/plotly/dash/issues/1164:
    dash_duo._wd_wait = WebDriverWait(
        dash_duo.driver,
        timeout=10,
        ignored_exceptions=(NoSuchElementException, StaleElementReferenceException),
    )

    def wait_for_clickable(selector, timeout=None):
        """Explicit wait until the element is clickable, timeout if not set,
        equals to the fixture's `wait_timeout` shortcut to `WebDriverWait` with
        `EC.element_to_be_clickable`."""
        return dash_duo._wd_wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector)),
        )

    # Build a portable webviz from config file
    appdir = tmp_path / "app"
    subprocess.call(  # nosec
        ["webviz", "build", "webviz-raw-data.yml", "--portable", appdir],
        cwd=testdata_folder / "webviz_examples",
    )
    # Remove Talisman
    fn = appdir / "webviz_app.py"
    with open(fn, "r") as f:
        lines = f.readlines()
    with open(fn, "w") as f:
        for line in lines:
            if not line.strip("\n").startswith("Talisman"):
                f.write(line)
    # Import generated app
    sys.path.append(str(appdir))
    from webviz_app import app

    # Start and test app
    dash_duo.start_server(app)
    for page in [
        "inplacevolumesonebyone",
        "reservoirsimulationtimeseriesonebyone",
        "inplacevolumes",
        # "parameterdistribution",
        "parametercorrelation",
        "reservoirsimulationtimeseries",
    ]:
        wait_for_clickable(f"#{page}").click()
        logs = [
            log
            for log in dash_duo.get_logs()
            if "TypeError: Cannot read property 'hardwareConcurrency' of undefined"
            not in log["message"]
        ]

        if logs != []:
            raise AssertionError(page, logs)

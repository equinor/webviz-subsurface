import sys
import subprocess  # nosec


def test_basic_example(dash_duo, tmp_path):
    # Build a portable webviz from config file
    appdir = tmp_path / "app"
    subprocess.call(  # nosec
        ["webviz", "build", "aggregated.yaml", "--portable", appdir],
        cwd="./webviz-subsurface-testdata/webviz_examples",
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
        "reservoirsimulationtimeseries",
        "reservoirsimulationtimeseries_with_options_set",
        # "parameterdistribution",
        "morris_plot",
        "grid_viewer",
        "seg-y_viewer",
        "last_page",
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

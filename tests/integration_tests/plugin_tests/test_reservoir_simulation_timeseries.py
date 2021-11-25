import warnings

# pylint: disable=no-name-in-module
from webviz_config.plugins import ReservoirSimulationTimeSeries


def test_reservoir_simulation_timeseries(
    dash_duo, app, shared_settings, testdata_folder
) -> None:
    plugin = ReservoirSimulationTimeSeries(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        obsfile=testdata_folder
        / "01_drogon_ahm"
        / "share"
        / "observations"
        / "tables"
        / "ert_observations.yml",
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)

    logs = []
    for log in dash_duo.get_logs():
        if "dash_renderer" in log.get("message"):
            warnings.warn(log.get("message"))
        else:
            logs.append(log)
    assert not logs

# pylint: disable=no-name-in-module
from webviz_config.plugins import VolumetricAnalysis


def test_volumetrics_no_sens(dash_duo, app, shared_settings) -> None:
    plugin = VolumetricAnalysis(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        volfiles={"geogrid": "geogrid--vol.csv", "simgrid": "simgrid--vol.csv"},
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []


def test_volumetrics_sens(dash_duo, app, shared_settings) -> None:
    plugin = VolumetricAnalysis(
        app,
        shared_settings["SENS_SETTINGS"],
        ensembles=shared_settings["SENS_ENSEMBLES"],
        volfiles={"geogrid": "geogrid--vol.csv", "simgrid": "simgrid--vol.csv"},
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

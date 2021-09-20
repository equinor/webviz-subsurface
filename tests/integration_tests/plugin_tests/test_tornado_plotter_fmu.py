# pylint: disable=no-name-in-module
from webviz_config.plugins import TornadoPlotterFMU


def test_tornado_plotter_fmu(dash_duo, app, shared_settings) -> None:
    plugin = TornadoPlotterFMU(
        app,
        shared_settings["SENS_SETTINGS"],
        ensemble=shared_settings["SENS_ENSEMBLES"][0],
        csvfile="share/results/volumes/geogrid--vol.csv",
        multi_value_selectors=["REGION", "ZONE"],
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

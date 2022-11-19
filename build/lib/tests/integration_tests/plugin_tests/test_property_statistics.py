import warnings

# pylint: disable=no-name-in-module
from webviz_config.plugins import PropertyStatistics


def test_property_statistics(dash_duo, app, shared_settings) -> None:
    plugin = PropertyStatistics(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        statistics_file="share/results/tables/grid_property_statistics_geogrid.csv",
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

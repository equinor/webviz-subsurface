# pylint: disable=no-name-in-module
from webviz_config.plugins import PvtPlot


def test_pvt_plot(dash_duo, app, shared_settings) -> None:
    plugin = PvtPlot(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        pvt_relative_file_path="share/results/tables/pvt.csv",
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

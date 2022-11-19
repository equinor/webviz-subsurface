# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterDistribution


def test_parameter_distribution(dash_duo, app, shared_settings) -> None:
    plugin = ParameterDistribution(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

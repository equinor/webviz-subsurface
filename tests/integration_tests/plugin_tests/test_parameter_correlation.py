# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterCorrelation


def test_parameter_correlation(dash_duo, app, shared_settings) -> None:

    plugin = ParameterCorrelation(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        drop_constants=True,
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterParallelCoordinates


def test_parameter_parallel_coordinates(dash_duo, app, shared_settings) -> None:
    plugin = ParameterParallelCoordinates(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

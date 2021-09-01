# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterResponseCorrelation


def test_parameter_response_correlation(dash_duo, app, shared_settings) -> None:
    plugin = ParameterResponseCorrelation(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        response_file="share/results/volumes/geogrid--vol.csv",
        response_filters={"ZONE": "multi", "REGION": "multi"},
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

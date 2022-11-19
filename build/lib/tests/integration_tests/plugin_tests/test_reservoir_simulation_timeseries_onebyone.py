# pylint: disable=no-name-in-module
from webviz_config.plugins import ReservoirSimulationTimeSeriesOneByOne


def test_reservoir_simulation_timeseries_onebyone(
    dash_duo, app, shared_settings
) -> None:
    plugin = ReservoirSimulationTimeSeriesOneByOne(
        app,
        shared_settings["SENS_SETTINGS"],
        ensembles=shared_settings["SENS_ENSEMBLES"],
        initial_vector="FOPT",
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

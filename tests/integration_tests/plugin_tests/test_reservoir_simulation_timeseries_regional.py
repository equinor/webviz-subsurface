# pylint: disable=no-name-in-module
from webviz_config.plugins import ReservoirSimulationTimeSeriesRegional


def test_reservoir_simulation_timeseries_regional(
    dash_duo, app, shared_settings, testdata_folder
) -> None:
    plugin = ReservoirSimulationTimeSeriesRegional(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        fipfile=testdata_folder
        / "01_drogon_ahm"
        / "realization-0"
        / "iter-0"
        / "share"
        / "results"
        / "tables"
        / "fip.yml",
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

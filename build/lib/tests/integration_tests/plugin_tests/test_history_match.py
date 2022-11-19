# pylint: disable=no-name-in-module
from webviz_config.plugins import HistoryMatch


def test_history_match(dash_duo, app, testdata_folder, shared_settings) -> None:

    plugin = HistoryMatch(
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        observation_file=testdata_folder
        / "01_drogon_ahm"
        / "share"
        / "observations"
        / "tables"
        / "ert_observations.yml",
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

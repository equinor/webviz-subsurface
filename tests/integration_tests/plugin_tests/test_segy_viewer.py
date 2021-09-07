# pylint: disable=no-name-in-module
from webviz_config.plugins import SegyViewer


def test_segy_viewer(dash_duo, app, shared_settings, testdata_folder) -> None:
    plugin = SegyViewer(
        app,
        shared_settings["HM_SETTINGS"],
        segyfiles=[
            testdata_folder
            / "01_drogon_ahm"
            / "realization-0"
            / "iter-0"
            / "share"
            / "results"
            / "seismic"
            / "seismic--amplitude_depth--20180701_20180101.segy"
        ],
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

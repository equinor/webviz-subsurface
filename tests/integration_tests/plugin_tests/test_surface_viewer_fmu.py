# pylint: disable=no-name-in-module
from webviz_config.plugins import SurfaceViewerFMU


def test_surface_viewer_fmu(dash_duo, app, shared_settings, testdata_folder) -> None:
    plugin = SurfaceViewerFMU(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        wellsuffix=".rmswell",
        wellfolder=testdata_folder
        / "01_drogon_ahm"
        / "realization-0"
        / "iter-0"
        / "share"
        / "results"
        / "wells",
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

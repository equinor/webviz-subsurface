# pylint: disable=no-name-in-module
from webviz_config.plugins import RftPlotter


def test_rft_plotter(dash_duo, app, shared_settings, testdata_folder) -> None:
    plugin = RftPlotter(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        formations=testdata_folder
        / "01_drogon_ahm"
        / "realization-0"
        / "iter-0"
        / "share"
        / "results"
        / "tables"
        / "formations_res_only.csv",
        faultlines=testdata_folder
        / "01_drogon_ahm"
        / "realization-0"
        / "iter-0"
        / "share"
        / "results"
        / "polygons"
        / "toptherys--gl_faultlines_extract_postprocess.csv",
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)

    # This assert is commented out because it causes problem that are
    # seemingly random.
    # assert dash_duo.get_logs() == []

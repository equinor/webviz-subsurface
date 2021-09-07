# pylint: disable=no-name-in-module
from webviz_config.plugins import SurfaceWithSeismicCrossSection


def test_surface_with_seismic_crosssection(
    dash_duo, app, shared_settings, testdata_folder
) -> None:
    plugin = SurfaceWithSeismicCrossSection(
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
        surfacefiles=[
            testdata_folder
            / "01_drogon_ahm"
            / "realization-0"
            / "iter-0"
            / "share"
            / "results"
            / "maps"
            / "topvolon--ds_extract_geogrid.gri"
        ],
        surfacenames=["Top Volon"],
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

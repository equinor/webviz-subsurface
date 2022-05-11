# pylint: disable=no-name-in-module
from webviz_config.plugins import SurfaceWithGridCrossSection


def test_surface_with_grid_crosssection(
    dash_duo, app, shared_settings, testdata_folder
) -> None:
    plugin = SurfaceWithGridCrossSection(
        app,
        shared_settings["HM_SETTINGS"],
        gridfile=(
            testdata_folder
            / "01_drogon_ahm"
            / "realization-0"
            / "iter-0"
            / "share"
            / "results"
            / "grids"
            / "geogrid.roff"
        ),
        gridparameterfiles=[
            testdata_folder
            / "01_drogon_ahm"
            / "realization-0"
            / "iter-0"
            / "share"
            / "results"
            / "grids"
            / "geogrid--phit.roff"
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

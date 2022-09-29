# pylint: disable=no-name-in-module
from webviz_config.plugins import RftPlotter
from webviz_config.testing import WebvizComposite


def test_rft_plotter(
    _webviz_duo: WebvizComposite, shared_settings, testdata_folder
) -> None:
    plugin = RftPlotter(
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

    _webviz_duo.start_server(plugin)

    _webviz_duo.toggle_webviz_settings_drawer()
    _webviz_duo.toggle_webviz_settings_group(
        plugin.view("map-view").settings_group_unique_id("map-settings")
    )
    # Using str literals directly, not IDs from the plugin as intended because
    # the run test did not accept the imports

    my_component_id = _webviz_duo.view_settings_group_unique_component_id(
        "map-view", "map-settings", "map-ensemble"
    )
    _webviz_duo.wait_for_contains_text(my_component_id, "iter-0")
    assert _webviz_duo.get_logs() == []

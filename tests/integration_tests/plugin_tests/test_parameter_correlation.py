# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterCorrelation
from webviz_config.testing import WebvizComposite


def test_parameter_correlation(_webviz_duo: WebvizComposite, shared_settings) -> None:

    parameter_correlation = ParameterCorrelation(
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
    )

    _webviz_duo.start_server(parameter_correlation)

    _webviz_duo.toggle_webviz_settings_drawer()
    _webviz_duo.toggle_webviz_settings_group(
        parameter_correlation.view("paracorr").settings_group_unique_id("settings")
    )
    # Using str literals directly, not IDs from the plugin as intended because
    # the run test did not accept the imports

    my_component_id = _webviz_duo.view_settings_group_unique_component_id(
        "paracorr", "settings", "shared-ensemble"
    )
    _webviz_duo.wait_for_contains_text(my_component_id, "iter-0")
    assert _webviz_duo.get_logs() == []

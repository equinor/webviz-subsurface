# pylint: disable=no-name-in-module
from webviz_config.plugins import VfpAnalysis
from webviz_config.testing import WebvizComposite


def test_vfp_analysis(_webviz_duo: WebvizComposite, shared_settings: dict) -> None:
    plugin = VfpAnalysis(
        shared_settings["HM_SETTINGS"], vfp_file_pattern="tests/data/vfp.arrow"
    )

    _webviz_duo.start_server(plugin)

    assert _webviz_duo.get_logs() == []

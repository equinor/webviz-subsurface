# pylint: disable=no-name-in-module
from webviz_config.plugins import VfpAnalysis
from webviz_config.testing import WebvizComposite


def test_vfp_analysis(_webviz_duo: WebvizComposite, shared_settings: dict) -> None:
    plugin = VfpAnalysis(vfp_file_pattern="../../data/vfp.arrow")

    _webviz_duo.start_server(plugin)

    assert _webviz_duo.get_logs() == []

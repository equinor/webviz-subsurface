# pylint: disable=no-name-in-module
from webviz_config.plugins import BhpQc
from webviz_config.testing import WebvizComposite


def test_bhp_qc(_webviz_duo: WebvizComposite, shared_settings: dict) -> None:
    plugin = BhpQc(
        shared_settings["HM_SETTINGS"], ensembles=shared_settings["HM_ENSEMBLES"]
    )

    _webviz_duo.start_server(plugin)
    print(_webviz_duo.get_logs())
    assert not _webviz_duo.get_logs()

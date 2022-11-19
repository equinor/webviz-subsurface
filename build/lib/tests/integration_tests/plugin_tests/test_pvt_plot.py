# pylint: disable=no-name-in-module
from webviz_config.plugins import PvtPlot
from webviz_config.testing import WebvizComposite


def test_pvt_plot(_webviz_duo: WebvizComposite, shared_settings: dict) -> None:
    plugin = PvtPlot(
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        pvt_relative_file_path="share/results/tables/pvt.csv",
    )

    _webviz_duo.start_server(plugin)

    assert _webviz_duo.get_logs() == []

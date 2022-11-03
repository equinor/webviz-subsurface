# pylint: disable=no-name-in-module
from webviz_config.plugins import BhpQc


def test_bhp_qc(app, dash_duo, shared_settings) -> None:
    plugin = BhpQc(
        shared_settings["HM_SETTINGS"], ensembles=shared_settings["HM_ENSEMBLES"]
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

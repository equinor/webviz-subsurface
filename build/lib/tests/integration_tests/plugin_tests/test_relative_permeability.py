# pylint: disable=no-name-in-module
from webviz_config.plugins import RelativePermeability


def test_relative_permeability(dash_duo, app, shared_settings) -> None:
    plugin = RelativePermeability(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        relpermfile="share/results/tables/relperm.csv",
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

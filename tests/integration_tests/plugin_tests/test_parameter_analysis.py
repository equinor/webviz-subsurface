import warnings

# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterAnalysis


def test_parameter_analysis(dash_duo, app, shared_settings) -> None:

    plugin = ParameterAnalysis(
        app,
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        time_index="monthly",
        column_keys=["WWCT:*"],
        drop_constants=True,
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    logs = []
    for log in dash_duo.get_logs():
        if "dash_renderer" in log.get("message"):
            warnings.warn(log.get("message"))
        else:
            logs.append(log)
    assert logs == []

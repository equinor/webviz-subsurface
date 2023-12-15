import warnings

# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterAnalysis
from webviz_config.testing import WebvizComposite


def test_parameter_analysis(
    _webviz_duo: WebvizComposite, shared_settings: dict
) -> None:
    plugin = ParameterAnalysis(
        shared_settings["HM_SETTINGS"],
        ensembles=shared_settings["HM_ENSEMBLES"],
        column_keys=["WWCT:*"],
        time_index="monthly",
        drop_constants=True,
    )
    _webviz_duo.start_server(plugin)

    logs = []
    for log in _webviz_duo.get_logs() or []:
        if "dash_renderer" in log.get("message"):
            warnings.warn(log.get("message"))
        else:
            logs.append(log)
    assert not logs

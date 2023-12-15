import warnings

# pylint: disable=no-name-in-module
from webviz_config.plugins import SimulationTimeSeriesOneByOne
from webviz_config.testing import WebvizComposite


def test_simulation_timeseries_onebyone(
    _webviz_duo: WebvizComposite, shared_settings: dict
) -> None:
    plugin = SimulationTimeSeriesOneByOne(
        webviz_settings=shared_settings["SENS_SETTINGS"],
        ensembles=shared_settings["SENS_ENSEMBLES"],
        initial_vector="FOPT",
    )
    _webviz_duo.start_server(plugin)
    logs = []
    for log in _webviz_duo.get_logs() or []:
        if "dash_renderer" in log.get("message"):
            warnings.warn(log.get("message"))
        else:
            logs.append(log)
    assert not logs

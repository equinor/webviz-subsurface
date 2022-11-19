# pylint: disable=no-name-in-module
from webviz_config.plugins import LinePlotterFMU


def test_line_plotter_fmu(dash_duo, app, testdata_folder, shared_settings) -> None:

    plugin = LinePlotterFMU(
        app,
        shared_settings["HM_SETTINGS"],
        aggregated_csvfile=testdata_folder
        / "reek_test_data"
        / "aggregated_data"
        / "smry_hm.csv",
        aggregated_parameterfile=testdata_folder
        / "reek_test_data"
        / "aggregated_data"
        / "parameters_hm.csv",
        observation_file=testdata_folder / "reek_test_data" / "observations.yml",
        observation_group="smry",
        remap_observation_values={"DATE": "date"},
        initial_data={
            "x": "DATE",
            "y": "FOPR",
            "ensembles": ["iter-0", "iter-3"],
            "colors": {"iter-0": "red", "iter-3": "blue"},
        },
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

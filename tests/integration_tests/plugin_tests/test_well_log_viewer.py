# pylint: disable=no-name-in-module
from webviz_config.plugins import WellLogViewer


def test_well_log_viewer(dash_duo, app, testdata_folder) -> None:
    wellfolder = testdata_folder / "observed_data" / "wells/"
    plugin = WellLogViewer(
        app,
        wellfolder=wellfolder,
        wellsuffix=".rmswell",
        mdlog="MDepth",
        logtemplates=[f"{testdata_folder}/webviz_examples/all_logs_template.yml"],
    )
    app.layout = plugin.layout
    dash_duo.start_server(app)
    assert dash_duo.get_logs() == []

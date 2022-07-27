from unittest import mock

import dash
import pandas as pd
from webviz_config import WebvizSettings
from webviz_config.common_cache import CACHE

# pylint: disable=no-name-in-module
from webviz_config.plugins import ParameterCorrelation
from webviz_config.themes import default_theme

import webviz_core_components as wcc

# pylint: enable=no-name-in-module

# mocked functions
GET_PARAMETERS = "webviz_subsurface.plugins._parameter_correlation.get_parameters"


def test_parameter_corr(dash_duo: dash.testing.composite.DashComposite) -> None:

    app = dash.Dash(__name__)
    app.css.config.serve_locally = True
    app.scripts.config.serve_locally = True
    app.config.suppress_callback_exceptions = True
    CACHE.init_app(app.server)
    webviz_settings = WebvizSettings(
        shared_settings={"scratch_ensembles": {"iter-0": ""}}, theme=default_theme
    )
    ensembles = ["iter-0"]

    with mock.patch(GET_PARAMETERS) as mock_parameters:
        mock_parameters.return_value = pd.read_csv("tests/data/parameters.csv")

        parameter_correlation = ParameterCorrelation(webviz_settings, ensembles)

        app.layout = dash.html.Div(
            className="layoutWrapper",
            children=[
                wcc.WebvizContentManager(
                    id="webviz-content-manager",
                    children=[
                        wcc.WebvizSettingsDrawer(
                            id="settings-drawer",
                            children=parameter_correlation.get_all_settings(),
                        ),
                        wcc.WebvizPluginsWrapper(
                            id="plugins-wrapper",
                            children=parameter_correlation.plugin_layout(),
                        ),
                    ],
                ),
            ],
        )
        dash_duo.start_server(app)

        dash_duo.find_element(".WebvizSettingsDrawer__ToggleOpen").click()

        # Using str literals directly, not IDs from the plugin as intended because
        # the run test did not accept the imports
        my_component = dash_duo.find_element(
            "#"
            + parameter_correlation.shared_settings_group("both-plots")
            .component_unique_id("ensemble-both")
            .to_string()
        )

        if not my_component.text.startswith("iter-0"):
            raise AssertionError()

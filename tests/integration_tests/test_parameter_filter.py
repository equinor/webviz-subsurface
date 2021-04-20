import json

import pandas as pd
import dash_html_components as html
from dash.dependencies import Input, Output, State
from webviz_config.themes import default_theme
from webviz_config import WebvizSettings

# pylint: disable=no-name-in-module
from webviz_subsurface._components.parameter_filter import ParameterFilter


class TestParameterFilter:
    def test_dataframe(self, dash_duo, app, testdata_folder) -> None:

        dframe = pd.read_csv(testdata_folder / "aggregated_data" / "parameters.csv")
        component = ParameterFilter(app, "test", dframe)
        assert set(component._constant_parameters) == set(
            [
                "MULTFLT_F2",
                "MULTFLT_F3",
                "MULTFLT_F4",
                "MULTFLT_F5",
                "MULTZ_MIDREEK",
                "INTERPOLATE_GO",
            ]
        )
        assert set(component._range_parameters) == set(["RMS_SEED"])
        assert set(component._discrete_parameters) == set(
            [
                "FWL",
                "MULTFLT_F1",
                "INTERPOLATE_WO",
                "COHIBA_MODEL_MODE",
            ]
        )
        assert component.is_sensitivity_run == True
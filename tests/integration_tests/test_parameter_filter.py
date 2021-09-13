import pandas as pd

from webviz_subsurface._components.parameter_filter import ParameterFilter


class TestParameterFilter:
    def test_dataframe(self, dash_duo, app, testdata_folder) -> None:

        dframe = pd.read_csv(
            testdata_folder / "reek_test_data" / "aggregated_data" / "parameters.csv"
        )
        component = ParameterFilter(app, "test", dframe)
        assert set(component._discrete_parameters) == set(
            ["FWL", "MULTFLT_F1", "INTERPOLATE_WO", "COHIBA_MODEL_MODE", "RMS_SEED"]
        )
        assert component.is_sensitivity_run == True

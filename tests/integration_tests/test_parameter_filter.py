import pandas as pd

from webviz_subsurface._components.parameter_filter import ParameterFilter


def test_dataframe(testdata_folder) -> None:
    # pylint: disable=protected-access
    dframe = pd.read_csv(
        testdata_folder / "reek_test_data" / "aggregated_data" / "parameters.csv"
    )

    expected_discrete_parameters = [
        "FWL",
        "MULTFLT_F1",
        "INTERPOLATE_WO",
        "COHIBA_MODEL_MODE",
        "RMS_SEED",
    ]

    component = ParameterFilter("test", dframe, include_sens_filter=False)
    assert set(component._discrete_parameters) == set(expected_discrete_parameters)

    component = ParameterFilter("test", dframe, include_sens_filter=True)
    assert set(component._discrete_parameters) == set(
        expected_discrete_parameters + ["SENSNAME"]
    )

    assert component.is_sensitivity_run is True

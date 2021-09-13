# pylint: disable=protected-access
import pandas as pd
import pytest

from webviz_subsurface._components.tornado._tornado_data import TornadoData


def test_tornado_data_init():
    # fmt: off
    input_data = [
        ["REAL",  "SENSNAME",   "SENSCASE",  "SENSTYPE", "VALUE" ],
        [     0,         "A",    "p10_p90", "mc"       ,     10.0],
        [     1,         "A",    "p10_p90", "mc"       ,     20.0],
        [     2,         "B",       "deep", "scalar"   ,     5.0],
        [     3,         "B",       "deep", "scalar"   ,     6.0],
        [     4,         "C",    "shallow", "scalar"   ,     25.0],
        [     5,         "C",    "shallow", "scalar"   ,     26.0],
        [     6,         "D", "simulation", "mc"       ,     9.0],
        [     7,         "D", "simulation", "mc"       ,     11.0],
    ]
    # fmt: on

    input_df = pd.DataFrame(input_data[1:], columns=input_data[0])

    with pytest.raises(ValueError) as exc:
        TornadoData(dframe=input_df)
    assert exc.value.args[0] == "Reference SENSNAME rms_seed not in input data"

    tornado_data = TornadoData(dframe=input_df, reference="A")

    assert tornado_data._calculate_ref_average(input_df) == 15.0
    avg_list = tornado_data._calculate_sensitivity_averages(input_df)
    assert avg_list[0] == {
        "sensname": "A",
        "senscase": "P90",
        "values": 11.0,
        "values_ref": -26.666666666666668,
        "reals": [0],
    }
    low_high_list = tornado_data._calculate_tornado_low_high_list(avg_list)
    assert low_high_list[0] == {
        "low": -26.666666666666668,
        "low_base": 0,
        "low_label": "P90",
        "low_tooltip": -26.666666666666668,
        "true_low": 11.0,
        "low_reals": [0],
        "sensname": "A",
        "high": 26.666666666666668,
        "high_base": 0,
        "high_label": "P10",
        "high_tooltip": 26.666666666666668,
        "true_high": 19.0,
        "high_reals": [1],
    }

    tornado_data = TornadoData(
        dframe=input_df, reference="B", scale="Absolute", cutbyref=True
    )
    assert tornado_data._calculate_tornado_table(input_df).to_dict("records") == [
        {
            "low": 0.0,
            "low_base": 5.5,
            "low_label": "P90",
            "low_tooltip": 5.5,
            "true_low": 11.0,
            "low_reals": [],
            "sensname": "A",
            "high": 8.0,
            "high_base": 5.5,
            "high_label": "P10",
            "high_tooltip": 13.5,
            "true_high": 19.0,
            "high_reals": [0, 1],
        },
        {
            "low": 0.0,
            "low_base": 0.0,
            "low_label": None,
            "low_tooltip": 0.0,
            "true_low": 5.5,
            "low_reals": [],
            "sensname": "B",
            "high": 0.0,
            "high_base": 0.0,
            "high_label": "deep",
            "high_tooltip": 0.0,
            "true_high": 5.5,
            "high_reals": [2, 3],
        },
        {
            "low": 0.0,
            "low_base": 0.0,
            "low_label": None,
            "low_tooltip": 0.0,
            "true_low": 5.5,
            "low_reals": [],
            "sensname": "C",
            "high": 20.0,
            "high_base": 0.0,
            "high_label": "shallow",
            "high_tooltip": 20.0,
            "true_high": 25.5,
            "high_reals": [4, 5],
        },
        {
            "low": 0.0,
            "low_base": 3.6999999999999993,
            "low_label": "P90",
            "low_tooltip": 3.6999999999999993,
            "true_low": 9.2,
            "low_reals": [],
            "sensname": "D",
            "high": 1.6000000000000014,
            "high_base": 3.6999999999999993,
            "high_label": "P10",
            "high_tooltip": 5.300000000000001,
            "true_high": 10.8,
            "high_reals": [6, 7],
        },
    ]

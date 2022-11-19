import copy
import datetime

import numpy as np
import pandas as pd
import pytest

from webviz_subsurface._providers import Frequency
from webviz_subsurface._utils.dataframe_utils import make_date_column_datetime_object
from webviz_subsurface.plugins._simulation_time_series._views._subplot_view._types import (
    FanchartOptions,
    StatisticsOptions,
)

# pylint: disable=line-too-long
from webviz_subsurface.plugins._simulation_time_series._views._subplot_view._utils.create_vector_traces_utils import (
    create_history_vector_trace,
    create_vector_fanchart_traces,
    create_vector_observation_traces,
    create_vector_realization_traces,
    create_vector_statistics_traces,
    render_hovertemplate,
)

# *******************************************************************
#####################################################################
#
# CONFIGURE TESTDATA
#
#####################################################################
# *******************************************************************

INPUT_VECTOR_STATISTICS_DF = pd.DataFrame(
    columns=[
        "DATE",
        StatisticsOptions.MEAN,
        StatisticsOptions.MIN,
        StatisticsOptions.MAX,
        StatisticsOptions.P10,
        StatisticsOptions.P90,
        StatisticsOptions.P50,
    ],
    data=[
        [datetime.datetime(2020, 1, 1), 1.0, 2.0, 3.0, 4.0, 5.0, 6.0],
        [datetime.datetime(2020, 1, 2), 1.5, 2.5, 3.5, 4.5, 5.5, 6.5],
    ],
)
make_date_column_datetime_object(INPUT_VECTOR_STATISTICS_DF)


# *******************************************************************
#####################################################################
#
# UNIT TESTS
#
#####################################################################
# *******************************************************************


def test_crate_vector_observation_traces() -> None:
    first_observation = {
        "date": datetime.datetime(2020, 1, 1),
        "value": 2.0,
        "comment": "first obs",
        "error": 0.5,
    }
    second_observation = {
        "date": datetime.datetime(2020, 6, 5),
        "value": 5.0,
        "comment": "second obs",
        "error": 1.2,
    }
    vector_observations = {"observations": [first_observation, second_observation]}

    expected_traces = [
        {
            "name": "Observation",
            "legendgroup": "Observation",
            "x": [datetime.datetime(2020, 1, 1), []],
            "y": [2.0, []],
            "marker": {"color": "black"},
            "hovertemplate": "(%{x}, %{y})<br>first obs",
            "showlegend": False,
            "error_y": {
                "type": "data",
                "array": [0.5, []],
                "visible": True,
            },
        },
        {
            "name": "Observation",
            "legendgroup": "Observation",
            "x": [datetime.datetime(2020, 6, 5), []],
            "y": [5.0, []],
            "marker": {"color": "black"},
            "hovertemplate": "(%{x}, %{y})<br>second obs",
            "showlegend": False,
            "error_y": {
                "type": "data",
                "array": [1.2, []],
                "visible": True,
            },
        },
    ]

    # Add legendgroup info for verification
    legend_group = "test group"
    expected_traces_with_legend_group = copy.deepcopy(expected_traces)
    expected_traces_with_legend_group[0]["name"] = "Observation: " + legend_group
    expected_traces_with_legend_group[0]["legendgroup"] = legend_group
    expected_traces_with_legend_group[1]["name"] = "Observation: " + legend_group
    expected_traces_with_legend_group[1]["legendgroup"] = legend_group

    assert expected_traces == create_vector_observation_traces(vector_observations)
    assert expected_traces_with_legend_group == create_vector_observation_traces(
        vector_observations, legend_group=legend_group
    )


def test_create_vector_realization_traces() -> None:
    vector_df = pd.DataFrame(
        columns=["DATE", "REAL", "A"],
        data=[
            [datetime.datetime(2020, 1, 1), 1, 1.0],
            [datetime.datetime(2020, 2, 1), 1, 2.0],
            [datetime.datetime(2031, 5, 10), 2, 5.0],
            [datetime.datetime(2031, 6, 10), 2, 6.0],
        ],
    )
    make_date_column_datetime_object(vector_df)

    created_traces = create_vector_realization_traces(
        vector_df=vector_df,
        ensemble="Test ensemble",
        color="red",
        legend_group="Test group",
        line_shape="linear",
        hovertemplate="Test hovertemplate ",
        show_legend=True,
        legendrank=2,
    )

    expected_traces = [
        {
            "line": {"width": 1, "shape": "linear", "color": "red"},
            "mode": "lines",
            "x": [datetime.datetime(2020, 1, 1), datetime.datetime(2020, 2, 1)],
            "y": [1.0, 2.0],
            "hovertemplate": "Test hovertemplate Realization: 1, Ensemble: Test ensemble",
            "name": "Test group",
            "legendgroup": "Test group",
            "legendrank": 2,
            "showlegend": True,
        },
        {
            "line": {"width": 1, "shape": "linear", "color": "red"},
            "mode": "lines",
            "x": [datetime.datetime(2031, 5, 10), datetime.datetime(2031, 6, 10)],
            "y": [5.0, 6.0],
            "hovertemplate": "Test hovertemplate Realization: 2, Ensemble: Test ensemble",
            "name": "Test group",
            "legendgroup": "Test group",
            "legendrank": 2,
            "showlegend": False,
        },
    ]

    assert expected_traces == created_traces


def test_create_vector_realization_traces_raise_error() -> None:
    multiple_vectors_df = pd.DataFrame(columns=["DATE", "REAL", "A", "B"])

    with pytest.raises(ValueError) as err:
        create_vector_realization_traces(
            vector_df=multiple_vectors_df,
            ensemble="Test ensemble",
            color="red",
            legend_group="Test group",
            line_shape="linear",
            hovertemplate="Test hovertemplate ",
        )
    assert str(err.value) == "Expected one vector column present in dataframe, got 2!"


def test_create_history_vector_trace() -> None:
    input_samples = [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
        datetime.datetime(2020, 1, 3),
    ]
    input_history_data = np.array([1.0, 2.0, 3.0])

    created_trace = create_history_vector_trace(
        samples=input_samples,
        history_data=input_history_data,
        line_shape="linear",
        color="green",
        vector_name="Test hist vector",
    )

    expected_trace = {
        "line": {"shape": "linear", "color": "green"},
        "mode": "lines",
        "x": input_samples,
        "y": input_history_data,
        "hovertext": "History: Test hist vector",
        "hoverinfo": "y+x+text",
        "name": "History",
        "showlegend": False,
        "legendgroup": "History",
        "legendrank": None,
    }

    assert created_trace == expected_trace


def test_create_history_vector_trace_raise_error() -> None:
    with pytest.raises(ValueError) as err:
        create_history_vector_trace(
            samples=[datetime.datetime(2020, 1, 1)],
            history_data=np.array([1.0, 2.0]),
            line_shape="linear",
            color="green",
            vector_name="Test hist vector",
        )
    assert str(err.value) == "Number of samples unequal number of data points!"


def test_render_hovertemplate() -> None:
    template_daily = "(%{x|%b} %{x|%-d}, %{x|%Y}, %{y})<br>"
    template_weekly = template_daily
    template_monthly = "(%{x|%b} %{x|%Y}, %{y})<br>"
    template_quarterly = "(Q%{x|%q} %{x|%Y}, %{y})<br>"
    template_yearly = "(%{x|%Y}, %{y})<br>"
    template_default = "(%{x}, %{y})<br>"

    # Test PER_DAY_/PER_INTVL_ vector names
    assert template_daily == render_hovertemplate("PER_DAY_a", Frequency.DAILY)
    assert template_weekly == render_hovertemplate("PER_DAY_a", Frequency.WEEKLY)
    assert template_monthly == render_hovertemplate("PER_DAY_a", Frequency.MONTHLY)
    assert template_quarterly == render_hovertemplate("PER_DAY_a", Frequency.QUARTERLY)
    assert template_yearly == render_hovertemplate("PER_DAY_a", Frequency.YEARLY)
    assert template_default == render_hovertemplate("PER_DAY_a", None)

    # Test other vector names
    assert template_default == render_hovertemplate("Vector_a", Frequency.DAILY)
    assert template_default == render_hovertemplate("Vector_a", Frequency.WEEKLY)
    assert template_default == render_hovertemplate("Vector_a", Frequency.MONTHLY)
    assert template_default == render_hovertemplate("Vector_a", Frequency.QUARTERLY)
    assert template_default == render_hovertemplate("Vector_a", Frequency.YEARLY)
    assert template_default == render_hovertemplate("Vector_a", None)


def test_create_vector_fanchart_traces_all_fanchart_options() -> None:
    created_fanchart_traces = create_vector_fanchart_traces(
        INPUT_VECTOR_STATISTICS_DF,
        fanchart_options=[
            FanchartOptions.MEAN,
            FanchartOptions.MIN_MAX,
            FanchartOptions.P10_P90,
        ],
        hex_color="#2b00ff",
        legend_group="First Legendgroup",
        line_shape="linear",
        show_legend=True,
    )

    # Verify number of trace dicts in list
    assert len(created_fanchart_traces) == 5

    # Verify Min
    assert created_fanchart_traces[0]["name"] == "First Legendgroup"
    assert created_fanchart_traces[0].get("fill", None) is None
    assert created_fanchart_traces[0]["hovertemplate"] == "(%{x}, %{y})<br>Minimum"
    assert np.array_equal(created_fanchart_traces[0]["y"], np.array([2.0, 2.5]))
    assert created_fanchart_traces[0]["x"] == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
    ]

    # Verify P90
    assert created_fanchart_traces[1]["name"] == "First Legendgroup"
    assert created_fanchart_traces[1].get("fill", None) == "tonexty"
    assert created_fanchart_traces[1]["hovertemplate"] == "(%{x}, %{y})<br>P90"
    assert np.array_equal(created_fanchart_traces[1]["y"], np.array([5.0, 5.5]))
    assert created_fanchart_traces[1]["x"] == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
    ]

    # Verify P10
    assert created_fanchart_traces[2]["name"] == "First Legendgroup"
    assert created_fanchart_traces[2].get("fill", None) == "tonexty"
    assert created_fanchart_traces[2]["hovertemplate"] == "(%{x}, %{y})<br>P10"
    assert np.array_equal(created_fanchart_traces[2]["y"], np.array([4.0, 4.5]))
    assert created_fanchart_traces[2]["x"] == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
    ]

    # Verify Max
    assert created_fanchart_traces[3]["name"] == "First Legendgroup"
    assert created_fanchart_traces[3].get("fill", None) == "tonexty"
    assert created_fanchart_traces[3]["hovertemplate"] == "(%{x}, %{y})<br>Maximum"
    assert np.array_equal(created_fanchart_traces[3]["y"], np.array([3.0, 3.5]))
    assert created_fanchart_traces[3]["x"] == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
    ]

    # Verify Mean
    assert created_fanchart_traces[4]["name"] == "First Legendgroup"
    assert created_fanchart_traces[4].get("fill", None) is None
    assert created_fanchart_traces[4]["hovertemplate"] == "(%{x}, %{y})<br>Mean"
    assert np.array_equal(created_fanchart_traces[4]["y"], np.array([1.0, 1.5]))
    assert created_fanchart_traces[4]["x"] == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
    ]


def test_create_vector_fanchart_traces_subset_fanchart_options() -> None:
    created_fanchart_traces = create_vector_fanchart_traces(
        INPUT_VECTOR_STATISTICS_DF,
        fanchart_options=[
            FanchartOptions.MEAN,
            FanchartOptions.P10_P90,
        ],
        hex_color="#2b00ff",
        legend_group="Second Legendgroup",
        line_shape="linear",
        show_legend=True,
    )

    # Verify number of trace dicts in list
    assert len(created_fanchart_traces) == 3

    # Verify P90
    assert created_fanchart_traces[0]["name"] == "Second Legendgroup"
    assert created_fanchart_traces[0].get("fill", None) is None
    assert created_fanchart_traces[0]["hovertemplate"] == "(%{x}, %{y})<br>P90"
    assert np.array_equal(created_fanchart_traces[0]["y"], np.array([5.0, 5.5]))
    assert created_fanchart_traces[0]["x"] == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
    ]

    # Verify P10
    assert created_fanchart_traces[1]["name"] == "Second Legendgroup"
    assert created_fanchart_traces[1].get("fill", None) == "tonexty"
    assert created_fanchart_traces[1]["hovertemplate"] == "(%{x}, %{y})<br>P10"
    assert np.array_equal(created_fanchart_traces[1]["y"], np.array([4.0, 4.5]))
    assert created_fanchart_traces[1]["x"] == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
    ]

    # Verify Mean
    assert created_fanchart_traces[2]["name"] == "Second Legendgroup"
    assert created_fanchart_traces[2].get("fill", None) is None
    assert created_fanchart_traces[2]["hovertemplate"] == "(%{x}, %{y})<br>Mean"
    assert np.array_equal(created_fanchart_traces[2]["y"], np.array([1.0, 1.5]))
    assert created_fanchart_traces[2]["x"] == [
        datetime.datetime(2020, 1, 1),
        datetime.datetime(2020, 1, 2),
    ]


def test_create_vector_statistics_traces_all_statistics_options() -> None:
    created_statistics_traces = create_vector_statistics_traces(
        INPUT_VECTOR_STATISTICS_DF,
        statistics_options=[
            StatisticsOptions.MEAN,
            StatisticsOptions.MIN,
            StatisticsOptions.MAX,
            StatisticsOptions.P10,
            StatisticsOptions.P50,
            StatisticsOptions.P90,
        ],
        color="green",
        legend_group="Third Legendgroup",
        line_shape="linear",
    )

    # Verify number of trace dicts in list
    assert len(created_statistics_traces) == 6

    # Verify Min
    assert created_statistics_traces[0]["name"] == "Third Legendgroup"
    assert created_statistics_traces[0]["hovertemplate"] == "(%{x}, %{y})<br>Minimum"
    assert np.array_equal(created_statistics_traces[0]["y"], np.array([2.0, 2.5]))
    assert np.array_equal(
        created_statistics_traces[0]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )

    # Verify P90
    assert created_statistics_traces[1]["name"] == "Third Legendgroup"
    assert created_statistics_traces[1]["hovertemplate"] == "(%{x}, %{y})<br>P90"
    assert np.array_equal(created_statistics_traces[1]["y"], np.array([5.0, 5.5]))
    assert np.array_equal(
        created_statistics_traces[1]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )

    # Verify P50
    assert created_statistics_traces[2]["name"] == "Third Legendgroup"
    assert created_statistics_traces[2]["hovertemplate"] == "(%{x}, %{y})<br>P50"
    assert np.array_equal(created_statistics_traces[2]["y"], np.array([6.0, 6.5]))
    assert np.array_equal(
        created_statistics_traces[2]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )

    # Verify P10
    assert created_statistics_traces[3]["name"] == "Third Legendgroup"
    assert created_statistics_traces[3]["hovertemplate"] == "(%{x}, %{y})<br>P10"
    assert np.array_equal(created_statistics_traces[3]["y"], np.array([4.0, 4.5]))
    assert np.array_equal(
        created_statistics_traces[3]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )

    # Verify Max
    assert created_statistics_traces[4]["name"] == "Third Legendgroup"
    assert created_statistics_traces[4]["hovertemplate"] == "(%{x}, %{y})<br>Maximum"
    assert np.array_equal(created_statistics_traces[4]["y"], np.array([3.0, 3.5]))
    assert np.array_equal(
        created_statistics_traces[4]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )

    # Verify Mean
    assert created_statistics_traces[5]["name"] == "Third Legendgroup"
    assert created_statistics_traces[5]["hovertemplate"] == "(%{x}, %{y})<br>Mean"
    assert np.array_equal(created_statistics_traces[5]["y"], np.array([1.0, 1.5]))
    assert np.array_equal(
        created_statistics_traces[5]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )


def test_create_vector_statistics_traces_subset_statistics_options() -> None:
    created_statistics_traces = create_vector_statistics_traces(
        INPUT_VECTOR_STATISTICS_DF,
        statistics_options=[
            StatisticsOptions.MEAN,
            StatisticsOptions.MIN,
            StatisticsOptions.P10,
        ],
        color="green",
        legend_group="Fourth Legendgroup",
        line_shape="linear",
    )

    # Verify number of trace dicts in list
    assert len(created_statistics_traces) == 3

    # Verify P50
    assert created_statistics_traces[0]["name"] == "Fourth Legendgroup"
    assert created_statistics_traces[0]["hovertemplate"] == "(%{x}, %{y})<br>Minimum"
    assert np.array_equal(created_statistics_traces[0]["y"], np.array([2.0, 2.5]))
    assert np.array_equal(
        created_statistics_traces[0]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )

    # Verify P10
    assert created_statistics_traces[1]["name"] == "Fourth Legendgroup"
    assert created_statistics_traces[1]["hovertemplate"] == "(%{x}, %{y})<br>P10"
    assert np.array_equal(created_statistics_traces[1]["y"], np.array([4.0, 4.5]))
    assert np.array_equal(
        created_statistics_traces[1]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )

    # Verify Mean
    assert created_statistics_traces[2]["name"] == "Fourth Legendgroup"
    assert created_statistics_traces[2]["hovertemplate"] == "(%{x}, %{y})<br>Mean"
    assert np.array_equal(created_statistics_traces[2]["y"], np.array([1.0, 1.5]))
    assert np.array_equal(
        created_statistics_traces[2]["x"],
        np.array(
            [
                datetime.datetime(2020, 1, 1),
                datetime.datetime(2020, 1, 2),
            ]
        ),
    )

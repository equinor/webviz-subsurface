import copy
import datetime

import numpy as np
import pandas as pd
import pytest

from webviz_subsurface._providers import Frequency
from webviz_subsurface.plugins._simulation_time_series.utils.create_vector_traces_utils import (
    create_history_vector_trace,
    create_vector_observation_traces,
    create_vector_realization_traces,
    render_hovertemplate,
)


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
    vector_df["DATE"] = pd.Series(vector_df["DATE"].dt.to_pydatetime(), dtype=object)

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
            "line": {"width": 1, "shape": "linear"},
            "x": [datetime.datetime(2020, 1, 1), datetime.datetime(2020, 2, 1)],
            "y": [1.0, 2.0],
            "hovertemplate": "Test hovertemplate Realization: 1, Ensemble: Test ensemble",
            "name": "Test group",
            "legendgroup": "Test group",
            "marker": {"color": "red"},
            "legendrank": 2,
            "showlegend": True,
        },
        {
            "line": {"width": 1, "shape": "linear"},
            "x": [datetime.datetime(2031, 5, 10), datetime.datetime(2031, 6, 10)],
            "y": [5.0, 6.0],
            "hovertemplate": "Test hovertemplate Realization: 2, Ensemble: Test ensemble",
            "name": "Test group",
            "legendgroup": "Test group",
            "marker": {"color": "red"},
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
        "line": {"shape": "linear"},
        "x": input_samples,
        "y": input_history_data,
        "hovertext": "History: Test hist vector",
        "hoverinfo": "y+x+text",
        "name": "History",
        "marker": {"color": "green"},
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

    # Test interval/average vector names
    assert template_daily == render_hovertemplate("AVG_a", Frequency.DAILY)
    assert template_weekly == render_hovertemplate("AVG_a", Frequency.WEEKLY)
    assert template_monthly == render_hovertemplate("AVG_a", Frequency.MONTHLY)
    assert template_quarterly == render_hovertemplate("AVG_a", Frequency.QUARTERLY)
    assert template_yearly == render_hovertemplate("AVG_a", Frequency.YEARLY)
    assert template_default == render_hovertemplate("AVG_a", None)

    # Test other vector names
    assert template_default == render_hovertemplate("Vector_a", Frequency.DAILY)
    assert template_default == render_hovertemplate("Vector_a", Frequency.WEEKLY)
    assert template_default == render_hovertemplate("Vector_a", Frequency.MONTHLY)
    assert template_default == render_hovertemplate("Vector_a", Frequency.QUARTERLY)
    assert template_default == render_hovertemplate("Vector_a", Frequency.YEARLY)
    assert template_default == render_hovertemplate("Vector_a", None)

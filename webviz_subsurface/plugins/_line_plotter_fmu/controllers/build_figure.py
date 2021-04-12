from typing import List, Callable, Tuple, Union, Optional
import json

import numpy as np
import pandas as pd
import dash
from dash.dependencies import Input, Output, ALL

from webviz_config.common_cache import CACHE

from webviz_subsurface._models import (
    EnsembleTableModelSet,
    ObservationModel,
    ParametersModel,
)
from ..figures.plotly_line_plot import PlotlyLinePlot


def build_figure(
    app: dash.Dash,
    get_uuid: Callable,
    tablemodel: EnsembleTableModelSet,
    observationmodel: ObservationModel,
    parametermodel: ParametersModel,
) -> None:
    @app.callback(
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "plotly_data"}, "data"
        ),
        Output(
            {"id": get_uuid("clientside"), "plotly_attribute": "initial_layout"}, "data"
        ),
        Input(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "x",
                "source": "table",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "y",
                "source": "table",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "ensemble",
                "source": "table",
            },
            "value",
        ),
        Input(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "parameter",
                "source": "parameter",
            },
            "value",
        ),
        Input(get_uuid("traces"), "value"),
        Input(
            {
                "id": get_uuid("clientside"),
                "attribute": "single_real",
            },
            "data",
        ),
        Input(get_uuid("graph"), "clickData"),
    )
    def _update_plot(
        x_column_name: str,
        y_column_name: str,
        ensemble_names: Union[List, str],
        parameter_name: str,
        traces: List,
        single_real_mode,
        click_data: Optional[None],
    ) -> Union[Tuple]:
        print("real", single_real_mode)
        print(click_data)

        if not ensemble_names:
            return [], dash.no_update
        ensemble_names = (
            [ensemble_names] if not isinstance(ensemble_names, list) else ensemble_names
        )
        df = merge_parameter_and_csv_data(
            tablemodel=tablemodel,
            parametermodel=parametermodel,
            ensemble_names=ensemble_names,
            table_column_names=[x_column_name, y_column_name],
            parameter_column_name=parameter_name,
        )
        active_x_value: str = click_data["points"][0]["x"] if click_data else None
        figure = PlotlyLinePlot(active_x_value=active_x_value)
        if "Realizations" in traces:
            figure.add_realization_traces(
                df,
                x_column_name,
                y_column_name,
                color_column=parameter_name,
                realization_slider=single_real_mode,
            )
            traces.remove("Realizations")

        if traces:
            stat_df = calc_series_statistics(df, [y_column_name], x_column_name)
            figure.add_statistical_lines(stat_df, x_column_name, y_column_name, traces)
        if observationmodel is not None:
            observations = observationmodel.get_observations_for_attribute(
                attribute=y_column_name, value=x_column_name
            )
            if observations is not None:
                figure.add_observations(
                    observations=observations, x_value=x_column_name
                )

        fig = figure.get_figure()
        return fig["data"], fig["layout"]


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calc_series_statistics(
    df: pd.DataFrame, vectors: list, refaxis: str = "DATE"
) -> pd.DataFrame:
    """Calculate statistics for given vectors over the ensembles
    refaxis is used if another column than DATE should be used to groupby.
    """
    # Invert p10 and p90 due to oil industry convention.
    def p10(x: List[float]) -> List[float]:
        return np.nanpercentile(x, q=90)

    def p90(x: List[float]) -> List[float]:
        return np.nanpercentile(x, q=10)

    # Calculate statistics, ignoring NaNs.
    stat_df = (
        df[["ENSEMBLE", refaxis] + vectors]
        .groupby(["ENSEMBLE", refaxis])
        .agg([np.nanmean, np.nanmin, np.nanmax, p10, p90])
        .reset_index()  # level=["label", refaxis], col_level=0)
    )
    # Rename nanmin, nanmax and nanmean to min, max and mean.
    col_stat_label_map = {
        "nanmin": "min",
        "nanmax": "max",
        "nanmean": "mean",
        "p10": "high_p10",
        "p90": "low_p90",
    }
    stat_df.rename(columns=col_stat_label_map, level=1, inplace=True)

    return stat_df


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def merge_parameter_and_csv_data(
    tablemodel: EnsembleTableModelSet,
    parametermodel: ParametersModel,
    ensemble_names: List,
    table_column_names: List,
    parameter_column_name: str,
) -> pd.DataFrame:
    dfs = []
    # Retrieve table data for each ensemble and aggregate
    for ens in ensemble_names:

        table = tablemodel.ensemble(ens)
        columns = table_column_names
        columns = [col for col in columns if col != "REAL"]
        col_df = table.get_column_data(columns)
        col_df["ENSEMBLE"] = ens
        dfs.append(col_df)
    data_df = pd.concat(dfs)
    dfs = []
    # Retrieve parameter data for each ensemble and aggregate
    for ens in ensemble_names:
        table = parametermodel.ensemble(ens)
        columns = [parameter_column_name]
        print(columns)
        columns = [col for col in columns if col != "REAL"]
        col_df = table.get_column_data(columns)
        col_df["ENSEMBLE"] = ens
        dfs.append(col_df)
    parameter_df = pd.concat(dfs)

    return pd.merge(data_df, parameter_df, on=["ENSEMBLE", "REAL"])

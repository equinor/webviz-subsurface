from typing import List, Callable, Tuple, Union, Optional, Dict

import numpy as np
import pandas as pd
import dash
from dash.dependencies import Input, Output
from webviz_config.common_cache import CACHE

from webviz_subsurface._models import ObservationModel
from webviz_subsurface._providers import EnsembleTableProviderSet
from ..figures.plotly_line_plot import PlotlyLinePlot


def build_figure(
    app: dash.Dash,
    get_uuid: Callable,
    tableproviders: EnsembleTableProviderSet,
    observationmodel: Optional[ObservationModel],
    parameterproviders: EnsembleTableProviderSet,
    colors: Dict,
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
        Input(get_uuid("observations"), "value"),
        Input(get_uuid("highlight-realizations"), "value"),
        Input({"id": get_uuid("parameter-filter"), "type": "data-store"}, "data"),
    )
    # pylint: disable=too-many-locals
    def _update_plot(
        x_column_name: str,
        y_column_name: str,
        ensemble_names: Union[List, str],
        parameter_name: str,
        traces: List,
        show_obs: List,
        highlight_realizations: List[int],
        parameter_filter: Dict,
    ) -> Union[Tuple]:
        highlight_realizations = (
            [int(real) for real in highlight_realizations]
            if highlight_realizations
            else []
        )
        if not ensemble_names:
            return [], dash.no_update
        ensemble_names = (
            [ensemble_names] if not isinstance(ensemble_names, list) else ensemble_names
        )
        real_filter = {} if parameter_filter is None else parameter_filter

        csv_dframe = get_table_data(
            tableproviders=tableproviders,
            ensemble_names=ensemble_names,
            table_column_names=[x_column_name, y_column_name],
            realization_filter=real_filter,
        )
        if parameter_name is not None:
            parameter_dframe = get_table_data(
                tableproviders=parameterproviders,
                ensemble_names=ensemble_names,
                table_column_names=[parameter_name],
                realization_filter=real_filter,
            )
            df = pd.merge(csv_dframe, parameter_dframe, on=["ENSEMBLE", "REAL"])
        else:
            df = csv_dframe
        if df.empty:
            return [], {"title": "No data found with current filter"}
        figure = PlotlyLinePlot(
            xaxis_title=x_column_name, yaxis_title=y_column_name, ensemble_colors=colors
        )
        if "Realizations" in traces:
            figure.add_realization_traces(
                df,
                x_column_name,
                y_column_name,
                color_column=parameter_name,
                highlight_reals=highlight_realizations,
                opacity=0.5 if len(traces) > 1 else None,
            )
            traces.remove("Realizations")

        if traces:
            stat_df = calc_series_statistics(df, [y_column_name], x_column_name)
            figure.add_statistical_lines(stat_df, x_column_name, y_column_name, traces)
        if show_obs and observationmodel is not None:

            observations = observationmodel.get_observations_for_attribute(
                attribute=y_column_name, value=x_column_name
            )
            if observations is not None:
                figure.add_observations(
                    observations=observations, x_value=x_column_name
                )

        fig = figure.get_figure()
        data = fig["data"]
        layout = fig["layout"]
        return data, layout

    @app.callback(
        Output(get_uuid("highlight-realizations"), "value"),
        Input(get_uuid("clear-highlight-realizations"), "n_clicks"),
    )
    def _clear_real_highlight(_click: int) -> Optional[List]:
        return []


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
def get_table_data(
    tableproviders: EnsembleTableProviderSet,
    ensemble_names: List,
    table_column_names: List,
    realization_filter: Dict[str, List],
) -> pd.DataFrame:

    dfs = []
    for ens_name in ensemble_names:
        if not realization_filter.get(ens_name):
            dframe = pd.DataFrame(columns=["ENSEMBLE", "REAL"] + table_column_names)
        else:
            provider = tableproviders.ensemble_provider(ens_name)
            dframe = provider.get_column_data(
                table_column_names, realizations=realization_filter.get(ens_name)
            )
            dframe["ENSEMBLE"] = ens_name
        dfs.append(dframe)
    if len(dfs) > 0:
        return pd.concat(dfs)
    return pd.DataFrame()

from typing import Callable, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from dash import Dash, Input, Output, State, no_update
from dash.exceptions import PreventUpdate
from webviz_config.common_cache import CACHE

from webviz_subsurface._models import ObservationModel
from webviz_subsurface._providers import EnsembleTableProviderSet

from ..figures.plotly_line_plot import PlotlyLinePlot


def build_figure(
    app: Dash,
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
        Input(get_uuid("stored_x_value"), "data"),
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
        Input(get_uuid("mode"), "value"),
        Input({"id": get_uuid("parameter-filter"), "type": "data-store"}, "data"),
    )
    # pylint: disable=too-many-locals, too-many-arguments
    def _update_plot(
        x_column_name: str,
        y_column_name: str,
        ensemble_names: Union[List, str],
        parameter_name: str,
        traces: List,
        show_obs: List,
        highlight_realizations: List[int],
        mode: str,
        parameter_filter: Optional[Dict],
    ) -> Union[Tuple]:
        if not x_column_name:
            raise PreventUpdate
        highlight_realizations = (
            [int(real) for real in highlight_realizations]
            if highlight_realizations
            else []
        )
        if not ensemble_names:
            return [], no_update
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
                dframe=df,
                x_column=x_column_name,
                y_column=y_column_name,
                color_column=parameter_name,
                highlight_reals=highlight_realizations,
                opacity=0.5 if len(traces) > 1 else None,
                mode=mode,
            )
            traces.remove("Realizations")

        if traces:
            stat_df = calc_series_statistics(df, [y_column_name], x_column_name)
            figure.add_statistical_lines(
                dframe=stat_df,
                x_column=x_column_name,
                y_column=y_column_name,
                traces=traces,
                mode=mode,
            )
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
        if _click is not None:
            return []
        raise PreventUpdate

    @app.callback(
        Output(get_uuid("stored_x_value"), "data"),
        Output(get_uuid("traces"), "options"),
        Output(get_uuid("traces"), "value"),
        Output(get_uuid("statistics_warning"), "children"),
        Input(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "x",
                "source": "table",
            },
            "value",
        ),
        State(
            {
                "id": get_uuid("data_selectors"),
                "data_attribute": "ensemble",
                "source": "table",
            },
            "value",
        ),
        State(get_uuid("traces"), "value"),
        State({"id": get_uuid("parameter-filter"), "type": "data-store"}, "data"),
    )
    def _update_statistics_options(
        x_column_name: str,
        ensemble_names: List,
        current_values: List,
        parameter_filter: Optional[Dict],
    ) -> Tuple[str, List[Dict], List, str]:
        """Deactivate statistics calculations if x-axis is varying between realizations"""
        if not ensemble_names:
            raise PreventUpdate
        real_filter = {} if parameter_filter is None else parameter_filter
        csv_dframe = get_table_data(
            tableproviders=tableproviders,
            ensemble_names=ensemble_names,
            table_column_names=[x_column_name],
            realization_filter=real_filter,
        )
        for _ens, ens_df in csv_dframe.groupby("ENSEMBLE"):
            realizations = list(ens_df["REAL"].unique())
            equal_x = all(
                (
                    np.all(
                        ens_df.loc[ens_df["REAL"] == real][x_column_name].values
                        == ens_df.loc[ens_df["REAL"] == realizations[0]][
                            x_column_name
                        ].values
                    )
                    for real in realizations
                )
            )
            if not equal_x:
                return (
                    x_column_name,
                    [
                        {"label": "Realizations", "value": "Realizations"},
                        {
                            "label": "Mean",
                            "value": "Mean",
                            "disabled": True,
                        },
                        {
                            "label": "P10/P90",
                            "value": "P10/P90",
                            "disabled": True,
                        },
                        {
                            "label": "Low/High",
                            "value": "Low/High",
                            "disabled": True,
                        },
                    ],
                    ["Realizations"] if "Realizations" in current_values else [],
                    "⚠️ Cannot calculate statistics as x-axis varies between realizations",
                )
        return (
            x_column_name,
            [
                {"label": val, "value": val}
                for val in ["Realizations", "Mean", "P10/P90", "Low/High"]
            ],
            current_values,
            "",
        )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def calc_series_statistics(
    df: pd.DataFrame, vectors: list, refaxis: str = "DATE"
) -> pd.DataFrame:
    """Calculate statistics for given vectors over the ensembles
    refaxis is used if another column than DATE should be used to groupby.
    """
    # Invert p10 and p90 due to oil industry convention.
    def p10(x: List[float]) -> np.floating:
        return np.nanpercentile(x, q=90)

    def p90(x: List[float]) -> np.floating:
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

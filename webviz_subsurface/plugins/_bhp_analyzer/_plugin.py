from pathlib import Path
from typing import Dict, List, Union

import numpy as np
import pandas as pd
import webviz_core_components as wcc
from dash import Dash, Input, Output, html
from webviz_config import WebvizPluginABC, WebvizSettings
from webviz_config.common_cache import CACHE

from webviz_subsurface._providers import EnsembleSummaryProvider

from ..._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    get_fanchart_traces,
)
from ..._utils.unique_theming import unique_colors
from .._simulation_time_series.types.provider_set import (
    create_lazy_provider_set_from_paths,
)
from ._plugin_ids import PluginIds
from .shared_settings import Filter


class BhpAnalyzer(WebvizPluginABC):
    """QC simulated bottom hole pressures (BHP) from reservoir simulations.

    Can be used to check if your simulated BHPs are in a realistic range.
    E.g. check if your simulated bottom hole pressures are very low in producers,
    or very high injectors.
    ---

    * **`ensembles`:** Which ensembles in `shared_settings` to visualize.
    * **`rel_file_pattern`:** path to `.arrow` files with summary data.
    ---
    Data is read directly from the arrow files with the raw frequency (not resampled).
    Resampling and csvs are not supported to avoid potential of interpolation, which
    might cover extreme BHP values.

    """

    def __init__(
        self,
        app: Dash,
        webviz_settings: WebvizSettings,
        ensembles: list,
        rel_file_pattern: str = "share/results/unsmry/*.arrow",
        wells: List[str] = None,
    ):
        super().__init__()

        self.ens_paths: Dict[str, Path] = {
            ensemble_name: webviz_settings.shared_settings["scratch_ensembles"][
                ensemble_name
            ]
            for ensemble_name in ensembles
        }

        self._input_provider_set = create_lazy_provider_set_from_paths(
            self.ens_paths,
            rel_file_pattern,
        )

        dfs = []
        column_keys = {}
        for ens_name in ensembles:
            ens_provider = self._input_provider_set.provider(ens_name)
            column_keys[ens_name] = _get_wbhp_vectors(ens_provider, wells)
            df = ens_provider.get_vectors_df(column_keys[ens_name], None)
            df["ENSEMBLE"] = ens_name
            dfs.append(df.loc[:, (df != 0).any(axis=0)])  # remove zero-columns

        self.smry = pd.concat(dfs)
        self.theme = webviz_settings.theme
        self.set_callbacks(app)

        self.add_store(PluginIds.Stores.SELECTED_ENSEMBLE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.SELECTED_PLOT_TYPE, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.SELECTED_SORT_BY, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.SELECTED_ASCENDING_DESCENDING, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.SELECTED_MAX_NUMBER_OF_WELLS, WebvizPluginABC.StorageType.SESSION)
        self.add_store(PluginIds.Stores.SELECTED_WELLS, WebvizPluginABC.StorageType.SESSION)

        self.add_shared_settings_group(Filter(self.smry), PluginIds.SharedSettings.FILTER)

    @property
    def tour_steps(self) -> List[dict]:
        return [
            {
                "id": self.uuid("layout"),
                "content": (
                    "Dashboard for BHP QC:"
                    "Check that simulated bottom hole pressures are realistic."
                ),
            },
            {"id": self.uuid("ensemble"), "content": "Select ensemble to QC."},
            {
                "id": self.uuid("sort_by"),
                "content": "Sort wells left to right according to this value.",
            },
            {
                "id": self.uuid("n_wells"),
                "content": (
                    "Show max selected number of top ranked wells after sorting and filtering."
                ),
            },
            {"id": self.uuid("wells"), "content": "Filter wells."},
        ]

    @property
    def ensembles(self) -> List[str]:
        return list(self.smry["ENSEMBLE"].unique())

    @property
    def wells(self) -> List[set]:
        return sorted(
            list(set(col[5:] for col in self.smry.columns if col.startswith("WBHP:")))
        )

    @property
    def ens_colors(self) -> dict:
        return unique_colors(self.ensembles, self.theme)

    @property
    def label_map(self) -> Dict[str, str]:
        return {
            "Mean": "mean",
            "Count (data points)": "count",
            "Stddev": "std",
            "Minimum": "min",
            "Maximum": "max",
            "P10 (high)": "high_p10",
            "P50": "p50",
            "P90 (low)": "low_p90",
        }

    @property
    def layout(self) -> wcc.FlexBox:
        return wcc.FlexBox(
            id=self.uuid("layout"),
            children=[
                wcc.Frame(
                    color="white",
                    highlight=False,
                    style={"flex": 6, "height": "65vh"},
                    children=[
                        wcc.Graph(id=self.uuid("graph"), style={"height": "60vh"}),
                    ],
                ),
            ],
        )

    def set_callbacks(self, app: Dash) -> None:
        @app.callback(
            Output(self.uuid("graph"), "figure"),
            Input(self.uuid("ensemble"), "value"),
            Input(self.uuid("plot_type"), "value"),
            Input(self.uuid("n_wells"), "value"),
            Input(self.uuid("wells"), "value"),
            Input(self.uuid("sort_by"), "value"),
            Input(self.uuid("stat_bars"), "value"),
            Input(self.uuid("ascending"), "value"),
        )
        def _update_graph(
            ensemble: str,
            plot_type: str,
            n_wells: int,
            wells: Union[str, List[str]],
            sort_by: str,
            stat_bars: Union[str, List[str]],
            ascending: bool,
        ) -> dict:
            wells = wells if isinstance(wells, list) else [wells]
            stat_bars = stat_bars if isinstance(stat_bars, list) else [stat_bars]
            df = filter_df(df=self.smry, ensemble=ensemble, wells=wells)
            stat_df = (
                calc_statistics(df)
                .sort_values(sort_by, ascending=ascending)
                .iloc[0:n_wells, :]
            )
            traces = []
            if plot_type == "Fan chart":
                traces.extend(
                    _get_fanchart_traces(
                        ens_stat_df=stat_df,
                        color=self.ens_colors[ensemble],
                        legend_group=ensemble,
                    )
                )
            elif plot_type in ["Bar chart", "Line chart"]:
                for stat in stat_bars:
                    yaxis = "y2" if stat == "count" else "y"

                    if plot_type == "Bar chart":

                        traces.append(
                            {
                                "x": [vec[5:] for vec in stat_df.index],  # strip WBHP:
                                "y": stat_df[stat],
                                "name": [
                                    key
                                    for key, value in self.label_map.items()
                                    if value == stat
                                ][0],
                                "yaxis": yaxis,
                                "type": "bar",
                                "offsetgroup": stat,
                                "showlegend": True,
                            }
                        )
                    elif plot_type == "Line chart":
                        traces.append(
                            {
                                "x": [vec[5:] for vec in stat_df.index],  # strip WBHP:
                                "y": stat_df[stat],
                                "name": [
                                    key
                                    for key, value in self.label_map.items()
                                    if value == stat
                                ][0],
                                "yaxis": yaxis,
                                "type": "line",
                                "offsetgroup": stat,
                                "showlegend": True,
                            }
                        )
                    else:
                        raise ValueError("Invalid plot type.")

            layout = self.theme.create_themed_layout(
                {
                    "yaxis": {
                        "side": "left",
                        "title": "Bottom hole pressure",
                        "showgrid": True,
                    },
                    "yaxis2": {
                        "side": "right",
                        "overlaying": "y",
                        "title": "Count (data points)",
                        "showgrid": False,
                    },
                    "xaxis": {"showgrid": False},
                    "barmode": "group",
                    "legend": {"x": 1.05},
                }
            )
            return {"data": traces, "layout": layout}

        @app.callback(
            Output(self.uuid("select_stat"), "style"),
            Input(self.uuid("plot_type"), "value"),
        )
        def _update_stat_selector(plot_type: str) -> dict:
            return (
                {"display": "none"}
                if plot_type == "Fan chart"
                else {"display": "block"}
            )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def filter_df(df: pd.DataFrame, ensemble: str, wells: List[str]) -> pd.DataFrame:
    """Filter dataframe for current ensembles and wells.
    Replacing zeroes (well not open) with np.NaN to not be accounted for
    in statistics.
    """
    columns = ["ENSEMBLE"] + [f"WBHP:{well}" for well in wells]
    return df.loc[df["ENSEMBLE"] == ensemble][columns].replace(0, np.NaN)


def calc_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate statistics for given vectors over the ensembles
    refaxis is used if another column than DATE should be used to groupby.
    """
    # Invert p10 and p90 due to oil industry convention.
    def p10(x: np.ndarray) -> float:
        return np.nanpercentile(x, q=90)

    def p50(x: np.ndarray) -> float:
        return np.nanpercentile(x, q=50)

    def p90(x: np.ndarray) -> float:
        return np.nanpercentile(x, q=10)

    # Calculate statistics, ignoring NaNs.
    stat_df = (
        df.groupby("ENSEMBLE")
        .agg([np.nanmean, "count", np.nanstd, np.nanmin, np.nanmax, p10, p50, p90])
        .reset_index(drop=True, level="ENSEMBLE")
    )
    # Rename nanmin, nanmax and nanmean to min, max and mean.
    col_stat_label_map = {
        "nanmin": "min",
        "nanmax": "max",
        "nanmean": "mean",
        "nanstd": "std",
        "p10": "high_p10",
        "p90": "low_p90",
    }
    stat_df.rename(columns=col_stat_label_map, level=1, inplace=True)
    stat_df = stat_df.transpose().unstack()
    stat_df.columns = stat_df.columns.get_level_values(1)  # Remove 0 index column
    return stat_df


def _get_fanchart_traces(
    ens_stat_df: pd.DataFrame,
    color: str,
    legend_group: str,
) -> List[dict]:
    """Renders a fanchart for an ensemble vector"""

    x = [vec[5:] for vec in ens_stat_df.index]

    data = FanchartData(
        samples=x,
        low_high=LowHighData(
            low_data=ens_stat_df["low_p90"].values,
            low_name="P90 (low)",
            high_data=ens_stat_df["high_p10"].values,
            high_name="P10 (high)",
        ),
        minimum_maximum=MinMaxData(
            minimum=ens_stat_df["min"].values,
            maximum=ens_stat_df["max"].values,
        ),
        free_line=FreeLineData("Mean", ens_stat_df["mean"].values),
    )

    return get_fanchart_traces(
        data=data,
        hex_color=color,
        legend_group=legend_group,
        hovermode="x",
    )


# ---------------------------
def _get_wbhp_vectors(
    ens_provider: EnsembleSummaryProvider,
    wells: List[str] = None,
) -> list:
    """Return list of WBHP vectors. If wells arg is None, return for all wells."""

    if wells is not None:
        return [f"WBHP:{well}" for well in wells]

    wbhp_vectors = [
        vector for vector in ens_provider.vector_names() if vector.startswith("WBHP:")
    ]
    if not wbhp_vectors:
        raise RuntimeError("No WBHP vectors found.")

    return wbhp_vectors

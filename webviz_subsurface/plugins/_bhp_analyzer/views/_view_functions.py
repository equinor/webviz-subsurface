from typing import List, Dict

from webviz_config.common_cache import CACHE
from dash.development.base_component import Component
from dash import callback, Input, Output
import numpy as np
import pandas as pd
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC
import webviz_core_components as wcc

from ...._utils.fanchart_plotting import (
    FanchartData,
    FreeLineData,
    LowHighData,
    MinMaxData,
    get_fanchart_traces,
)
from .._plugin_ids import PluginIds

#ADD SELECT STATISTICS
class BarLineSettings(SettingsGroupABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        SELECT_STATISTICS = "select-statistics"

    def __init__(self) -> None:
        super().__init__("View Settings")

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

    def layout(self) -> List[Component]:
        return [
            wcc.SelectWithLabel(
                                    label="Select statistics",
                                    id=self.register_component_unique_id(BarLineSettings.Ids.SELECT_STATISTICS),
                                    options=[
                                        {"label": key, "value": value}
                                        for key, value in self.label_map.items()
                                    ],
                                    size=8,
                                    value=["min", "low_p90", "mean", "high_p10", "max"],
            ),
        ]
"""    
    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_STATISTICS), "data"
            ),
            Input(
                self.component_unique_id(BarLineSettings.Ids.SELECT_STATISTICS).to_string(), "value"
            ),
        )
        def _set_select_statistics(selected_statistics: List[str]) -> List[str]:
            return selected_statistics
"""

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
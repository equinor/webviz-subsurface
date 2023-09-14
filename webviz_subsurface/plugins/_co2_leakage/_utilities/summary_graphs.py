import dataclasses
from typing import Iterable, List, Union

import numpy as np
import pandas as pd
import plotly.colors
import plotly.graph_objects as go

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
)


# pylint: disable=too-many-locals
def generate_summary_figure(
    table_provider_unsmry: EnsembleTableProvider,
    realizations_unsmry: List[int],
    scale: Union[Co2MassScale, Co2VolumeScale],
    table_provider_containment: EnsembleTableProvider,
    realizations_containment: List[int],
) -> go.Figure:
    columns_unsmry = _column_subset_unsmry(table_provider_unsmry)
    columns_containment = _column_subset_containment(table_provider_containment)
    df_unsmry = _read_dataframe(
        table_provider_unsmry, realizations_unsmry, columns_unsmry, scale
    )
    df_containment = _read_dataframe_containment(
        table_provider_containment, realizations_containment, columns_containment, scale
    )
    fig = go.Figure()
    showlegend = True

    r_min = min(df_unsmry.REAL)
    unsmry_last_total = df_unsmry[df_unsmry.REAL == r_min]["total"].iloc[-1]
    unsmry_last_mobile = df_unsmry[df_unsmry.REAL == r_min][columns_unsmry.mobile].iloc[
        -1
    ]
    unsmry_last_dissolved = df_unsmry[df_unsmry.REAL == r_min][
        columns_unsmry.dissolved
    ].iloc[-1]
    containment_last_total = df_containment[df_containment.REAL == r_min]["total"].iloc[
        -1
    ]
    containment_last_mobile = df_containment[df_containment.REAL == r_min][
        columns_containment.mobile
    ].iloc[-1]
    containment_last_dissolved = df_containment[df_containment.REAL == r_min][
        columns_containment.dissolved
    ].iloc[-1]
    last_total_err_percentage = (
        100.0 * abs(containment_last_total - unsmry_last_total) / unsmry_last_total
    )
    last_mobile_err_percentage = (
        100.0 * abs(containment_last_mobile - unsmry_last_mobile) / unsmry_last_mobile
    )
    last_dissolved_err_percentage = (
        100.0
        * abs(containment_last_dissolved - unsmry_last_dissolved)
        / unsmry_last_dissolved
    )
    last_total_err_percentage = np.round(last_total_err_percentage, 2)
    last_mobile_err_percentage = np.round(last_mobile_err_percentage, 2)
    last_dissolved_err_percentage = np.round(last_dissolved_err_percentage, 2)

    for _, sub_df in df_unsmry.groupby("realization"):
        colors = plotly.colors.qualitative.Plotly
        fig.add_scatter(
            x=sub_df[columns_unsmry.time],
            y=sub_df["total"],
            name="UNSMRY",
            legendgroup="group_1",
            legendgrouptitle_text=f"Total ({last_total_err_percentage} %)",
            showlegend=showlegend,
            marker_color=colors[3],
        )
        fig.add_scatter(
            x=sub_df[columns_unsmry.time],
            y=sub_df[columns_unsmry.mobile],
            name=f"UNSMRY ({columns_unsmry.mobile})",
            legendgroup="group_2",
            legendgrouptitle_text=f"Mobile ({last_mobile_err_percentage} %)",
            showlegend=showlegend,
            marker_color=colors[2],
        )
        fig.add_scatter(
            x=sub_df[columns_unsmry.time],
            y=sub_df[columns_unsmry.dissolved],
            name=f"UNSMRY ({columns_unsmry.dissolved})",
            legendgroup="group_3",
            legendgrouptitle_text=f"Dissolved ({last_dissolved_err_percentage} %)",
            showlegend=showlegend,
            marker_color=colors[0],
        )
        fig.add_scatter(
            x=sub_df[columns_unsmry.time],
            y=sub_df[columns_unsmry.trapped],
            name=f"UNSMRY ({columns_unsmry.trapped})",
            legendgroup="group_4",
            legendgrouptitle_text="Trapped",
            showlegend=showlegend,
            marker_color=colors[1],
        )
        showlegend = False
    showlegend = True
    for _, sub_df in df_containment.groupby("realization"):
        colors = plotly.colors.qualitative.Plotly
        fig.add_scatter(
            x=sub_df[columns_containment.time],
            y=sub_df["total"],
            name="Containment script",
            legendgroup="group_1",
            showlegend=showlegend,
            marker_color=colors[3],
            line_dash="dash",
        )
        fig.add_scatter(
            x=sub_df[columns_containment.time],
            y=sub_df[columns_containment.mobile],
            name=f"Containment script ({columns_containment.mobile})",
            legendgroup="group_2",
            showlegend=showlegend,
            marker_color=colors[2],
            line_dash="dash",
        )
        fig.add_scatter(
            x=sub_df[columns_containment.time],
            y=sub_df[columns_containment.dissolved],
            name=f"Containment script ({columns_containment.dissolved})",
            legendgroup="group_3",
            showlegend=showlegend,
            marker_color=colors[0],
            line_dash="dash",
        )
        showlegend = False
    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = f"Amount CO2 [{scale.value}]"
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 10
    fig.layout.margin.t = 60
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10
    return fig


@dataclasses.dataclass
class _ColumnNames:
    time: str
    dissolved: str
    trapped: str
    mobile: str

    def values(self) -> Iterable[str]:
        return dataclasses.asdict(self).values()


@dataclasses.dataclass
class _ColumnNamesContainment:
    time: str
    dissolved: str
    mobile: str

    def values(self) -> Iterable[str]:
        return dataclasses.asdict(self).values()


def _read_dataframe(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    columns: _ColumnNames,
    co2_scale: Union[Co2MassScale, Co2VolumeScale],
) -> pd.DataFrame:
    full = pd.concat(
        [
            table_provider.get_column_data(list(columns.values()), [real]).assign(
                realization=real
            )
            for real in realizations
        ]
    )
    full["total"] = (
        full[columns.dissolved] + full[columns.trapped] + full[columns.mobile]
    )
    for col in [columns.dissolved, columns.trapped, columns.mobile, "total"]:
        if co2_scale == Co2MassScale.MTONS:
            full[col] = full[col] / 1e9
        elif co2_scale == Co2MassScale.NORMALIZE:
            full[col] = full[col] / full["total"].max()
    return full


def _read_dataframe_containment(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    columns: _ColumnNamesContainment,
    co2_scale: Union[Co2MassScale, Co2VolumeScale],
) -> pd.DataFrame:
    full = pd.concat(
        [
            table_provider.get_column_data(list(columns.values()), [real]).assign(
                realization=real
            )
            for real in realizations
        ]
    )
    full["total"] = full[columns.dissolved] + full[columns.mobile]
    for col in [columns.dissolved, columns.mobile, "total"]:
        if co2_scale == Co2MassScale.MTONS:
            full[col] = full[col] / 1e9
        elif co2_scale == Co2MassScale.NORMALIZE:
            full[col] = full[col] / full["total"].max()
    return full


def _column_subset_unsmry(table_provider: EnsembleTableProvider) -> _ColumnNames:
    existing = set(table_provider.column_names())
    assert "DATE" in existing
    # Try PFLOTRAN names
    col_names = _ColumnNames("DATE", "FGMDS", "FGMTR", "FGMGP")
    if set(col_names.values()).issubset(existing):
        return col_names
    # Try Eclipse names
    col_names = _ColumnNames("DATE", "FWCD", "FGCDI", "FGCDM")
    if set(col_names.values()).issubset(existing):
        return col_names
    raise KeyError(f"Could not find suitable data columns among: {', '.join(existing)}")


def _column_subset_containment(
    table_provider: EnsembleTableProvider,
) -> _ColumnNamesContainment:
    existing = set(table_provider.column_names())
    assert "date" in existing
    col_names = _ColumnNamesContainment("date", "total_aqueous", "total_gas")
    if set(col_names.values()).issubset(existing):
        return col_names
    raise KeyError(f"Could not find suitable data columns among: {', '.join(existing)}")

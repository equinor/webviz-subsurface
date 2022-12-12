import dataclasses
from typing import Iterable, List

import pandas as pd
import plotly.colors
import plotly.graph_objects as go

from webviz_subsurface._providers import EnsembleTableProvider
from webviz_subsurface.plugins._co2_leakage._utilities.generic import Co2Scale


def generate_summary_figure(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    scale: Co2Scale,
) -> go.Figure:
    columns = _column_subset(table_provider)
    df = _read_dataframe(table_provider, realizations, columns, scale)
    fig = go.Figure()
    showlegend = True
    for _, sub_df in df.groupby("realization"):
        colors = plotly.colors.qualitative.Plotly
        fig.add_scatter(
            x=sub_df[columns.time],
            y=sub_df[columns.dissolved],
            name=f"Dissolved ({columns.dissolved})",
            legendgroup="Dissolved",
            showlegend=showlegend,
            marker_color=colors[0],
        )
        fig.add_scatter(
            x=sub_df[columns.time],
            y=sub_df[columns.trapped],
            name=f"Trapped ({columns.trapped})",
            legendgroup="Trapped",
            showlegend=showlegend,
            marker_color=colors[1],
        )
        fig.add_scatter(
            x=sub_df[columns.time],
            y=sub_df[columns.mobile],
            name=f"Mobile ({columns.mobile})",
            legendgroup="Mobile",
            showlegend=showlegend,
            marker_color=colors[2],
        )
        fig.add_scatter(
            x=sub_df[columns.time],
            y=sub_df["total"],
            name="Total",
            legendgroup="Total",
            showlegend=showlegend,
            marker_color=colors[3],
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


def _read_dataframe(
    table_provider: EnsembleTableProvider,
    realizations: List[int],
    columns: _ColumnNames,
    co2_scale: Co2Scale,
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
        if co2_scale == Co2Scale.MTONS:
            full[col] = full[col] / 1e9
        elif co2_scale == Co2Scale.NORMALIZE:
            full[col] = full[col] / full["total"].max()
    return full


def _column_subset(table_provider: EnsembleTableProvider) -> _ColumnNames:
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

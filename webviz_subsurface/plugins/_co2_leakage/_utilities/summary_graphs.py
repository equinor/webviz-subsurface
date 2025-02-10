from typing import Union

import numpy as np
import plotly.colors
import plotly.graph_objects as go

from webviz_subsurface.plugins._co2_leakage._utilities.containment_data_provider import (
    ContainmentDataProvider,
)
from webviz_subsurface.plugins._co2_leakage._utilities.generic import (
    Co2MassScale,
    Co2VolumeScale,
)
from webviz_subsurface.plugins._co2_leakage._utilities.unsmry_data_provider import (
    UnsmryDataProvider,
)


# pylint: disable=too-many-locals
def generate_summary_figure(
    unsmry_provider: UnsmryDataProvider,
    scale: Union[Co2MassScale, Co2VolumeScale],
    containment_provider: ContainmentDataProvider,
) -> go.Figure:
    df_unsmry = unsmry_provider.extract(scale)
    df_containment = containment_provider.extract_condensed_dataframe(scale)

    # TODO: expose these directly from data providers?
    r_min = min(df_unsmry.REAL)
    unsmry_last_total = df_unsmry[df_unsmry.REAL == r_min][
        unsmry_provider.colname_total
    ].iloc[-1]
    unsmry_last_mobile = df_unsmry[df_unsmry.REAL == r_min][
        unsmry_provider.colname_mobile
    ].iloc[-1]
    unsmry_last_dissolved = df_unsmry[df_unsmry.REAL == r_min][
        unsmry_provider.colname_dissolved
    ].iloc[-1]

    containment_reference = df_containment[df_containment.REAL == r_min]
    containment_last_total = containment_reference[
        containment_reference["phase"] == "total"
    ]["amount"].iloc[-1]
    containment_last_mobile = containment_reference[
        containment_reference["phase"] == "free_gas"
    ]["amount"].iloc[-1]
    containment_last_dissolved = containment_reference[
        containment_reference["phase"] == "dissolved"
    ]["amount"].iloc[-1]
    # ---
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

    _colors = {
        "total": plotly.colors.qualitative.Plotly[3],
        "mobile": plotly.colors.qualitative.Plotly[2],
        "dissolved": plotly.colors.qualitative.Plotly[0],
        "trapped": plotly.colors.qualitative.Plotly[1],
    }

    fig = go.Figure()
    showlegend = True
    for _, sub_df in df_unsmry.groupby("realization"):
        fig.add_scatter(
            x=sub_df[unsmry_provider.colname_date],
            y=sub_df[unsmry_provider.colname_total],
            name="UNSMRY",
            legendgroup="total",
            legendgrouptitle_text=f"Total ({last_total_err_percentage} %)",
            showlegend=showlegend,
            marker_color=_colors["total"],
        )
        fig.add_scatter(
            x=sub_df[unsmry_provider.colname_date],
            y=sub_df[unsmry_provider.colname_mobile],
            name=f"UNSMRY ({unsmry_provider.colname_mobile})",
            legendgroup="mobile",
            legendgrouptitle_text=f"Mobile ({last_mobile_err_percentage} %)",
            showlegend=showlegend,
            marker_color=_colors["mobile"],
        )
        fig.add_scatter(
            x=sub_df[unsmry_provider.colname_date],
            y=sub_df[unsmry_provider.colname_dissolved],
            name=f"UNSMRY ({unsmry_provider.colname_dissolved})",
            legendgroup="dissolved",
            legendgrouptitle_text=f"Dissolved ({last_dissolved_err_percentage} %)",
            showlegend=showlegend,
            marker_color=_colors["dissolved"],
        )
        fig.add_scatter(
            x=sub_df[unsmry_provider.colname_date],
            y=sub_df[unsmry_provider.colname_trapped],
            name=f"UNSMRY ({unsmry_provider.colname_trapped})",
            legendgroup="trapped",
            legendgrouptitle_text="Trapped",
            showlegend=showlegend,
            marker_color=_colors["trapped"],
        )
        showlegend = False

    _col_names = {
        "total": "total",
        "free_gas": "mobile",
        "dissolved": "dissolved",
        "trapped_gas": "trapped",
    }

    first_real = None
    for (real, phase), sub_df in df_containment.groupby(["REAL", "phase"]):
        if first_real is None:
            first_real = real
        fig.add_scatter(
            x=sub_df["date"],
            y=sub_df["amount"],
            name=f"Containment script ({phase})",
            legendgroup=_col_names[phase],
            showlegend=bool(first_real == real),
            marker_color=_colors[_col_names[phase]],
            line_dash="dash",
        )

    fig.layout.xaxis.title = "Time"
    fig.layout.yaxis.title = f"Amount CO2 [{scale.value}]"
    fig.layout.paper_bgcolor = "rgba(0,0,0,0)"
    fig.layout.margin.b = 10
    fig.layout.margin.t = 60
    fig.layout.margin.l = 10
    fig.layout.margin.r = 10
    return fig

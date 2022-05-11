import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import webviz_core_components as wcc

from ..utils import make_dataframes as makedf

# Color scales
HEATMAP_COLOR = [
    # [0, "gold"],
    [0, "#FF5500"],
    [0.1, "red"],
    [0.3, "darkred"],
    [0.4, "dimgrey"],
    [0.45, "lightgrey"],
    [0.5, "WhiteSmoke"],
    [0.55, "lightgrey"],
    [0.6, "dimgrey"],
    [0.7, "darkblue"],
    [0.9, "blue"],
    [1, "#00AFFF"],
    # [1, "cyan"],
]

# -------------------------------
# pylint: disable = too-many-locals
def prod_misfit_plot(
    df_diff: pd.DataFrame,
    phases: list,
    colorby: str,
    sorting: str = None,
    figheight: int = 450,
    misfit_exponent: float = 1.0,
    normalize: bool = False,
) -> List[wcc.Graph]:
    """Create plot of misfit per realization. One plot per ensemble.
    Misfit is absolute value of |sim - obs|, weighted by obs_error"""

    logging.debug("--- Updating production misfit plot ---")

    if df_diff.empty:
        fig = px.bar(title="No data to plot for current selections.")
        return [wcc.Graph(figure=fig, style={"height": figheight})]

    figures, max_misfit, min_misfit = [], 0, 0

    for ens_name, ensdf in df_diff.groupby("ENSEMBLE"):

        df_misfit, plot_phases, color_phases = _calculate_misfits(
            phases,
            ensdf,
            normalize,
            misfit_exponent,
        )

        # caclulate min-max ranges from first ensemble
        if max_misfit == min_misfit == 0:
            for _, df_date in df_misfit.groupby("DATE"):
                max_misfit = max_misfit + df_date["TOTAL_MISFIT"].max()
                min_misfit = min_misfit + df_date["TOTAL_MISFIT"].min()

        fig = _create_fig_barplot(
            ens_name,
            df_misfit,
            colorby,
            plot_phases,
            color_phases,
            max_misfit,
            min_misfit,
            sorting,
        )

        figures.append(wcc.Graph(figure=fig, style={"height": figheight}))

    return figures


# -------------------------------
def coverage_diffplot(
    df_diff: pd.DataFrame,
    phases: list,
    colorby: str,
    vector_type: str = "well",
    figheight: int = 450,
    boxmode: str = "group",
    boxplot_points: str = "outliers",
) -> List[wcc.Graph]:
    """Create plot of misfit per well. One plot per phase."""

    logging.debug("--- Updating coverage box plot ---")
    figures = []

    if df_diff.empty:
        fig = px.box(title="No data to plot for current selections.")
        return [wcc.Graph(figure=fig, style={"height": figheight})]

    # --- drop columns (realizations) with no data
    ensdf = df_diff.dropna(axis="columns")
    ensdf.DATE = ensdf.DATE.str[:10]

    for phase in phases:

        fig_phase = _create_fig_diffplot(
            ensdf, colorby, vector_type, phase, boxmode, boxplot_points
        )

        figures.append(wcc.Graph(figure=fig_phase, style={"height": figheight}))

    return figures


# -------------------------------
def coverage_crossplot(
    df_smry: pd.DataFrame,
    phases: list,
    colorby: str,
    vector_type: str = "well",
    figheight: int = 450,
    boxplot_points: str = "outliers",
) -> List[wcc.Graph]:
    """Create plot of hist vs simvector. One plot per phase."""

    logging.debug("--- Updating coverage box plot ---")
    figures = []

    prefix = "W" if vector_type == "well" else "G"
    phase_vector, phase_hvector = {}, {}
    phase_vector["Oil"] = prefix + "OPT"
    phase_vector["Water"] = prefix + "WPT"
    phase_vector["Gas"] = prefix + "GPT"
    phase_hvector["Oil"] = prefix + "OPTH"
    phase_hvector["Water"] = prefix + "WPTH"
    phase_hvector["Gas"] = prefix + "GPTH"

    vectorlist = []
    for phase in phases:
        vectorlist.append(phase_vector[phase])
        vectorlist.append(phase_hvector[phase])

    # --- drop columns (realizations) with no data
    # ensdf = df_smry.dropna(axis="columns")

    ensdf = df_smry
    ensdf.DATE = ensdf.DATE.str[:10]
    ensdf["id"] = ensdf.reset_index().index
    ensdf = pd.wide_to_long(
        ensdf,
        vectorlist,
        i="id",
        j="WELL",
        sep=":",
        suffix=r".+",
        # suffix=r"\w+|\d+",
    )
    # use hist avg values as x-values
    ensdf = makedf.get_df_hist_avg(ensdf)

    for phase in phases:

        fig_phase = _create_fig_crossplot(
            ensdf,
            colorby,
            phase,
            boxplot_points,
            phase_vector,
            phase_hvector,
        )

        figures.append(wcc.Graph(figure=fig_phase, style={"height": figheight}))

    return figures


# -------------------------------
def heatmap_plot(
    df_diff_stat: pd.DataFrame,
    phases: list,
    vector_type: str = "well",
    filter_largest: int = 10,
    figheight: int = 450,
    scale_col_range: float = 1.0,
) -> List[wcc.Graph]:
    """Create heatmap of mean misfit per well or group. One plot per phase."""

    logging.debug("--- Updating heatmap ---")
    figures = []

    prefix = "DIFF_W" if vector_type == "well" else "DIFF_G"
    phase_vector = {}
    phase_vector["Oil"] = prefix + "OPT"
    phase_vector["Water"] = prefix + "WPT"
    phase_vector["Gas"] = prefix + "GPT"

    logging.debug(f"Dataframe, diff_stat:\n{df_diff_stat}")

    if df_diff_stat.empty:
        fig = px.bar(title="No data to plot for current selections.")
        return [wcc.Graph(figure=fig, style={"height": figheight})]

    # -------------------------
    for phase in phases:
        df_diff_stat_phase = df_diff_stat[df_diff_stat.VECTOR == phase_vector[phase]]

        # logging.debug(f"Dataframe, diff {phase} phase:\n{df_diff_stat_phase}")

        zmax = scale_col_range * max(
            abs(df_diff_stat_phase.DIFF_MEAN.max()),
            abs(df_diff_stat_phase.DIFF_MEAN.min()),
        )

        for ens_name, df_diff_stat_phase in df_diff_stat_phase.groupby("ENSEMBLE"):

            fig_phase = _create_fig_heatmap(
                ens_name, phase, df_diff_stat_phase, filter_largest, zmax
            )

            figures.append(wcc.Graph(figure=fig_phase, style={"height": figheight}))

    return figures


# -- help functions -------------


def _calculate_misfits(
    phases: List[str],
    ensdf: pd.DataFrame,
    normalize: bool,
    misfit_exponent: float,
) -> Tuple[pd.DataFrame, List[str], Dict[str, str]]:
    """Calculate misfits for total and phases and return as dataframe"""

    # --- drop columns (realizations) with no data
    ensdf = ensdf.dropna(axis="columns")

    all_columns = list(ensdf)  # column names

    df_misfit = ensdf[["ENSEMBLE", "DATE", "REAL"]].copy()
    df_misfit = df_misfit.astype({"REAL": "string"})
    df_misfit["TOTAL_MISFIT"] = 0

    plot_phases = []
    color_phases = {}

    phase_misfit_name = dict(Oil="OIL_MISFIT", Water="WAT_MISFIT", Gas="GAS_MISFIT")
    diff_name = dict(Oil="DIFF_WOPT", Water="DIFF_WWPT", Gas="DIFF_WGPT")
    color = dict(Oil="#2ca02c", Water="#1f77b4", Gas="#d62728")

    for phase in phases:
        phase_columns = [x for x in all_columns if x.startswith(diff_name[phase])]
        df_misfit[phase_misfit_name[phase]] = ensdf[phase_columns].abs().sum(axis=1)
        if normalize:
            df_misfit[phase_misfit_name[phase]] = df_misfit[
                phase_misfit_name[phase]
            ] / len(phase_columns)
        df_misfit[phase_misfit_name[phase]] = df_misfit[phase_misfit_name[phase]] ** (
            1 / misfit_exponent
        )
        df_misfit["TOTAL_MISFIT"] = (
            df_misfit["TOTAL_MISFIT"] + df_misfit[phase_misfit_name[phase]]
        )
        plot_phases.append(phase_misfit_name[phase])
        color_phases[phase_misfit_name[phase]] = color[phase]
    # -------------------------

    return df_misfit, plot_phases, color_phases


# -------------------------------
def _create_fig_barplot(
    ens_name: str,
    df_misfit: pd.DataFrame,
    colorby: str,
    plot_phases: List[str],
    color_phases: Dict[str, str],
    max_misfit: float,
    min_misfit: float,
    sorting: Optional[str],
) -> px.bar:
    """Return misfit bar plot"""

    mean_misfit = df_misfit["TOTAL_MISFIT"].mean()

    color: Any = px.NO_COLOR
    color_discrete_map: Optional[dict] = None
    if colorby == "misfit":
        color = "TOTAL_MISFIT"
    elif colorby == "date":
        color = "DATE"
    elif colorby == "phases":
        color = None
        color_discrete_map = color_phases

    fig = px.bar(
        df_misfit,
        x="REAL",
        y=plot_phases,
        title=ens_name,
        range_y=[0, max_misfit * 1.05],
        color=color,
        color_discrete_map=color_discrete_map,
        range_color=[min_misfit * 0.20, max_misfit * 1.00],
        color_continuous_scale=px.colors.sequential.amp,
    )
    if sorting:
        fig.update_layout(xaxis={"categoryorder": sorting})
    fig.update_xaxes(showticklabels=False)
    fig.update_xaxes(title_text="Realization (hover to see values)")
    fig.update_yaxes(title_text="Cumulative misfit")
    fig.add_hline(mean_misfit)
    fig.add_annotation(average_arrow_annotation(mean_misfit))
    fig.update_layout(margin=dict(l=20, r=20, t=30, b=20))
    # fig.update_layout(coloraxis_colorbar_thickness=20)
    # fig.update(layout_coloraxis_showscale=False)

    return fig


# -------------------------------
def _create_fig_diffplot(
    ensdf: pd.DataFrame,
    colorby: str,
    vector_type: str,
    phase: str,
    boxmode: str,
    boxplot_points: str,
) -> Union[px.box, px.strip]:
    """Return boxplot or strip-plot fig"""

    all_columns = list(ensdf)  # column names

    prefix = "DIFF_W" if vector_type == "well" else "DIFF_G"
    phase_vector = {}
    phase_vector["Oil"] = prefix + "OPT"
    phase_vector["Water"] = prefix + "WPT"
    phase_vector["Gas"] = prefix + "GPT"

    facet_name = "DATE"
    if colorby == "DATE":
        facet_name = "ENSEMBLE"

    phase_columns = [x for x in all_columns if x.startswith(phase_vector[phase])]
    phase_well_labels = [col.split(":")[1] for col in phase_columns]
    text_labels = dict(value=f"{phase} diff (sim-obs)", variable="Well name")

    if boxplot_points == "strip":
        fig_phase = px.strip(
            ensdf,
            y=phase_columns,
            color=colorby,
            facet_col=facet_name,
            facet_col_wrap=2,
            labels=text_labels,
            stripmode=boxmode,
        )
    else:
        fig_phase = px.box(
            ensdf,
            y=phase_columns,
            color=colorby,
            facet_col=facet_name,
            facet_col_wrap=2,
            points=boxplot_points,
            labels=text_labels,
            boxmode=boxmode,
        )
    fig_phase.add_hline(0)
    fig_phase.update_xaxes(ticktext=phase_well_labels, tickvals=phase_columns)

    return fig_phase


# -------------------------------
def _create_fig_crossplot(
    ensdf: pd.DataFrame,
    colorby: str,
    phase: str,
    boxplot_points: str,
    phase_vector: dict,
    phase_hvector: dict,
) -> Union[px.box, px.strip]:
    """Return crossplot style boxplot or strip-plot fig. ensdf must be in long format."""

    facet_name = "DATE"
    if colorby == "DATE":
        facet_name = "ENSEMBLE"

    if boxplot_points == "strip":
        fig_phase = px.strip(
            ensdf,
            x=phase_hvector[phase],
            y=phase_vector[phase],
            color=colorby,
            facet_col=facet_name,
            facet_col_wrap=2,
            hover_name=ensdf.index.get_level_values("WELL"),
        )
    else:
        fig_phase = px.box(
            ensdf,
            x=phase_hvector[phase],
            y=phase_vector[phase],
            color=colorby,
            facet_col=facet_name,
            facet_col_wrap=2,
            points=boxplot_points,
            hover_name=ensdf.index.get_level_values("WELL"),
        )

    # -- add zeroline (diagonal) for oil_vector
    rmin = min(ensdf[phase_hvector[phase]].min(), ensdf[phase_vector[phase]].min())
    rmax = max(ensdf[phase_hvector[phase]].max(), ensdf[phase_vector[phase]].max())
    fig_phase.add_trace(
        go.Scattergl(
            x=[rmin, rmax],
            y=[rmin, rmax],
            mode="lines",
            line_color="rgb(0,100,80)",  # "gray",
            name="zeroline",
            showlegend=True,
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )

    # -- add 10% off-set for oil_vector
    fig_phase.add_trace(
        go.Scattergl(
            x=[rmin, rmax] + [rmax, rmin],
            y=[rmin * 1.1, rmax * 1.1] + [rmax * 0.9, rmin * 0.9],
            fill="toself",
            fillcolor="rgba(0,100,80,0.2)",
            # mode="lines",
            line_color="rgba(255,255,255,0)",
            name="±10% off-set",
            showlegend=True,
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )

    # -- add 20% off-set for oil_vector
    fig_phase.add_trace(
        go.Scattergl(
            x=[rmin, rmax] + [rmax, rmin],
            y=[rmin * 1.2, rmax * 1.2] + [rmax * 0.8, rmin * 0.8],
            fill="toself",
            fillcolor="rgba(255, 99, 71, 0.1)",
            # mode="lines",
            line_color="rgba(255,255,255,0)",
            name="±20% off-set",
            showlegend=True,
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )

    return fig_phase


# -------------------------------
def _create_fig_heatmap(
    ens_name: str,
    phase: str,
    df_diff_stat_phase: pd.DataFrame,
    filter_largest: int,
    zmax: float,
) -> px.imshow:
    """Return heatmap plot."""

    zmin = -zmax

    df_pivot = df_diff_stat_phase.pivot(
        index="WELL", columns="DATE", values="DIFF_MEAN"
    )

    df_sorted = df_diff_stat_phase[["WELL", "DIFF_MEAN"]].copy()
    df_sorted["DIFF_MEAN"] = df_sorted.DIFF_MEAN.abs()
    df_sorted = df_sorted.groupby("WELL").max()
    df_sorted = df_sorted.sort_values(by=["DIFF_MEAN"], ascending=False)

    if filter_largest > 0:
        wells_largest_misfit = list(df_sorted.index)[:filter_largest]
        df_pivot = df_pivot[df_pivot.index.isin(wells_largest_misfit)]

    logging.debug(f"Dataframe pivot table, {ens_name} diff {phase} phase:\n{df_pivot}")

    fig_phase = px.imshow(
        df_pivot,
        color_continuous_scale=HEATMAP_COLOR,
        zmin=zmin,
        zmax=zmax,
    )
    fig_phase.update_layout(
        title_text=f"{ens_name} - {phase} cummulative misfit (mean) vs date",
        title_font_size=16,
    )
    fig_phase.update_traces(
        hoverongaps=False,
        hovertemplate="Date: %{x}"
        "<br>Well: %{y}"
        "<br>Difference: %{z:.3s}<extra></extra>",
    )

    return fig_phase


# -------------------------------
def average_arrow_annotation(mean_value: np.float64, yref: str = "y") -> Dict[str, Any]:
    decimals = 0
    if mean_value < 0.001:
        decimals = 5
    elif mean_value < 0.01:
        decimals = 4
    elif mean_value < 0.1:
        decimals = 3
    elif mean_value < 10:
        decimals = 2
    elif mean_value < 100:
        decimals = 1

    text = f"Total average: {mean_value:,.{decimals}f}"

    return {
        "x": 0.5,
        "y": mean_value,
        "xref": "paper",
        "yref": yref,
        "text": text,
        "showarrow": True,
        "align": "center",
        "arrowhead": 2,
        "arrowsize": 1,
        "arrowwidth": 1,
        "arrowcolor": "#636363",
        "ax": 20,
        "ay": -25,
    }

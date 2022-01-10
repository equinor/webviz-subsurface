import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
import webviz_core_components as wcc


# -------------------------------
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

    if df_diff.empty:
        fig = px.bar(title="No data to plot for current selections.")
        return [wcc.Graph(figure=fig, style={"height": figheight})]

    misfit_plot_start_time = time.time()
    int_n = 0

    logging.debug("--- Updating production misfit plot ---")
    max_misfit, min_misfit = 0, 0
    figures = []

    for ens_name, ensdf in df_diff.groupby("ENSEMBLE"):

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        all_columns = list(ensdf)  # column names

        df_misfit = ensdf[["ENSEMBLE", "DATE", "REAL"]].copy()
        df_misfit = df_misfit.astype({"REAL": "string"})
        df_misfit["TOTAL_MISFIT"] = 0

        plot_phases = []
        color_phases = {}

        # -------------------------
        if "Oil" in phases:
            oil_columns = [x for x in all_columns if x.startswith("DIFF_WOPT")]
            df_misfit["OIL_MISFIT"] = ensdf[oil_columns].abs().sum(axis=1)
            if normalize:
                df_misfit["OIL_MISFIT"] = df_misfit["OIL_MISFIT"] / len(oil_columns)
            df_misfit["OIL_MISFIT"] = df_misfit["OIL_MISFIT"] ** (1 / misfit_exponent)
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["OIL_MISFIT"]
            )
            plot_phases.append("OIL_MISFIT")
            color_phases["OIL_MISFIT"] = "#2ca02c"
        # -------------------------
        if "Water" in phases:
            wat_columns = [x for x in all_columns if x.startswith("DIFF_WWPT")]
            df_misfit["WAT_MISFIT"] = ensdf[wat_columns].abs().sum(axis=1)
            if normalize:
                df_misfit["WAT_MISFIT"] = df_misfit["WAT_MISFIT"] / len(wat_columns)
            df_misfit["WAT_MISFIT"] = df_misfit["WAT_MISFIT"] ** (1 / misfit_exponent)
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["WAT_MISFIT"]
            )
            plot_phases.append("WAT_MISFIT")
            color_phases["WAT_MISFIT"] = "#1f77b4"
        # -------------------------
        if "Gas" in phases:
            gas_columns = [x for x in all_columns if x.startswith("DIFF_WGPT")]
            df_misfit["GAS_MISFIT"] = ensdf[gas_columns].abs().sum(axis=1)
            if normalize:
                df_misfit["GAS_MISFIT"] = df_misfit["GAS_MISFIT"] / len(gas_columns)
            df_misfit["GAS_MISFIT"] = df_misfit["GAS_MISFIT"] ** (1 / misfit_exponent)
            df_misfit["TOTAL_MISFIT"] = (
                df_misfit["TOTAL_MISFIT"] + df_misfit["GAS_MISFIT"]
            )
            plot_phases.append("GAS_MISFIT")
            color_phases["GAS_MISFIT"] = "#d62728"
        # -------------------------

        int_n += 1
        logging.debug(
            f"\n--- update_prod_misfit_plot --- {ens_name} "
            f"Intermediate time {int_n}: {time.time() - misfit_plot_start_time} seconds."
        )

        if (
            max_misfit == min_misfit == 0
        ):  # caclulate min-max ranges from first ensemble
            for _, df_date in df_misfit.groupby("DATE"):
                max_misfit = max_misfit + df_date["TOTAL_MISFIT"].max()
                min_misfit = min_misfit + df_date["TOTAL_MISFIT"].min()
        mean_misfit = df_misfit["TOTAL_MISFIT"].mean()

        color: Any = px.NO_COLOR
        color_discrete_map: Optional[dict] = None
        if colorby == "misfit":
            color = "TOTAL_MISFIT"
        elif colorby == "Date":
            color = "DATE"
        elif colorby == "Phases":
            color = None
            color_discrete_map = color_phases

        fig = px.bar(
            df_misfit,
            x="REAL",
            y=plot_phases,
            title=ens_name,
            # range_y=[min_misfit * 0.25, max_misfit * 1.05],
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

        figures.append(wcc.Graph(figure=fig, style={"height": figheight}))

        int_n += 1
        logging.debug(
            f"\n--- update_prod_misfit_plot --- {ens_name} "
            f"Intermediate time {int_n}: {time.time() - misfit_plot_start_time} seconds."
        )

    logging.debug(
        "\n--- update_prod_misfit_plot ---"
        f"Total time: {time.time() - misfit_plot_start_time} seconds.\n"
    )
    return figures


# --------------------------------
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

    # --- drop columns (realizations) with no data
    ensdf = df_diff.dropna(axis="columns")
    ensdf.DATE = ensdf.DATE.str[:10]

    print(phases)

    phase_vector = {}
    prefix = "W" if vector_type == "well" else "G"
    phase_vector["Oil"] = "DIFF_" + prefix + "OPT"
    phase_vector["Water"] = "DIFF_" + prefix + "WPT"
    phase_vector["Gas"] = "DIFF_" + prefix + "GPT"

    all_columns = list(ensdf)  # column names
    facet_name = "DATE"
    if colorby == "DATE":
        facet_name = "ENSEMBLE"

    for phase in phases:
        phase_columns = [x for x in all_columns if x.startswith(phase_vector[phase])]
        phase_well_labels = [col.split(":")[1] for col in phase_columns]
        text_labels = dict(value=f"{phase} diff (sim-obs)", variable="Well name")

        print(phase_columns, phase_well_labels)

        if boxplot_points == "strip":
            fig_phase = px.strip(
                ensdf,
                y=phase_columns,
                color=colorby,
                facet_col=facet_name,
                facet_col_wrap=2,
                # points=boxplot_points,
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

    # --- drop columns (realizations) with no data
    # ensdf = df_smry.dropna(axis="columns")

    ensdf = df_smry
    ensdf.DATE = ensdf.DATE.str[:10]
    ensdf["id"] = ensdf.reset_index().index
    ensdf = pd.wide_to_long(
        ensdf,
        ["WOPT", "WWPT", "WGPT", "WOPTH", "WWPTH", "WGPTH"],
        i="id",
        j="WELL",
        sep=":",
        suffix=r"\w+",
    )
    print(ensdf)

    phase_vector = {}
    phase_hvector = {}
    prefix = "W" if vector_type == "well" else "G"
    phase_vector["Oil"] = prefix + "OPT"
    phase_vector["Water"] = prefix + "WPT"
    phase_vector["Gas"] = prefix + "GPT"
    phase_hvector["Oil"] = prefix + "OPTH"
    phase_hvector["Water"] = prefix + "WPTH"
    phase_hvector["Gas"] = prefix + "GPTH"

    facet_name = "DATE"
    if colorby == "DATE":
        facet_name = "ENSEMBLE"

    for phase in phases:

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
    """Create heatmap of misfit per well or group. One plot per phase."""

    logging.debug("--- Updating heatmap ---")
    figures = []

    if vector_type == "group":
        oil_vector, wat_vector, gas_vector = "DIFF_GOPT", "DIFF_GWPT", "DIFF_GGPT"
    elif vector_type == "well":
        oil_vector, wat_vector, gas_vector = "DIFF_WOPT", "DIFF_WWPT", "DIFF_WGPT"
    else:
        raise ValueError(
            "vector_type = ",
            vector_type,
            ". 'vector_type' argument must be 'well' or 'group'",
        )

    # -------------------------
    if "Oil" in phases:
        df_diff_stat_oil = df_diff_stat[df_diff_stat.VECTOR == oil_vector]
        # logging.debug(f"Dataframe, diff oil phase:\n{df_diff_stat_oil}")

        zmax = scale_col_range * max(
            abs(df_diff_stat_oil.DIFF_MEAN.max()), abs(df_diff_stat_oil.DIFF_MEAN.min())
        )
        zmin = -zmax

        for ens_name, ensdf in df_diff_stat_oil.groupby("ENSEMBLE"):

            df_temp = ensdf[["WELL", "DIFF_MEAN"]].copy()
            df_temp["DIFF_MEAN"] = df_temp.DIFF_MEAN.abs()
            df_temp = df_temp.groupby("WELL").max()
            df_temp = df_temp.sort_values(by=["DIFF_MEAN"], ascending=False)

            df_pivot = ensdf.pivot(index="WELL", columns="DATE", values="DIFF_MEAN")
            if filter_largest > 0:
                wells_largest_misfit = list(df_temp.index)[:filter_largest]
                df_pivot = df_pivot[df_pivot.index.isin(wells_largest_misfit)]

            # logging.debug(
            #     f"Dataframe pivot table, {ens_name} diff oil phase:\n{df_pivot}"
            # )

            fig_oil = px.imshow(
                df_pivot,
                color_continuous_scale=SYMMETRIC,
                zmin=zmin,
                zmax=zmax,
            )
            fig_oil.update_layout(
                title_text=f"{ens_name} - Oil cummulative misfit (mean) vs date",
                title_font_size=16,
            )
            fig_oil.update_traces(
                hoverongaps=False,
                hovertemplate="Date: %{x}"
                "<br>Well: %{y}"
                "<br>Difference: %{z:.3s}<extra></extra>",
            )

            figures.append(wcc.Graph(figure=fig_oil, style={"height": figheight}))

    # -------------------------
    if "Water" in phases:
        df_diff_stat_wat = df_diff_stat[df_diff_stat.VECTOR == wat_vector]

        zmax = scale_col_range * max(
            abs(df_diff_stat_wat.DIFF_MEAN.max()), abs(df_diff_stat_wat.DIFF_MEAN.min())
        )
        zmin = -zmax

        for ens_name, ensdf in df_diff_stat_wat.groupby("ENSEMBLE"):

            df_temp = ensdf[["WELL", "DIFF_MEAN"]].copy()
            df_temp["DIFF_MEAN"] = df_temp.DIFF_MEAN.abs()
            df_temp = df_temp.groupby("WELL").max()
            df_temp = df_temp.sort_values(by=["DIFF_MEAN"], ascending=False)

            df_pivot = ensdf.pivot(index="WELL", columns="DATE", values="DIFF_MEAN")
            if filter_largest > 0:
                wells_largest_misfit = list(df_temp.index)[:filter_largest]
                df_pivot = df_pivot[df_pivot.index.isin(wells_largest_misfit)]

            fig_wat = px.imshow(
                df_pivot,
                color_continuous_scale=SYMMETRIC,
                zmin=zmin,
                zmax=zmax,
            )
            fig_wat.update_layout(
                title_text=f"{ens_name} - Wat cummulative misfit (mean) vs date",
                title_font_size=16,
            )
            fig_wat.update_traces(
                hoverongaps=False,
                hovertemplate="Date: %{x}"
                "<br>Well: %{y}"
                "<br>Difference: %{z:.3s}<extra></extra>",
            )

            figures.append(wcc.Graph(figure=fig_wat, style={"height": figheight}))

    # -------------------------
    if "Gas" in phases:
        df_diff_stat_gas = df_diff_stat[df_diff_stat.VECTOR == gas_vector]

        zmax = scale_col_range * max(
            abs(df_diff_stat_gas.DIFF_MEAN.max()), abs(df_diff_stat_gas.DIFF_MEAN.min())
        )
        zmin = -zmax

        for ens_name, ensdf in df_diff_stat_gas.groupby("ENSEMBLE"):

            df_temp = ensdf[["WELL", "DIFF_MEAN"]].copy()
            df_temp["DIFF_MEAN"] = df_temp.DIFF_MEAN.abs()
            df_temp = df_temp.groupby("WELL").max()
            df_temp = df_temp.sort_values(by=["DIFF_MEAN"], ascending=False)

            df_pivot = ensdf.pivot(index="WELL", columns="DATE", values="DIFF_MEAN")
            if filter_largest > 0:
                wells_largest_misfit = list(df_temp.index)[:filter_largest]
                df_pivot = df_pivot[df_pivot.index.isin(wells_largest_misfit)]

            fig_gas = px.imshow(
                df_pivot,
                color_continuous_scale=SYMMETRIC,
                zmin=zmin,
                zmax=zmax,
            )
            fig_gas.update_layout(
                title_text=f"{ens_name} - Gas cummulative misfit (mean) vs date",
                title_font_size=16,
            )
            fig_gas.update_traces(
                hoverongaps=False,
                hovertemplate="Date: %{x}"
                "<br>Well: %{y}"
                "<br>Difference: %{z:.3s}<extra></extra>",
            )

            figures.append(wcc.Graph(figure=fig_gas, style={"height": figheight}))

    return figures

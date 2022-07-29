# pylint: disable=too-many-lines
import logging
from typing import Any, List, Optional, Tuple, Union

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import webviz_core_components as wcc
from plotly.subplots import make_subplots

from .._seismic_color_scales import ColorScales
from ._dataframe_functions import df_seis_ens_stat
from ._support_functions import average_arrow_annotation


# -------------------------------
def update_misfit_plot(
    df: pd.DataFrame,
    sorting: str,
    figheight: int = 450,
    misfit_weight: Optional[str] = None,
    misfit_exponent: float = 1.0,
    normalize: bool = False,
) -> List[wcc.Graph]:
    """Create plot of misfit per realization. One plot per ensemble.
    Misfit is absolute value of |sim - obs|, weighted by obs_error"""

    # max_diff = find_max_diff(df)
    max_diff = None
    figures = []

    for ens_name, ensdf in df.groupby("ENSEMBLE"):
        logging.debug(f"Seismic misfit plot, updating {ens_name}")

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        # --- calculate absolute diff, (|sim - obs| / obs_error), and store in new df
        ensdf_diff = pd.DataFrame()
        for col in ensdf.columns:
            if col.startswith("real-"):
                ensdf_diff[col] = abs(ensdf[col] - ensdf["obs"])
                if misfit_weight == "obs_error":
                    ensdf_diff[col] = ensdf_diff[col] / ensdf["obs_error"]
                ensdf_diff[col] = ensdf_diff[col] ** misfit_exponent

        # --- make sum of abs diff values over each column (realization)
        ensdf_diff_sum = ensdf_diff.abs().sum().reset_index()
        ensdf_diff_sum = ensdf_diff_sum.rename(columns={"index": "REAL", 0: "ABSDIFF"})
        ensdf_diff_sum["ENSEMBLE"] = ens_name

        if normalize:
            ensdf_diff_sum["ABSDIFF"] = (
                ensdf_diff_sum["ABSDIFF"] / len(ensdf_diff)
            ) ** (1 / misfit_exponent)

        # --- remove "real-" from REAL column values
        # --- (only keep real number for nicer xaxis label)
        ensdf_diff_sum = ensdf_diff_sum.replace(
            to_replace=r"^real-", value="", regex=True
        )

        # --- calculate max from first ensemble, use with color range ---
        if max_diff is None:
            max_diff = ensdf_diff_sum["ABSDIFF"].max()

        mean_diff = ensdf_diff_sum["ABSDIFF"].mean()

        # --- sorting ----
        if sorting is not None:
            ensdf_diff_sum = ensdf_diff_sum.sort_values(
                by=["ABSDIFF"], ascending=sorting
            )

        fig = px.bar(
            ensdf_diff_sum,
            x="REAL",
            y="ABSDIFF",
            title=ens_name,
            range_y=[0, max_diff * 1.05],
            color="ABSDIFF",
            range_color=[0, max_diff],
            color_continuous_scale=px.colors.sequential.amp,
            hover_data={"ABSDIFF": ":,.3r"},
        )
        fig.update_xaxes(showticklabels=False)
        fig.update_xaxes(title_text="Realization (hover to see values)")
        fig.update_yaxes(title_text="Cumulative misfit")
        fig.add_hline(mean_diff)
        fig.add_annotation(average_arrow_annotation(mean_diff, "y"))
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20))
        fig.update_layout(coloraxis_colorbar_thickness=20)
        # fig.update(layout_coloraxis_showscale=False)

        figures.append(wcc.Graph(figure=fig, style={"height": figheight}))

    return figures


# -------------------------------
def update_obsdata_raw(
    df_obs: pd.DataFrame,
    colorby: Optional[str] = None,
    showerror: bool = False,
    showhistogram: bool = False,
    reset_index: bool = False,
) -> px.scatter:
    """Plot seismic obsdata; raw plot.
    Takes dataframe with obsdata and metadata as input"""

    if colorby not in df_obs.columns and colorby is not None:
        colorby = None
        logging.warning(f"{colorby} is not included, colorby is reset to None")

    df_obs = df_obs.sort_values(by=["region"])
    df_obs = df_obs.astype({colorby: "string"})
    # df_obs = df_obs.astype({colorby: int})

    # ----------------------------------------
    # fig: raw data plot
    # ----------------------------------------

    if reset_index:
        df_obs.reset_index(inplace=True)
        df_obs["data_point"] = df_obs.index + 1
    else:
        df_obs["data_point"] = df_obs.data_number

    marg_y = None
    if showhistogram:
        marg_y = "histogram"

    err_y = None
    if showerror:
        err_y = "obs_error"

    fig_raw = px.scatter(
        df_obs,
        x="data_point",
        y="obs",
        color=colorby,
        marginal_y=marg_y,
        error_y=err_y,
        hover_data={
            "region": True,
            "data_point": False,
            "obs": ":.2r",
            "obs_error": ":.2r",
            "east": ":,.0f",
            "north": ":,.0f",
            "data_number": True,
        },
        title="obs data raw plot | colorby: " + str(colorby),
    )
    if reset_index:
        fig_raw.update_xaxes(title_text="data point (sorted by region)")
    else:
        fig_raw.update_xaxes(title_text="data point (original ordering)")
    if showerror:
        fig_raw.update_yaxes(title_text="observation value w/error")
    else:
        fig_raw.update_yaxes(title_text="observation value")

    fig_raw.update_yaxes(uirevision="true")  # don't update y-range during callbacks
    return fig_raw


# -------------------------------
def update_obsdata_map(
    df_obs: pd.DataFrame,
    colorby: str,
    df_polygon: pd.DataFrame,
    obs_range: List[float],
    obs_err_range: List[float],
    scale_col_range: float = 0.6,
    marker_size: int = 10,
) -> Optional[px.scatter]:
    """Plot seismic obsdata; map view plot.
    Takes dataframe with obsdata and metadata as input"""

    if ("east" not in df_obs.columns) or ("north" not in df_obs.columns):
        logging.warning("-- Do not have necessary data for making map view plot")
        logging.warning("-- Consider adding east/north coordinates to metafile")
        return None

    if df_obs[colorby].dtype == "int64" or colorby == "region":
        df_obs = df_obs.sort_values(by=[colorby])
        df_obs = df_obs.astype(
            {colorby: "string"}
        )  # define as string to colorby discrete variable
    # ----------------------------------------
    color_scale = None
    scale_midpoint = None
    range_col = None

    if colorby == "obs":
        range_col, scale_midpoint, color_scale = _get_obsdata_col_settings(
            colorby, obs_range, scale_col_range
        )
    if colorby == "obs_error":
        range_col, scale_midpoint, color_scale = _get_obsdata_col_settings(
            colorby, obs_err_range, scale_col_range
        )

    # ----------------------------------------
    fig = px.scatter(  # map view plot
        df_obs,
        x="east",
        y="north",
        color=colorby,
        hover_data={
            "east": False,
            "north": False,
            "region": True,
            "obs": ":.2r",
            "obs_error": ":.2r",
            "data_number": True,
        },
        color_continuous_scale=color_scale,
        color_continuous_midpoint=scale_midpoint,
        range_color=range_col,
        title="obs data map view plot | colorby: " + str(colorby),
    )

    # ----------------------------------------
    # add polygon to map if defined
    if not df_polygon.empty:
        for poly_id, polydf in df_polygon.groupby("ID"):
            fig.append_trace(
                go.Scattergl(
                    x=polydf["X"],
                    y=polydf["Y"],
                    mode="lines",
                    line_color="RoyalBlue",
                    name=f"pol{poly_id}",
                    showlegend=False,
                    hoverinfo="name",
                ),
                row="all",
                col="all",
                # exclude_empty_subplots=True,
            )

    fig.update_yaxes(scaleanchor="x")
    fig.update_layout(coloraxis_colorbar_x=0.95)
    fig.update_layout(coloraxis_colorbar_y=1.0)
    fig.update_layout(coloraxis_colorbar_yanchor="top")
    fig.update_layout(coloraxis_colorbar_len=0.9)
    fig.update_layout(coloraxis_colorbar_thickness=20)
    fig.update_traces(marker=dict(size=marker_size), selector=dict(mode="markers"))

    fig.update_layout(uirevision="true")  # don't update layout during callbacks

    return fig


# -------------------------------
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
def update_obs_sim_map_plot(
    df: pd.DataFrame,
    ens_name: str,
    df_polygon: pd.DataFrame,
    obs_range: List[float],
    scale_col_range: float = 0.8,
    slice_accuracy: Union[int, float] = 100,
    slice_position: float = 0.0,
    plot_coverage: int = 0,
    marker_size: int = 10,
    slice_type: str = "stat",
) -> Tuple[Optional[Any], Optional[Any]]:
    """Plot seismic obsdata, simdata and diffdata; side by side map view plots.
    Takes dataframe with obsdata, metadata and simdata as input"""

    logging.debug(f"Seismic obs vs sim map plot, updating {ens_name}")

    ensdf = df[df.ENSEMBLE.eq(ens_name)]

    if ("east" not in ensdf.columns) or ("north" not in ensdf.columns):
        logging.warning("-- Do not have necessary data for making map view plot")
        logging.warning("-- Consider adding east/north coordinates to metafile")
        return None, None

    # --- drop columns (realizations) with no data
    ensdf = ensdf.dropna(axis="columns")

    # --- get dataframe with statistics per datapoint
    ensdf_stat = df_seis_ens_stat(ensdf, ens_name)

    if ensdf_stat.empty:
        return (
            make_subplots(
                rows=1,
                cols=3,
                subplot_titles=("No data for current selection", "---", "---"),
            ),
            go.Figure(),
        )

    # ----------------------------------------
    # set obs/sim color scale and ranges
    range_col, _, color_scale = _get_obsdata_col_settings(
        "obs", obs_range, scale_col_range
    )

    # ----------------------------------------
    if plot_coverage == 0:
        title3 = "Abs diff (mean)"
    elif plot_coverage in [1, 2]:
        title3 = "Coverage plot"
    else:
        title3 = "Region plot"

    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=("Observed", "Simulated (mean)", title3),
        shared_xaxes=True,
        vertical_spacing=0.02,
        shared_yaxes=True,
        horizontal_spacing=0.02,
    )

    fig.add_trace(
        go.Scattergl(
            x=ensdf_stat["east"],
            y=ensdf_stat["north"],
            mode="markers",
            marker=dict(
                size=marker_size,
                color=ensdf["obs"],
                colorscale=color_scale,
                colorbar_x=0.29,
                colorbar_thicknessmode="fraction",
                colorbar_thickness=0.02,
                colorbar_len=0.9,
                cmin=range_col[0],
                cmax=range_col[1],
                showscale=True,
            ),
            showlegend=False,
            text=ensdf.obs,
            customdata=list(zip(ensdf.region, ensdf.east)),
            hovertemplate=(
                "Obs: %{text:.2r}<br>Region: %{customdata[0]}<br>"
                "East: %{customdata[1]:,.0f}<extra></extra>"
            ),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scattergl(
            x=ensdf_stat["east"],
            y=ensdf_stat["north"],
            mode="markers",
            marker=dict(
                size=marker_size,
                color=ensdf_stat["sim_mean"],
                colorscale=color_scale,
                colorbar_x=0.63,
                colorbar_thicknessmode="fraction",
                colorbar_thickness=0.02,
                colorbar_len=0.9,
                cmin=range_col[0],
                cmax=range_col[1],
                showscale=True,
            ),
            showlegend=False,
            text=ensdf_stat.sim_mean,
            customdata=list(zip(ensdf.region, ensdf.east)),
            hovertemplate=(
                "Sim (mean): %{text:.2r}<br>Region: %{customdata[0]}<br>"
                "East: %{customdata[1]:,.0f}<extra></extra>"
            ),
        ),
        row=1,
        col=2,
    )

    if plot_coverage == 0:  # abs diff plot
        fig.add_trace(
            go.Scattergl(
                x=ensdf_stat["east"],
                y=ensdf_stat["north"],
                mode="markers",
                marker=dict(
                    size=marker_size,
                    color=ensdf_stat["diff_mean"],
                    cmin=0,
                    cmax=obs_range[1] * scale_col_range,
                    colorscale=ColorScales.SEISMIC_DIFF,
                    colorbar_x=0.97,
                    colorbar_thicknessmode="fraction",
                    colorbar_thickness=0.02,
                    colorbar_len=0.9,
                    showscale=True,
                ),
                showlegend=False,
                text=ensdf_stat.diff_mean,
                customdata=list(zip(ensdf.region, ensdf.east)),
                hovertemplate=(
                    "Abs diff (mean): %{text:.2r}<br>Region: %{customdata[0]}<br>"
                    "East: %{customdata[1]:,.0f}<extra></extra>"
                ),
            ),
            row=1,
            col=3,
        )
    elif plot_coverage in [1, 2]:
        coverage = "sim_coverage" if plot_coverage == 1 else "sim_coverage_adj"
        fig.add_trace(
            go.Scattergl(
                x=ensdf_stat["east"],
                y=ensdf_stat["north"],
                mode="markers",
                marker=dict(
                    size=marker_size,
                    color=ensdf_stat[coverage],
                    cmin=-1.0,
                    cmax=2.0,
                    colorscale=ColorScales.SEISMIC_COVERAGE,
                    colorbar=dict(
                        # title="Coverage",
                        tickvals=[-0.5, 0.5, 1.5],
                        ticktext=["Overmodelled", "Coverage", "Undermodelled"],
                    ),
                    colorbar_x=0.97,
                    colorbar_thicknessmode="fraction",
                    colorbar_thickness=0.02,
                    colorbar_len=0.9,
                    showscale=True,
                ),
                opacity=0.5,
                showlegend=False,
                text=ensdf_stat[coverage],
                customdata=list(zip(ensdf.region, ensdf.east)),
                hovertemplate=(
                    "Coverage value: %{text:.2r}<br>Region: %{customdata[0]}<br>"
                    "East: %{customdata[1]:,.0f}<extra></extra>"
                ),
            ),
            row=1,
            col=3,
        )
    else:  # region plot
        fig.add_trace(
            go.Scattergl(
                x=ensdf["east"],
                y=ensdf["north"],
                mode="markers",
                marker=dict(
                    size=marker_size,
                    color=ensdf.region,
                    colorscale=px.colors.qualitative.Plotly,
                    colorbar_x=0.97,
                    colorbar_thicknessmode="fraction",
                    colorbar_thickness=0.02,
                    colorbar_len=0.9,
                    showscale=False,
                ),
                opacity=0.8,
                showlegend=False,
                hovertemplate="Region: %{text}<extra></extra>",
                text=ensdf.region,
            ),
            row=1,
            col=3,
        )

    # ----------------------------------------
    # add horizontal line at slice position
    fig.add_hline(
        y=slice_position,
        line_dash="dot",
        line_color="green",
        row="all",
        col="all",
        annotation_text="slice",
        annotation_position="bottom left",
    )

    # ----------------------------------------
    # add polygon to map if defined
    if not df_polygon.empty:
        for poly_id, polydf in df_polygon.groupby("ID"):
            fig.append_trace(
                go.Scattergl(
                    x=polydf["X"],
                    y=polydf["Y"],
                    mode="lines",
                    line_color="RoyalBlue",
                    name=f"pol{poly_id}",
                    showlegend=False,
                    hoverinfo="name",
                ),
                row="all",
                col="all",
                # exclude_empty_subplots=True,
            )

    fig.update_yaxes(scaleanchor="x")
    fig.update_xaxes(scaleanchor="x")
    fig.update_xaxes(matches="x")  # this solved issue with misaligned zoom/pan

    fig.update_layout(uirevision="true")  # don't update layout during callbacks

    fig.update_layout(hovermode="closest")
    # fig.update_layout(template="plotly_dark")

    # ----------------------------------------
    if slice_type == "stat":
        # Create lineplot along slice - statistics

        df_sliced_stat = ensdf_stat[
            (ensdf_stat.north < slice_position + slice_accuracy)
            & (ensdf_stat.north > slice_position - slice_accuracy)
        ]
        df_sliced_stat = df_sliced_stat.sort_values(by="east", ascending=True)

        fig_slice_stat = go.Figure(
            [
                go.Scatter(
                    name="Obsdata",
                    x=df_sliced_stat["east"],
                    y=df_sliced_stat["obs"],
                    mode="markers+lines",
                    marker=dict(color="red", size=5),
                    line=dict(width=2, dash="solid"),
                    showlegend=True,
                ),
                go.Scatter(
                    name="Sim mean",
                    x=df_sliced_stat["east"],
                    y=df_sliced_stat["sim_mean"],
                    mode="markers+lines",
                    marker=dict(color="green", size=3),
                    line=dict(width=1, dash="dot"),
                    showlegend=True,
                ),
                go.Scatter(
                    name="Sim p10",
                    x=df_sliced_stat["east"],
                    y=df_sliced_stat["sim_p10"],
                    mode="lines",
                    marker=dict(color="#444"),
                    line=dict(width=1),
                    showlegend=True,
                ),
                go.Scatter(
                    name="Sim p90",
                    x=df_sliced_stat["east"],
                    y=df_sliced_stat["sim_p90"],
                    marker=dict(color="#444"),
                    line=dict(width=1),
                    mode="lines",
                    fillcolor="rgba(68, 68, 68, 0.3)",
                    fill="tonexty",
                    showlegend=True,
                ),
                go.Scatter(
                    name="Sim min",
                    x=df_sliced_stat["east"],
                    y=df_sliced_stat["sim_min"],
                    mode="lines",
                    line=dict(width=1, dash="dot", color="grey"),
                    showlegend=True,
                ),
                go.Scatter(
                    name="Sim max",
                    x=df_sliced_stat["east"],
                    y=df_sliced_stat["sim_max"],
                    mode="lines",
                    line=dict(width=1, dash="dot", color="grey"),
                    showlegend=True,
                ),
            ]
        )
        fig_slice_stat.update_layout(
            yaxis_title="Attribute value",
            xaxis_title="East",
            title="Attribute values along slice",
            hovermode="x",
        )
        fig_slice_stat.update_yaxes(
            uirevision="true"
        )  # don't update y-range during callbacks

        return fig, fig_slice_stat

    # ----------------------------------------
    if slice_type == "reals":
        # Create lineplot along slice - individual realizations

        df_sliced_reals = ensdf[
            (ensdf.north < slice_position + slice_accuracy)
            & (ensdf.north > slice_position - slice_accuracy)
        ]
        df_sliced_reals = df_sliced_reals.sort_values(by="east", ascending=True)

        fig_slice_reals = go.Figure(
            [
                go.Scatter(
                    name="Obsdata",
                    x=df_sliced_reals["east"],
                    y=df_sliced_reals["obs"],
                    mode="markers+lines",
                    marker=dict(color="red", size=7),
                    line=dict(width=5, dash="solid"),
                    showlegend=True,
                ),
            ],
        )

        for col in df_sliced_reals.columns:
            if col.startswith("real-"):
                fig_slice_reals.add_trace(
                    go.Scattergl(
                        x=df_sliced_reals["east"],
                        y=df_sliced_reals[col],
                        mode="lines",  # "markers+lines",
                        line_shape="linear",
                        line=dict(width=1, dash="dash"),
                        name=col,
                        showlegend=True,
                        hoverinfo="name",
                    )
                )

        fig_slice_reals.update_layout(
            yaxis_title="Attribute value",
            xaxis_title="East",
            title="Attribute values along slice",
            hovermode="closest",
            clickmode="event+select",
        )
        fig_slice_reals.update_yaxes(
            uirevision="true"
        )  # don't update user selected y-ranges during callbacks

        return fig, fig_slice_reals

    return fig, None


# -------------------------------
# pylint: disable=too-many-locals
def update_crossplot(
    df: pd.DataFrame,
    colorby: Optional[str] = None,
    sizeby: Optional[str] = None,
    showerrorbar: Optional[str] = None,
    fig_columns: int = 1,
    figheight: int = 450,
) -> Optional[List[wcc.Graph]]:
    """Create crossplot of ensemble average sim versus obs,
    one value per seismic datapoint."""

    dfs, figures = [], []
    for ens_name, ensdf in df.groupby("ENSEMBLE"):
        logging.debug(f"Seismic crossplot; updating {ens_name}")

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        # --- make dataframe with statistics per datapoint
        ensdf_stat = df_seis_ens_stat(ensdf, ens_name)
        if ensdf_stat.empty:
            break

        # del ensdf

        if (
            sizeby in ("sim_std", "diff_std")
            and ensdf_stat["sim_std"].isnull().values.any()
        ):
            logging.info("Chosen sizeby is ignored for current selections (std = nan).")
            sizeby = None

        errory = None
        errory_minus = None
        if showerrorbar == "sim_std":
            errory = "sim_std"
        elif showerrorbar == "sim_p10_p90":
            ensdf_stat["error_plus"] = abs(
                ensdf_stat["sim_mean"] - ensdf_stat["sim_p10"]
            )
            ensdf_stat["error_minus"] = abs(
                ensdf_stat["sim_mean"] - ensdf_stat["sim_p90"]
            )
            errory = "error_plus"
            errory_minus = "error_minus"

        # -------------------------------------------------------------
        if colorby == "region":
            ensdf_stat = ensdf_stat.sort_values(by=[colorby])
            ensdf_stat = ensdf_stat.astype({"region": "string"})

        dfs.append(ensdf_stat)
    # -------------------------------------------------------------
    if len(dfs) == 0:
        return None

    df_stat = pd.concat(dfs)

    no_plots = len(df_stat.ENSEMBLE.unique())
    if no_plots <= fig_columns:
        total_height = figheight * (1 + 45 / figheight)
    else:
        total_height = figheight * round(no_plots / fig_columns)

    fig = px.scatter(
        df_stat,
        facet_col="ENSEMBLE",
        facet_col_wrap=fig_columns,
        x="obs",
        y="sim_mean",
        error_y=errory,
        error_y_minus=errory_minus,
        color=colorby,
        size=sizeby,
        size_max=20,
        # hover_data=list(df_stat.columns),
        hover_data={
            "region": True,
            "ENSEMBLE": False,
            "obs": ":.2r",
            # "obs_error": ":.2r",
            "sim_mean": ":.2r",
            # "sim_std": ":.2r",
            "diff_mean": ":.2r",
            # "east": ":,.0f",
            # "north": ":,.0f",
            "data_number": True,
        },
    )
    fig.update_traces(marker=dict(sizemode="area"), error_y_thickness=1.0)
    fig.update_layout(uirevision="true")  # don't update layout during callbacks

    # add zero/diagonal line
    min_obs = df.obs.min()
    max_obs = df.obs.max()
    fig.add_trace(
        go.Scattergl(
            x=[min_obs, max_obs],  # xplot_range,
            y=[min_obs, max_obs],  # yplot_range,
            mode="lines",
            line_color="gray",
            name="zeroline",
            showlegend=False,
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )

    # set marker line color = black (default is white)
    if sizeby is None:
        fig.update_traces(
            marker=dict(line=dict(width=0.4, color="black")),
            selector=dict(mode="markers"),
        )

    figures.append(wcc.Graph(figure=fig.to_dict(), style={"height": total_height}))
    return figures


# -------------------------------
# pylint: disable=too-many-statements
# pylint: disable=too-many-locals
def update_errorbarplot(
    df: pd.DataFrame,
    colorby: Optional[str] = None,
    showerrorbar: Optional[str] = None,
    showerrorbarobs: Optional[str] = None,
    reset_index: bool = False,
    fig_columns: int = 1,
    figheight: int = 450,
) -> Optional[List[wcc.Graph]]:
    """Create errorbar plot of ensemble sim versus obs,
    one value per seismic datapoint."""

    first = True
    figures = []
    dfs = []

    for ens_name, ensdf in df.groupby("ENSEMBLE"):
        logging.debug(f"Seismic errorbar plot; updating {ens_name}")

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        # --- make dataframe with statistics per datapoint
        ensdf_stat = df_seis_ens_stat(ensdf, ens_name)
        if ensdf_stat.empty:
            break

        del ensdf

        errory = None
        errory_minus = None
        if showerrorbar == "sim_std":
            errory = "sim_std"
        elif showerrorbar == "sim_p10_p90":
            ensdf_stat["error_plus"] = abs(
                ensdf_stat["sim_mean"] - ensdf_stat["sim_p10"]
            )
            ensdf_stat["error_minus"] = abs(
                ensdf_stat["sim_mean"] - ensdf_stat["sim_p90"]
            )
            errory = "error_plus"
            errory_minus = "error_minus"

        # -------------------------------------------------------------
        ensdf_stat = ensdf_stat.sort_values(by=["region"])
        ensdf_stat = ensdf_stat.astype({"region": "string"})

        if reset_index:
            ensdf_stat.reset_index(inplace=True)

        ensdf_stat["counter"] = (
            ensdf_stat.index + 1
        )  # make new counter after reset index

        # -------------------------------------------------------------
        # get color ranges from first case
        if first:
            cmin = None
            cmax = None
            if isinstance(colorby, float):
                cmin = ensdf_stat[colorby].min()
                cmax = ensdf_stat[colorby].quantile(0.8)
            first = False

        dfs.append(ensdf_stat)
    # -------------------------------------------------------------
    if len(dfs) == 0:
        return None

    df_stat = pd.concat(dfs)

    no_plots = len(df_stat.ENSEMBLE.unique())
    if no_plots <= fig_columns:
        total_height = figheight * (1 + 45 / figheight)
    else:
        total_height = figheight * round(no_plots / fig_columns)

    fig = px.scatter(
        df_stat,
        facet_col="ENSEMBLE",
        facet_col_wrap=fig_columns,
        x="counter",
        y="sim_mean",
        error_y=errory,
        error_y_minus=errory_minus,
        color=colorby,
        range_color=[cmin, cmax],
        # hover_data=list(df_stat.columns),
        hover_data={
            "region": True,
            "ENSEMBLE": False,
            "counter": False,
            "obs": ":.2r",
            # "obs_error": ":.2r",
            "sim_mean": ":.2r",
            # "sim_std": ":.2r",
            "diff_mean": ":.2r",
            # "east": ":,.0f",
            # "north": ":,.0f",
            "data_number": True,
        },
    )
    fig.update_traces(error_y_thickness=1.0, selector=dict(type="scatter"))

    # -----------------------
    obserrory = (
        dict(type="data", array=df_stat["obs_error"], visible=True, thickness=1.0)
        if showerrorbarobs is not None
        else None
    )
    obslegend = colorby == "region"

    fig.add_trace(
        go.Scattergl(
            x=df_stat["counter"],
            y=df_stat["obs"],
            error_y=obserrory,
            mode="markers",
            line_color="gray",
            name="obs",
            showlegend=obslegend,
            opacity=0.5,
        ),
        row="all",
        col="all",
        exclude_empty_subplots=True,
    )
    fig.update_layout(hovermode="closest")

    if reset_index:
        fig.update_xaxes(title_text="data point (index reset, sorted by region)")
    else:
        fig.update_xaxes(title_text="data point (original numbering)")
    if showerrorbar:
        fig.update_yaxes(title_text="Simulated mean w/error")
    else:
        fig.update_yaxes(title_text="Simulated mean")

    fig.update_yaxes(uirevision="true")  # don't update y-range during callbacks
    figures.append(wcc.Graph(figure=fig.to_dict(), style={"height": total_height}))
    return figures


# -------------------------------
def update_errorbarplot_superimpose(
    df: pd.DataFrame,
    showerrorbar: Optional[str] = None,
    showerrorbarobs: Optional[str] = None,
    reset_index: bool = True,
    figheight: int = 450,
) -> Optional[List[wcc.Graph]]:
    """Create errorbar plot of ensemble sim versus obs,
    one value per seismic datapoint."""

    first = True
    figures = []
    ensdf_stat = {}
    data_to_plot = False

    for ens_name, ensdf in df.groupby("ENSEMBLE"):
        logging.debug(f"Seismic errorbar plot; updating {ens_name}")

        # --- drop columns (realizations) with no data
        ensdf = ensdf.dropna(axis="columns")

        # --- make dataframe with statistics per datapoint
        ensdf_stat[ens_name] = df_seis_ens_stat(ensdf, ens_name)
        if not ensdf_stat[ens_name].empty:
            data_to_plot = True
        else:
            break

        del ensdf

        # -------------------------------------------------------------
        errory = None

        if showerrorbar == "sim_std":
            errory = dict(
                type="data",
                array=ensdf_stat[ens_name]["sim_std"],
                visible=True,
                thickness=1.0,
            )
        elif showerrorbar == "sim_p10_p90":
            ensdf_stat[ens_name]["error_plus"] = abs(
                ensdf_stat[ens_name]["sim_mean"] - ensdf_stat[ens_name]["sim_p10"]
            )
            ensdf_stat[ens_name]["error_minus"] = abs(
                ensdf_stat[ens_name]["sim_mean"] - ensdf_stat[ens_name]["sim_p90"]
            )
            errory = dict(
                type="data",
                symmetric=False,
                array=ensdf_stat[ens_name]["error_plus"],
                arrayminus=ensdf_stat[ens_name]["error_minus"],
                visible=True,
                thickness=1.0,
            )

        # -------------------------------------------------------------
        ensdf_stat[ens_name] = ensdf_stat[ens_name].sort_values(by=["region"])
        ensdf_stat[ens_name] = ensdf_stat[ens_name].astype({"region": "string"})

        if reset_index:
            ensdf_stat[ens_name].reset_index(inplace=True)

        ensdf_stat[ens_name]["counter"] = (
            ensdf_stat[ens_name].index + 1
        )  # make new counter after index reset

        # -----------------------
        if first:

            fig = px.scatter()

            obserrory = None
            if showerrorbarobs is not None:
                obserrory = dict(
                    type="data",
                    array=ensdf_stat[ens_name]["obs_error"],
                    visible=True,
                    thickness=1.0,
                )

            fig.add_scattergl(
                x=ensdf_stat[ens_name]["counter"],
                y=ensdf_stat[ens_name]["obs"],
                error_y=obserrory,
                mode="markers",
                line_color="gray",
                name="obs",
                showlegend=True,
            )
            fig.add_scattergl(
                x=ensdf_stat[ens_name]["counter"],
                y=ensdf_stat[ens_name]["sim_mean"],
                mode="markers",
                name=ens_name,
                error_y=errory,
            )
            first = False
        # -----------------------
        else:
            fig.add_scattergl(
                x=ensdf_stat[ens_name]["counter"],
                y=ensdf_stat[ens_name]["sim_mean"],
                mode="markers",
                name=ens_name,
                error_y=errory,
            )

    if not data_to_plot:
        return None

    fig.update_layout(hovermode="x")

    if reset_index:
        fig.update_xaxes(title_text="data point (index reset, sorted by region)")
    else:
        fig.update_xaxes(title_text="data point (original numbering)")
    if showerrorbar:
        fig.update_yaxes(title_text="Simulated mean w/error")
    else:
        fig.update_yaxes(title_text="Simulated mean")

    fig.update_yaxes(uirevision="true")  # don't update y-range during callbacks
    figures.append(wcc.Graph(figure=fig.to_dict(), style={"height": figheight}))
    return figures


def _get_obsdata_col_settings(
    colorby: str,
    obs_range: List[float],
    scale_col: float,
) -> Tuple[List[float], Union[None, float], Any]:
    """return color scale range for obs or obs_error.
    Make obs range symetric and obs_error range positive.
    Adjust range with scale_col value."""

    if colorby == "obs_error":
        lower = obs_range[0]
        upper = max(obs_range[1] * scale_col, lower * 1.01)
        range_col = [lower, upper]
        scale_midpoint = None
        color_scale = ColorScales.SEISMIC_ERROR

    if colorby == "obs":
        abs_max = max(abs(obs_range[0]), abs(obs_range[1]))
        upper = abs_max * scale_col
        lower = -1 * upper
        range_col = [lower, upper]
        scale_midpoint = 0.0
        color_scale = ColorScales.SEISMIC_SYMMETRIC

    return range_col, scale_midpoint, color_scale

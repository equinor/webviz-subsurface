import itertools
from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from webviz_config import WebvizConfigTheme

from ......_utils.colors import StandardColors
from ...._types import NodeType, PressurePlotMode


def create_well_control_figure(
    node_info: Dict[str, Any],
    smry: pd.DataFrame,
    pressure_plot_mode: PressurePlotMode,
    real: int,
    display_ctrlmode_bar: bool,
    shared_xaxes: bool,
    include_bhp: bool,
    theme: WebvizConfigTheme,
) -> Dict:
    # pylint: disable=too-many-locals
    """Creates the plotly figure consisting of multiple subplots, possibly
    sharing the same x-axis.
    """
    node_name = node_info["name"]
    titles = [
        "Number of realizations on different control modes",
        "Network Pressures",
    ]
    rows = 2
    row_heights = [0.5, 0.5]
    if display_ctrlmode_bar and pressure_plot_mode == PressurePlotMode.SINGLE_REAL:
        rows = 3
        display_ctrlmode_bar = True
        row_heights = [0.46, 0.46, 0.08]
        titles.append("Single realization control modes")

    fig = make_subplots(
        rows=rows,
        cols=1,
        shared_xaxes=shared_xaxes,
        vertical_spacing=0.1,
        subplot_titles=titles if titles else ["No vector selected"],
        row_heights=row_heights,
    )
    theme_colors = theme.plotly_theme["layout"]["colorway"]

    # Prepare data
    ctrlmode_sumvec = node_info["ctrlmode_sumvec"]
    smry_ctrlmodes = smry[["DATE", "REAL", ctrlmode_sumvec]].copy()
    # Truncate at -1
    smry_ctrlmodes[ctrlmode_sumvec].clip(-1, None, inplace=True)
    # Replace interpolated values
    smry_ctrlmodes[ctrlmode_sumvec] = smry_ctrlmodes[ctrlmode_sumvec].apply(
        lambda x: "Interpolated" if x % 1 else x
    )

    # Add traces
    add_ctrl_mode_traces(fig, node_info, smry_ctrlmodes)
    add_network_pressure_traces(
        fig, node_info, smry, pressure_plot_mode, real, include_bhp, theme_colors
    )

    if display_ctrlmode_bar and pressure_plot_mode == PressurePlotMode.SINGLE_REAL:
        add_ctrlmode_bar(
            fig,
            node_info,
            smry_ctrlmodes,
            real,
            3,
        )
        fig.update_yaxes(range=[0, 1], row=3, col=1, visible=False)

    fig.update_layout(
        plot_bgcolor="white",
        title=f"Network Analysis for node: {node_name}",
    )
    fig.update_yaxes(
        title="# realizations", range=[0, smry.REAL.nunique()], row=1, col=1
    )
    fig.update_yaxes(autorange="reversed", title="Pressure", row=2, col=1)
    return fig.to_dict()


def add_ctrl_mode_traces(fig: go.Figure, node_info: dict, smry: pd.DataFrame) -> None:
    """Adding area chart traces to the control modes subplot."""
    sumvec = node_info["ctrlmode_sumvec"]
    df = smry.groupby("DATE")[sumvec].value_counts().unstack().fillna(0).reset_index()
    df["Other"] = 0
    categories = get_ctrlmode_categories(node_info["type"])

    for col in [col for col in df.columns if not col in ["DATE", "Other"]]:
        if str(col) in categories:
            name = categories[str(col)]["name"]
            color = categories[str(col)]["color"]
            add_area_trace(fig, df.DATE, df[col], name, color, row=1)
        else:
            df.Other = df.Other + df[col]

    if df.Other.sum() > 0:
        add_area_trace(
            fig,
            df.DATE,
            df.Other,
            categories["Other"]["name"],
            categories["Other"]["color"],
            row=1,
        )


def add_network_pressure_traces(
    fig: go.Figure,
    node_info: Dict[str, Any],
    smry: pd.DataFrame,
    pressure_plot_mode: PressurePlotMode,
    real: int,
    include_bhp: bool,
    theme_colors: list,
) -> None:
    """Adding line traces to the network pressures subplot.

    Missing summary vectors is currently just ignored, but it is possible
    to show a warning or even raise an exception.
    """

    color_iterator = itertools.cycle(theme_colors)
    traces = {}
    for node_network in node_info["networks"]:
        df = get_filtered_smry(
            node_network, node_info["ctrlmode_sumvec"], pressure_plot_mode, real, smry
        )

        for nodedict in node_network["nodes"]:
            if nodedict["type"] == NodeType.WELL_BH and not include_bhp:
                continue
            sumvec = nodedict["pressure"]
            label = nodedict["label"]

            # It the summary vector is not found, do nothing.
            if sumvec in df.columns:
                if label not in traces:
                    traces[label] = {
                        "type": "scatter",
                        "x": [],
                        "y": [],
                        "line": dict(color=next(color_iterator)),
                        "name": label,
                        "showlegend": True,
                        "hovertext": (f"{label}"),
                        "legendgroup": "Nodes",
                        "mode": "lines",
                    }
                traces[label]["x"].extend(list(df["DATE"]))
                traces[label]["y"].extend(list(df[sumvec]))

    for trace in traces.values():
        fig.add_trace(trace, row=2, col=1)


def add_ctrlmode_bar(
    fig: go.Figure, node_info: Dict, smry: pd.DataFrame, real: int, chart_row: int
) -> None:
    # pylint: disable=too-many-locals
    """Adding area traces to the single realization control mode bar"""
    sumvec = node_info["ctrlmode_sumvec"]
    categories = get_ctrlmode_categories(node_info["type"])
    df = smry[smry.REAL == real]
    prev_ctrlmode = df[df.DATE == df.DATE.min()][sumvec].values[0]
    ctrlmode_startdate = df.DATE.min()
    end_date = df.DATE.max()
    start_date = df.DATE.min()

    for _, row in df.iterrows():
        ctrlmode = row[sumvec]
        if ctrlmode != prev_ctrlmode or row.DATE == end_date:
            category = categories[str(prev_ctrlmode)]
            add_area_trace(
                fig,
                [
                    start_date,
                    ctrlmode_startdate,
                    ctrlmode_startdate,
                    row.DATE,
                    row.DATE,
                    end_date,
                ],
                [0, 0, 1, 1, 0, 0],
                category["name"],
                category["color"],
                row=chart_row,
                showlegend=False,
                linewidth=0,
            )
            ctrlmode_startdate = row.DATE
        prev_ctrlmode = ctrlmode


def get_filtered_smry(
    node_network: dict,
    ctrlmode_sumvec: str,
    pressure_plot_mode: PressurePlotMode,
    real: int,
    smry: pd.DataFrame,
) -> pd.DataFrame:
    """Filters the summary dataframe according to the valid
    start and end dates for the network. Removing un-necessary rows/columns
    and averaging over realizations if that option is selected.
    """
    start_date = pd.to_datetime(node_network["start_date"])
    end_date = pd.to_datetime(node_network["end_date"])
    sumvecs = ["REAL", "DATE", ctrlmode_sumvec] + [
        nodedict["pressure"]
        for nodedict in node_network["nodes"]
        if nodedict["pressure"] in smry.columns
    ]
    df = smry[smry.DATE >= start_date][sumvecs]
    if end_date is not None:
        df = df[df.DATE < end_date]

    if pressure_plot_mode == PressurePlotMode.MEAN:
        # Filter out realizations whitout production
        df = df[df[ctrlmode_sumvec] != 0.0]
        # Group by date and take the mean of each group
        df = df.groupby("DATE").mean().reset_index()
    elif pressure_plot_mode == PressurePlotMode.SINGLE_REAL:
        df = df[df.REAL == real]
    return df


def add_area_trace(
    fig: go.Figure,
    x_series: list,
    y_series: list,
    name: str,
    color: str,
    row: int,
    showlegend: bool = True,
    linewidth: float = 0.2,
) -> go.Figure:
    """Adding single area trace to subplot"""
    fig.add_trace(
        go.Scatter(
            x=x_series,
            y=y_series,
            hoverinfo="text+x+y",
            hoveron="fills",
            mode="lines",
            # fill="tonexty",
            # fillcolor=color,
            line=dict(width=linewidth, color=color),
            name=name,
            text=name,
            stackgroup="one",
            legendgroup="Ctrl Modes",
            showlegend=showlegend,
        ),
        row=row,
        col=1,
    )


def get_ctrlmode_categories(node_type: NodeType) -> dict:
    """Returning name and color for the control mode values"""
    if node_type == NodeType.WELL:
        return {
            "0.0": {"name": "SHUT/STOP", "color": "#302f2f"},  # grey
            "1.0": {"name": "ORAT", "color": StandardColors.OIL_GREEN.value},  # green
            "2.0": {"name": "WRAT", "color": StandardColors.WATER_BLUE.value},  # blue
            "3.0": {"name": "GRAT", "color": StandardColors.GAS_RED.value},  # red
            "4.0": {"name": "LRAT", "color": "#b06d15"},  # muted purple
            "5.0": {"name": "RESV", "color": "#67ab99"},  # green/blue
            "6.0": {"name": "THP", "color": "#7e5980"},  # purple
            "7.0": {"name": "BHP", "color": "#1f77b4"},  # muted blue
            "-1.0": {"name": "GRUP", "color": "#cfcc74"},  # yellow
            "Interpolated": {"name": "Interpolated", "color": "#ffffff"},  # white
            "Other": {"name": "Other", "color": "#ffffff"},  # white
        }
    if node_type == NodeType.GROUP:
        return {
            "0.0": {"name": "NONE", "color": "#302f2f"},  # grey
            "1.0": {"name": "ORAT", "color": StandardColors.OIL_GREEN.value},  # green
            "2.0": {"name": "WRAT", "color": StandardColors.WATER_BLUE.value},  # blue
            "3.0": {"name": "GRAT", "color": StandardColors.GAS_RED.value},  # red
            "4.0": {"name": "LRAT", "color": "#b06d15"},  # muted purple
            "5.0": {"name": "RESV", "color": "#67ab99"},  # green/blue
            "6.0": {"name": "PRBL", "color": "#7e5980"},  # purple
            "7.0": {"name": "ENERGY", "color": "#1f77b4"},  # muted blue
            "-ve": {"name": "GRUP", "color": "#cfcc74"},  # yellow
            "Interpolated": {"name": "Interpolated", "color": "#ffffff"},  # white
            "Other": {"name": "Other", "color": "#ffffff"},  # white
        }
    raise ValueError(f"Node type: {node_type} not implemented")

from typing import Dict, Any, List
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_figure(
    node_info: Dict[str, Any],
    smry: pd.DataFrame,
    pressure_plot_options: dict,
) -> dict:
    node_name = node_info["name"]
    titles = [
        f"Number of realizations on different control modes",
        f"Network Pressures",
    ]
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.1,
        subplot_titles=titles if titles else ["No vector selected"],
    )

    add_ctrl_mode_traces(fig, node_info, smry)

    add_network_pressure_traces(fig, node_info, smry, pressure_plot_options)

    fig.update_layout(
        plot_bgcolor="white", title=f"Network Analysis for node: {node_name}"
    )
    fig.update_yaxes(
        title="# realizations", range=[0, smry.REAL.nunique()], row=1, col=1
    )
    fig.update_yaxes(autorange="reversed", title="Pressure", row=2, col=1)
    return fig.to_dict()


def add_ctrl_mode_traces(fig: go.Figure, node_info: dict, smry: pd.DataFrame):
    """Description"""

    sumvec = node_info["ctrlmode_sumvec"]
    df = smry[["DATE", sumvec]].copy()
    df[sumvec].clip(-1, None, inplace=True)

    df = df.groupby("DATE")[sumvec].value_counts().unstack().fillna(0).reset_index()
    df["Other"] = 0
    categories = get_ctrlmode_categories(node_info["type"])

    for col in [col for col in df.columns if not col in ["DATE", "Other"]]:
        if str(col) in categories:
            name = categories[str(col)]["name"]
            color = categories[str(col)]["color"]
            add_area_trace(fig, df.DATE, df[col], name, color)
        else:
            df.Other = df.Other + df[col]

    if df.Other.sum() > 0:
        add_area_trace(
            fig,
            df.DATE,
            df.Other,
            categories["Other"]["name"],
            categories["Other"]["color"],
        )


def add_network_pressure_traces(
    fig: go.Figure,
    node_info: Dict[str, Any],
    smry: pd.DataFrame,
    pressure_plot_options: dict,
) -> go.Figure:
    """Description"""

    for node_network in node_info["networks"]:
        df = get_filtered_smry(
            node_network, node_info["ctrlmode_sumvec"], pressure_plot_options, smry
        )

        for nodedict in node_network["nodes"]:
            if (
                nodedict["type"] == "well_bhp"
                and "include_bhp" not in pressure_plot_options["include_bhp"]
            ):
                continue
            sumvec = nodedict["pressure"]
            label = nodedict["label"]
            if sumvec in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=list(df["DATE"]),
                        y=list(df[sumvec]),
                        name=label,
                        showlegend=True,
                        hovertext=(f"{label}"),
                        legendgroup="Nodes",
                    ),
                    row=2,
                    col=1,
                )
            else:
                print(f"Summary vector {sumvec} not in dataset.")


def get_filtered_smry(
    node_network: dict,
    ctrlmode_sumvec: str,
    pressure_plot_options: dict,
    smry: pd.DataFrame,
) -> pd.DataFrame:
    """Description"""
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
    if pressure_plot_options["mean_or_single_real"] == "plot_mean":
        # Filter out realizations whitout production
        df = df[df[ctrlmode_sumvec] != 0.0]
        # Group by date and take the mean of each group
        df = df.groupby("DATE").mean().reset_index()
    elif pressure_plot_options["mean_or_single_real"] == "single_real":
        df = df[df.REAL == pressure_plot_options["realization"]]
    return df


def add_area_trace(
    fig: go.Figure, x_series: str, y_series: str, name: str, color: str
) -> go.Figure:
    """Description"""
    fig.add_trace(
        go.Scatter(
            x=x_series,
            y=y_series,
            hoverinfo="text+x+y",
            hoveron="fills",
            mode="lines",
            # fill="tonexty",
            # fillcolor=color,
            line=dict(width=0.2, color=color),
            name=name,
            text=name,
            stackgroup="one",
            legendgroup="Ctrl Modes",
        ),
        row=1,
        col=1,
    )


def get_ctrlmode_categories(node_type: str) -> dict:
    """Description"""
    if node_type == "well":
        return {
            "0.0": {"name": "SHUT/STOP", "color": "#302f2f"},  # grey
            "1.0": {"name": "ORAT", "color": "#044a2e"},  # green
            "2.0": {"name": "WRAT", "color": "#10026b"},  # blue
            "3.0": {"name": "GRAT", "color": "#7a0202"},  # red
            "4.0": {"name": "LRAT", "color": "#b06d15"},  # muted purple
            "5.0": {"name": "RESV", "color": "#67ab99"},  # green/blue
            "6.0": {"name": "THP", "color": "#7e5980"},  # purple
            "7.0": {"name": "BHP", "color": "#1f77b4"},  # muted blue
            "-1.0": {"name": "GRUP", "color": "#cfcc74"},  # yellow
            "Other": {"name": "Other", "color": "#ffffff"},  # white
        }
    if node_type == "field_group":
        return {
            "0.0": {"name": "NONE", "color": "#302f2f"},  # grey
            "1.0": {"name": "ORAT", "color": "#044a2e"},  # green
            "2.0": {"name": "WRAT", "color": "#10026b"},  # blue
            "3.0": {"name": "GRAT", "color": "#7a0202"},  # red
            "4.0": {"name": "LRAT", "color": "#b06d15"},  # muted purple
            "5.0": {"name": "RESV", "color": "#67ab99"},  # green/blue
            "6.0": {"name": "PRBL", "color": "#7e5980"},  # purple
            "7.0": {"name": "ENERGY", "color": "#1f77b4"},  # muted blue
            "-ve": {"name": "GRUP", "color": "#cfcc74"},  # yellow
            "Other": {"name": "Other", "color": "#ffffff"},  # white
        }
    raise ValueError(f"Node type: {node_type} not implemented")

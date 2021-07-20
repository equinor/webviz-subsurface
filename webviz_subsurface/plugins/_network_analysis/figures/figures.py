from typing import Dict, Any, List
import pandas as pd
import plotly.graph_objects as go


def make_node_pressure_graph(
    node_networks: List[Dict[str, Any]],
    node_name: str,
    smry: pd.DataFrame,
    pressure_plot_options: dict,
) -> go.Figure:
    """Description"""
    fig = go.Figure()

    for node_network in node_networks:
        df = get_filtered_smry(node_network, pressure_plot_options, smry)

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
                    {
                        "type": "scatter",
                        "x": list(df["DATE"]),
                        "y": list(df[sumvec]),
                        "name": label,
                        "showlegend": True,
                        "hovertext": (f"{label}"),
                    }
                )
            else:
                print(f"Summary vector {sumvec} not in dataset.")

    fig.update_layout(
        title_text=f"Node Pressures - {node_name}",
        yaxis_title="Pressure",
        plot_bgcolor="white",
    )
    fig.update_yaxes(autorange="reversed")

    return fig


def make_area_graph(node_type: str, node: str, smry: pd.DataFrame) -> go.Figure:
    """Description"""
    fig = go.Figure()

    sumvec = get_ctrlmode_sumvec(node_type, node)
    if sumvec not in smry.columns:
        return go.Figure().update_layout(plot_bgcolor="white")
    df = smry[["DATE", sumvec]]
    df = smry.groupby("DATE")[sumvec].value_counts().unstack().fillna(0).reset_index()
    df["Other"] = 0
    categories = get_ctrlmode_categories(node_type)

    for col in [col for col in df.columns if not col in ["DATE", "Other"]]:
        if str(col) in categories:
            name = categories[str(col)]["name"]
            color = categories[str(col)]["color"]
            add_trace(fig, df.DATE, df[col], name, color)
        else:
            df.Other = df.Other + df[col]

    if df.Other.sum() > 0:
        add_trace(
            fig,
            df.DATE,
            df.Other,
            categories["Other"]["name"],
            categories["Other"]["color"],
        )

    fig.update_layout(
        title_text=f"Number of realizations on different control modes - {node}",
        yaxis_title="# realizations",
        yaxis=dict(range=[0, smry.REAL.nunique()]),
        plot_bgcolor="white",
    )

    return fig


def get_filtered_smry(
    node_network: dict, pressure_plot_options: dict, smry: pd.DataFrame
) -> pd.DataFrame:
    """Description"""
    start_date = pd.to_datetime(node_network["start_date"])
    end_date = pd.to_datetime(node_network["end_date"])
    sumvecs = ["REAL", "DATE"] + [
        nodedict["pressure"]
        for nodedict in node_network["nodes"]
        if nodedict["pressure"] in smry.columns
    ]
    df = smry[smry.DATE >= start_date][sumvecs]
    if end_date is not None:
        df = df[df.DATE < end_date]
    if pressure_plot_options["mean_or_single_real"] == "plot_mean":
        df = df.groupby("DATE").mean().reset_index()
    elif pressure_plot_options["mean_or_single_real"] == "single_real":
        df = df[df.REAL == pressure_plot_options["realization"]]
    return df


def get_ctrlmode_sumvec(node_type: str, node: str) -> str:
    """Description"""
    if node == "FIELD":
        return "FMCTP"
    if node_type == "well":
        return f"WMCTL:{node}"
    if node_type == "field_group":
        return f"GMCTP:{node}"
    raise ValueError(f"Node type {node_type} not implemented")


def add_trace(
    fig: go.Figure, x_series: str, y_series: str, name: str, color: str
) -> go.Figure:
    """Description
    Ikke helt sikker paa om retur-typen er riktig her. kanskje den heller burde
    returnere en dict?
    """
    fig.add_trace(
        go.Scatter(
            x=x_series,
            y=y_series,
            hoverinfo="x+y",
            mode="lines",
            line=dict(width=0.5, color=color),
            name=name,
            stackgroup="one",
        )
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

import pandas as pd
import plotly.graph_objects as go

def make_node_pressure_graph(
    node_type: str, node: str, smry: pd.DataFrame
) -> go.Figure():
    """Description"""
    fig = go.Figure()

    sumvec = get_pressure_sumvec(node_type, node, smry)
    if sumvec not in smry.columns:
        return go.Figure().update_layout(plot_bgcolor="white")
    df = smry[["DATE", sumvec]].groupby("DATE").mean().reset_index()
    fig.add_trace(
        {
            "x": list(df["DATE"]),
            "y": list(df[sumvec]),
            "name": sumvec,
            "showlegend": True,
        }
    )

    fig.update_layout(
        title_text="Node Pressures",
        yaxis_title="Pressure",
        plot_bgcolor="white",
    )

    return fig


def make_area_graph(node_type: str, node: str, smry: pd.DataFrame) -> go.Figure():
    """Description"""
    fig = go.Figure()

    sumvec = get_ctrlmode_sumvec(node_type, node, smry)
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
        title_text="Number of realizations on different control modes",
        yaxis_title="# realizations",
        yaxis=dict(range=[0, smry.REAL.nunique()]),
        plot_bgcolor="white",
    )

    return fig


def get_ctrlmode_sumvec(node_type: str, node: str, smry: pd.DataFrame) -> str:
    """Description"""
    if node == "FIELD":
        return "FMCTP"
    elif node_type == "well":
        return f"WMCTL:{node}"
    elif node_type == "field_group":
        return f"GMCTP:{node}"
    else:
        raise ValueError(f"Node type {node_type} not implemented")

def get_pressure_sumvec(node_type: str, node: str, smry: pd.DataFrame) -> str:
    """Description"""
    if node == "FIELD":
        return "FPR"
    elif node_type == "well":
        return f"WTHP:{node}"
    elif node_type == "field_group":
        return f"GPR:{node}"
    else:
        raise ValueError(f"Node type {node_type} not implemented")


def add_trace(fig, x_series, y_series, name, color):
    """Description"""
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


def get_ctrlmode_categories(node_type):
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
    elif node_type == "field_group":
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
    else:
        raise ValueError(f"Node type: {node_type} not implemented")

import plotly.express as px
import plotly.graph_objs as go


def color_figure(
    colors: list,
    bargap: float = None,
    height: float = None,
):
    """
    Create bar chart with colors, can e.g. be used as a color selector
    by retrieving clickdata.
    The color argument is a list of items where the individual items
    are either a name of a built-in plotly colorscale, or a list of colors.
    """
    color_lists = []
    for item in colors:
        if isinstance(item, list) and item:
            color_lists.append(item)
        if isinstance(item, str):
            color_lists.append(get_px_colors(item))

    return go.Figure(
        data=[
            go.Bar(
                orientation="h",
                y=[str(idx)] * len(clist),
                x=[1] * len(clist),
                customdata=list(range(len(clist))),
                marker=dict(color=clist),
                hovertemplate="%{marker.color}<extra></extra>",
            )
            for idx, clist in enumerate(reversed(color_lists))
        ],
        layout=dict(
            title=None,
            barmode="stack",
            barnorm="fraction",
            bargap=bargap if bargap is not None else 0.5,
            showlegend=False,
            xaxis=dict(range=[-0.02, 1.02], showticklabels=False, showgrid=False),
            yaxis_showticklabels=False,
            height=height if height is not None else 20 * len(color_lists),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        ),
    )


def get_px_colors(px_cscale: str):
    for cmodule in [
        px.colors.diverging,
        px.colors.sequential,
        px.colors.cyclical,
        px.colors.qualitative,
    ]:
        if px_cscale in cmodule.__dict__:
            return cmodule.__dict__[px_cscale]
    return []

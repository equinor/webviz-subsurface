import plotly.express as px
import plotly.graph_objs as go


def color_figure(
    px_colors: dict,
    custom_colors: dict = None,
    height: float = None,
):
    """
    Create bar chart with colors, can be used as a color selector
    by retrieving clickdata.
    Input can either be a ditionary with plotly colors with the key
    beeing the px colormodul to use and the value is a list of
    colorscale names, or can be given in as a custom_color dictionary where
    the key is a name and the value is a list of colors.
    """
    custom_colors = custom_colors if custom_colors is not None else {}

    for px_cmodule, px_cscales in px_colors.items():
        if px_cmodule == "diverging":
            custom_colors.update(get_px_colors(px.colors.diverging, px_cscales))
        if px_cmodule == "sequential":
            custom_colors.update(get_px_colors(px.colors.sequential, px_cscales))
        if px_cmodule == "cyclical":
            custom_colors.update(get_px_colors(px.colors.cyclical, px_cscales))
        if px_cmodule == "qualitative":
            custom_colors.update(get_px_colors(px.colors.qualitative, px_cscales))

    return go.Figure(
        data=[
            go.Bar(
                orientation="h",
                y=[name] * len(colors),
                x=[1] * len(colors),
                customdata=list(range(len(colors))),
                marker=dict(color=colors),
                hovertemplate="%{marker.color}<extra></extra>",
            )
            for name, colors in custom_colors.items()
        ],
        layout=dict(
            title=None,
            barmode="stack",
            barnorm="fraction",
            bargap=0.5,
            showlegend=False,
            xaxis=dict(range=[-0.02, 1.02], showticklabels=False, showgrid=False),
            yaxis_showticklabels=False,
            height=height if height is not None else 20 * len(custom_colors),
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        ),
    )


def get_px_colors(px_cmodule, cscales: list):
    return {k: v for (k, v) in px_cmodule.__dict__.items() if k in cscales}

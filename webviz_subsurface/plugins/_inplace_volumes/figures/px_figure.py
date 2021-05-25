import inspect
import plotly.express as px
import plotly.graph_objects as go


def create_figure(plot_type, **kwargs) -> go.Figure:
    """Create subplots for selected parameters"""

    plotargs = set_default_args(**kwargs)

    fig = make_initial_figure(plot_type=plot_type, **plotargs)

    fig = update_xaxes(fig, **plotargs)
    fig = update_yaxes(fig, **plotargs)
    fig = update_layout(fig, plot_type, **plotargs)
    fig = for_each_annotation(fig, **plotargs)

    fig.update_traces(marker_size=15, selector=dict(type="scatter"))
    #    fig.for_each_trace(lambda t: t.update())
    fig.update_traces(marker_line=dict(color="#000000", width=1))
    fig.update_traces(nbinsx=20, selector=dict(type="histogram"))

    if plot_type == "distribution":
        fig = convert_violin_to_distribution_plot(fig, **plotargs)

    return fig


def set_default_args(**plotargs):

    plotargs["histnorm"] = plotargs.get("histnorm", "percent")
    plotargs["barmode"] = plotargs.get("barmode", "group")
    plotargs["opacity"] = plotargs.get("opacity", 0.7)

    if plotargs.get("facet_col") is not None:
        facet_cols = plotargs["data_frame"][plotargs["facet_col"]].nunique()
        plotargs.update(
            facet_col_wrap=min(
                min([x for x in range(100) if (x * (x + 1)) >= facet_cols]),
                20,
            ),
            facet_row_spacing=max((0.08 - (0.00071 * facet_cols)), 0.03),
        )
        plotargs["custom_data"] = [plotargs["facet_col"]]

    return plotargs


def make_initial_figure(plot_type, **plotargs):

    if plot_type == "distribution":
        plot_type = "violin"

    # pylint: disable=protected-access
    plotfunc = getattr(px._chart_types, plot_type)

    valid_plotargs = inspect.signature(plotfunc).parameters.keys()
    plotargs = {arg: value for arg, value in plotargs.items() if arg in valid_plotargs}

    return plotfunc(**plotargs)


def update_xaxes(figure, **kwargs):
    data_frame = kwargs["data_frame"]
    facet_col = kwargs.get("facet_col", None)
    figure.update_xaxes(
        gridwidth=1,
        gridcolor="lightgrey",
        showline=True,
        linewidth=2,
        linecolor="black",
        mirror=True,
        fixedrange=True,
        title=None,
        showticklabels=(data_frame[facet_col].nunique() <= 100)
        if facet_col is not None
        else None,
        tickangle=0,
        tickfont_size=max((20 - (0.4 * data_frame[facet_col].nunique())), 10)
        if facet_col is not None
        else None,
    )
    return figure.update_layout(**kwargs.get("xaxis", {}))


def update_yaxes(figure, **kwargs):
    figure.update_yaxes(
        showline=True,
        linewidth=2,
        linecolor="black",
        mirror=True,
        gridwidth=1,
        gridcolor="lightgrey",
    )
    return figure.update_layout(**kwargs.get("yaxis", {}))


def update_layout(figure, plot_type, **kwargs):
    if plot_type in ["histogram", "bar"]:
        figure.update_layout(
            bargap=0.1,
        )
    figure.update_layout(plot_bgcolor="white")
    return figure.update_layout(**kwargs.get("layout", {}))


def for_each_annotation(figure, **kwargs):
    data_frame = kwargs["data_frame"]
    facet_col = kwargs.get("facet_col", None)
    return figure.for_each_annotation(
        lambda a: a.update(
            text=(a.text.split("=")[-1]),
            visible=data_frame[facet_col].nunique() <= 42
            if facet_col is not None
            else None,
            font_size=max((18 - (0.4 * data_frame[facet_col].nunique())), 10)
            if facet_col is not None
            else None,
        )
    )


def convert_violin_to_distribution_plot(figure, **kwargs):
    figure.for_each_trace(
        lambda t: t.update(
            y0=0,
            hoveron="violins",
            hoverinfo="none",
            meanline_visible=True,
            orientation="h",
            side="positive",
            width=2,
            points=False,
        )
    )
    hovertraces = create_hover_boxes_for_violin_plots(
        figure=figure,
        dframe=kwargs["data_frame"],
        facet_col=kwargs.get("facet_col", None),
        color_col=kwargs.get("color", None),
        x=kwargs["x"],
    )
    for trace in hovertraces:
        figure.add_trace(trace)
    return figure


def create_hover_boxes_for_violin_plots(figure, dframe, x, facet_col, color_col):

    # Create invisible boxes used for hoverinfo on the violin plots
    # Necessary due to https://github.com/plotly/plotly.js/issues/2145
    hovertraces = []
    for trace in figure["data"]:
        hover_text = hover_box_text(trace, dframe, x, facet_col, color_col)
        hovertraces.append(
            go.Scatter(
                x=[min(trace.x), min(trace.x), max(trace.x), max(trace.x)],
                y=[0, 1, 1, 0],
                xaxis=trace.xaxis,
                yaxis=trace.yaxis,
                mode="lines",
                fill="toself",
                opacity=0,
                showlegend=False,
                text=hover_text,
                hoverinfo="text",
                hoverlabel=dict(bgcolor="#E6FAEC", font=dict(color="#243746", size=15)),
            )
        )
    return hovertraces


def hover_box_text(trace, dframe, x, facet_col, color_col):
    colors = list(dframe[color_col].unique()) if color_col in dframe else []
    facet = trace["customdata"][0][0] if trace["customdata"] is not None else ""
    text = f"<b>{x}</b><br>" f"<b>{facet}</b><br>"
    if not colors:
        series = get_filtered_x_series(dframe, x, facet_col, facet)
        text = text + (
            f"Avg: {series.mean():{'.3g'}}<br>" f"Std: {series.std():{'.3g'}}<br>"
        )
    else:
        for color_item in colors:
            series = get_filtered_x_series(
                dframe, x, facet_col, facet, color_col, color_item
            )
            if series.empty:
                continue
            if color_item != facet:
                text = text + f"<b>{color_item}:</b><br>"
            text = text + (
                f"Avg: {series.mean():{'.3g'}}<br>" f"Std: {series.std():{'.3g'}}<br>"
            )
    return text


def get_filtered_x_series(
    dframe, x, facet_col=None, facet=None, color_col=None, color=None
):
    if facet_col is None and color_col is None:
        return dframe[x]
    if facet_col is None and color_col is not None:
        return dframe.loc[dframe[color_col] == color][x]
    if facet_col is not None and color_col is None:
        return dframe.loc[dframe[facet_col] == facet][x]
    if facet_col is not None and color_col is not None:
        return dframe.loc[(dframe[facet_col] == facet) & (dframe[color_col] == color)][
            x
        ]

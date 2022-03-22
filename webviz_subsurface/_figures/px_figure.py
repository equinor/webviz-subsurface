import inspect
from typing import Any, Callable, List, Optional, Union

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pandas.api.types import is_numeric_dtype


def create_figure(plot_type: str, **kwargs: Any) -> go.Figure:
    """Create subplots for selected parameters"""

    if kwargs["data_frame"].empty:
        return empty_figure_layout()

    plotargs = set_default_args(**kwargs)

    fig: go.Figure = make_initial_figure(plot_type=plot_type, **plotargs)
    fig = update_xaxes(fig, plot_type=plot_type, **plotargs)
    fig = update_yaxes(fig, plot_type=plot_type, **plotargs)
    fig = update_layout(fig, **plotargs)
    fig = update_traces(fig, **plotargs)
    fig = for_each_annotation(fig, **plotargs)

    if plot_type == "distribution":
        fig = convert_violin_to_distribution_plot(fig, **plotargs)

    return fig


def set_default_args(**plotargs: Any) -> dict:

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
            facet_col_spacing=max((0.06 - (0.00071 * facet_cols)), 0.03),
        )
        plotargs["custom_data"] = plotargs.get("custom_data", []) + [
            plotargs["facet_col"]
        ]
    return plotargs


def make_initial_figure(plot_type: str, **plotargs: Any) -> Callable:

    if plot_type == "distribution":
        plot_type = "violin"

    # pylint: disable=protected-access
    plotfunc = getattr(px._chart_types, plot_type)

    valid_plotargs = inspect.signature(plotfunc).parameters.keys()
    plotargs = {arg: value for arg, value in plotargs.items() if arg in valid_plotargs}

    return plotfunc(**plotargs)


def update_xaxes(figure: go.Figure, plot_type: str, **kwargs: Any) -> go.Figure:
    data_frame = kwargs["data_frame"]
    facet_col = kwargs.get("facet_col")
    return figure.update_xaxes(
        gridwidth=1,
        gridcolor="#ECECEC",
        showline=kwargs.get("framed", True),
        linewidth=2,
        linecolor="black",
        mirror=True,
        title=None
        if facet_col is not None or not isinstance(kwargs.get("x"), str)
        else kwargs.get("x"),
        showticklabels=(data_frame[facet_col].nunique() <= 100)
        if facet_col is not None
        else None,
        tickangle=0,
        tickfont_size=max((20 - (0.4 * data_frame[facet_col].nunique())), 10)
        if facet_col is not None
        else None,
        fixedrange=plot_type == "distribution",
    ).update_xaxes(**kwargs.get("xaxis", {}))


def update_yaxes(figure: go.Figure, plot_type: str, **kwargs: Any) -> go.Figure:
    return figure.update_yaxes(
        showline=kwargs.get("framed", True),
        linewidth=2,
        linecolor="black",
        mirror=True,
        gridwidth=1,
        gridcolor="#ECECEC",
        fixedrange=plot_type == "distribution",
        showticklabels=plot_type != "distribution",
    ).update_yaxes(**kwargs.get("yaxis", {}))


def update_layout(figure: go.Figure, **kwargs: Any) -> go.Figure:
    return figure.update_layout(plot_bgcolor="white", bargap=0).update_layout(
        **kwargs.get("layout", {})
    )


# pylint: disable=unnecessary-lambda
def update_traces(figure: go.Figure, **kwargs: Any) -> go.Figure:
    data_frame = kwargs["data_frame"]
    facet_col = kwargs.get("facet_col")
    return (
        figure.update_traces(
            marker_size=max((20 - (1.5 * data_frame[facet_col].nunique())), 5)
            if facet_col is not None
            else 20,
            selector=lambda t: t["type"] in ["scatter", "scattergl"],
        )
        .update_traces(textposition="inside", selector=dict(type="pie"))
        .for_each_trace(lambda t: set_marker_color(t))
        .for_each_trace(
            lambda t: t.update(
                xbins_size=(t["x"].max() - t["x"].min()) / kwargs.get("nbins", 15)
            )
            if is_numeric_dtype(t["x"])
            else None,
            selector=dict(type="histogram"),
        )
    )


def set_marker_color(trace: go) -> go:
    marker_attributes = trace.marker.to_plotly_json()
    if (
        "color" in marker_attributes
        and isinstance(trace.marker.color, str)
        and "#" in trace.marker.color
    ):
        opacity = marker_attributes.get(
            "opacity", 0.5 if trace.type in ["scatter", "scattergl"] else 0.7
        )
        trace.update(marker_line=dict(color=trace.marker.color, width=1))
        trace.update(marker_color=hex_to_rgb(trace.marker.color, opacity=opacity))
        trace.update(marker_opacity=1)
    return trace


def for_each_annotation(figure: go.Figure, **kwargs: Any) -> go.Figure:
    data_frame = kwargs["data_frame"]
    facet_col = kwargs.get("facet_col")
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


def empty_figure_layout() -> go.Figure:
    return go.Figure(
        layout=dict(
            xaxis={"visible": False},
            yaxis={"visible": False},
            plot_bgcolor="white",
            annotations=[
                dict(
                    text="No data available for figure",
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font={"size": 20},
                )
            ],
        )
    )


def convert_violin_to_distribution_plot(figure: go.Figure, **kwargs: Any) -> go.Figure:
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


def create_hover_boxes_for_violin_plots(
    figure: go.Figure,
    dframe: pd.DataFrame,
    x: str,
    facet_col: Optional[str],
    color_col: Optional[str],
) -> list:

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


def hover_box_text(
    trace: dict,
    dframe: pd.DataFrame,
    x: str,
    facet_col: Optional[str],
    color_col: Optional[str],
) -> str:
    colors = list(dframe[color_col].unique()) if color_col in dframe else []
    facet = trace["customdata"][-1][0] if trace["customdata"] is not None else ""
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


# pylint: disable=inconsistent-return-statements
def get_filtered_x_series(
    dframe: pd.DataFrame,
    x: str,
    facet_col: Optional[str] = None,
    facet: Optional[str] = None,
    color_col: Optional[str] = None,
    color: Optional[str] = None,
) -> pd.Series:
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


def hex_to_rgb(hex_string: str, opacity: float = 1) -> str:
    """Converts a hex color to rgb"""
    hex_string = hex_string.lstrip("#")
    hlen = len(hex_string)
    rgb: List[Union[int, float]] = [
        int(hex_string[i : i + hlen // 3], 16) for i in range(0, hlen, hlen // 3)
    ]
    rgb.append(opacity)
    return f"rgba{tuple(rgb)}"

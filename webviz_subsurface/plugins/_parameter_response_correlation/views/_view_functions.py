from typing import Any, Dict

import pandas as pd
from plotly.subplots import make_subplots

from webviz_subsurface._figures import create_figure


def make_distribution_plot(df, parameter, response, theme):
    """Make plotly traces for scatterplot and histograms for selected
    response and input parameter"""

    fig = make_subplots(
        rows=4,
        cols=2,
        specs=[
            [{"colspan": 2, "rowspan": 2}, None],
            [None, None],
            [{"rowspan": 2}, {"rowspan": 2}],
            [None, None],
        ],
    )
    scatter_trace, trendline = create_figure(
        plot_type="scatter",
        data_frame=df,
        x=parameter,
        y=response,
        trendline="ols",
        hover_data={"REAL": True},
        color_discrete_sequence=["SteelBlue"],
        marker={"size": 20, "opacity": 0.7},
    ).data

    fig.add_trace(scatter_trace, 1, 1)
    fig.add_trace(trendline, 1, 1)
    fig.add_trace(
        {
            "type": "histogram",
            "x": df[parameter],
            "showlegend": False,
        },
        3,
        1,
    )
    fig.add_trace(
        {
            "type": "histogram",
            "x": df[response],
            "showlegend": False,
        },
        3,
        2,
    )
    fig["layout"].update(
        theme_layout(
            theme.plotly_theme,
            {
                "bargap": 0.05,
                "xaxis": {
                    "title": parameter,
                },
                "yaxis": {"title": response},
                "xaxis2": {"title": parameter},
                "xaxis3": {"title": response},
                "title": f"Distribution of {response} and {parameter}",
            },
        )
    )
    return fig


def make_correlation_plot(
    series, response, theme, corr_method, corr_cutoff, max_parameters
) -> Dict[str, Any]:
    """Make Plotly trace for correlation plot"""
    xaxis_range = max(abs(series.values)) * 1.1
    layout = {
        "barmode": "relative",
        "margin": {"l": 200, "r": 50, "b": 20, "t": 100},
        "xaxis": {"range": [-xaxis_range, xaxis_range]},
        "yaxis": {"dtick": 1},
        "title": (
            f"Correlations between {response} and input parameters<br>"
            f"{corr_method.capitalize()} correlation with abs cut-off {corr_cutoff}"
            f" and max {max_parameters} parameters"
        ),
    }
    layout = theme.create_themed_layout(layout)

    return {
        "data": [
            {"x": series.values, "y": series.index, "orientation": "h", "type": "bar"}
        ],
        "layout": layout,
    }


def theme_layout(theme, specific_layout) -> Dict:
    layout = {}
    layout.update(theme["layout"])
    layout.update(specific_layout)
    return layout


def correlate(inputdf, response, method="pearson") -> pd.DataFrame:
    """Returns the correlation matrix for a dataframe"""
    if method == "pearson":
        corrdf = inputdf.corr(method=method)
    elif method == "spearman":
        corrdf = inputdf.rank().corr(method="pearson")
    else:
        raise ValueError(
            f"Correlation method {method} is invalid. "
            "Available methods are 'pearson' and 'spearman'"
        )
    return corrdf.reindex(corrdf[response].abs().sort_values().index)

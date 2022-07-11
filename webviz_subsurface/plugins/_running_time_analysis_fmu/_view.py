from typing import Callable, List, Optional, Tuple, Type, Union

import pandas as pd
import webviz_core_components as wcc
import webviz_subsurface_components
from dash import Input, Output, callback
from dash.development.base_component import Component
from matplotlib.pyplot import figure
from webviz_config.common_cache import CACHE
from webviz_config.webviz_plugin_subclasses import ViewABC

from ._plugin_ids import PluginIds
from ._shared_settings import RunningTimeAnalysisFmuSettings


class RunTimeAnalysisGraph(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        GRAPH = "graph"
        RUNTIMEANALYSIS = "group-tree"

    def __init__(
            self, 
            plotly_theme: dict,
            job_status_df: pd.DataFrame,
            real_status_df: pd.DataFrame,
            filter_shorter: Union[int, float] = 10
            ) -> None:
        super().__init__("name")
        self.add_column(RunTimeAnalysisGraph.Ids.RUNTIMEANALYSIS)
        #column.add_view_element(wcc.Graph( ), RunTimeAnalysisGraph.Ids.GRAPH)
        self.plotly_theme = plotly_theme
        self.job_status_df = job_status_df
        self.real_status_df = real_status_df
        self.filter_shorter= filter_shorter

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(RunTimeAnalysisGraph.Ids.RUNTIMEANALYSIS)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.MODE), 'data'),
            Input(self.get_store_unique_id(PluginIds.Stores.ENSEMBLE), 'data'),
            Input(self.get_store_unique_id(PluginIds.Stores.COLORING), 'data'),
            Input(self.get_store_unique_id(PluginIds.Stores.FILTERING_SHORT), 'data'),
            Input(self.get_store_unique_id(PluginIds.Stores.FILTERING_PARAMS), 'data')
        )
        def _update_fig(
            mode: str,
            ens: str,
            coloring: str,
            filter_short: List[str],
            params: Union[str, List[str]],
        ) -> dict:
            """Update main figure
            Dependent on `mode` it will call rendering of the chosen form of visualization
            """
            plot_info = None
            if mode == "running_time_matrix":
                if "filter_short" in filter_short:
                    plot_info =  render_matrix(
                        self.job_status_df[
                            (self.job_status_df["ENSEMBLE"] == ens)
                            & (self.job_status_df["JOB_MAX_RUNTIME"] >= self.filter_shorter)
                        ],
                        coloring,
                        self.plotly_theme,
                    )
                else: 
                    plot_info = render_matrix(
                        self.job_status_df[(self.job_status_df["ENSEMBLE"] == ens)],
                        coloring,
                        self.plotly_theme,
                    )

            else: 

                # Otherwise: parallel coordinates
                # Ensure selected parameters is a list
                params = params if isinstance(params, list) else [params]
                # Color by success or runtime, for runtime drop unsuccesful
                colormap_labels: Union[List[str], None]
                if coloring == "Successful/failed realization":
                    plot_df = self.real_status_df[self.real_status_df["ENSEMBLE"] == ens]
                    colormap = make_colormap(
                        self.plotly_theme["layout"]["colorway"], discrete=2
                    )
                    color_by_col = "STATUS_BOOL"
                    colormap_labels = ["Failed", "Success"]
                else:
                    plot_df = self.real_status_df[
                        (self.real_status_df["ENSEMBLE"] == ens)
                        & (self.real_status_df["STATUS_BOOL"] == 1)
                    ]
                    colormap = self.plotly_theme["layout"]["colorscale"]["sequential"]
                    color_by_col = "RUNTIME"
                    colormap_labels = None

                # Call rendering of parallel coordinate plot
                plot_info = render_parcoord(
                    plot_df,
                    params,
                    self.plotly_theme,
                    colormap,
                    color_by_col,
                    colormap_labels,
                )
            return wcc.Graph(
                id = "run-time-analysis-fmu-graph",
                figure = plot_info    
            )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_matrix(status_df: pd.DataFrame, rel: str, theme: dict) -> dict:
    """Render matrix
    Returns figure object as heatmap for the chosen ensemble and scaling method.
    """
    if rel == "Same job in ensemble":
        z = list(status_df["JOB_SCALED_RUNTIME"])
    elif rel == "Slowest job in realization":
        z = list(status_df["REAL_SCALED_RUNTIME"])
    else:
        z = list(status_df["ENS_SCALED_RUNTIME"])
    data = {
        "type": "heatmap",
        "x": list(status_df["REAL"]),
        "y": list(status_df["JOB_ID"]),
        "z": z,
        "zmin": 0,
        "zmax": 1,
        "text": list(status_df["HOVERINFO"]),
        "hoverinfo": "text",
        "colorscale": theme["layout"]["colorscale"]["sequential"],
        "colorbar": {
            "tickvals": [
                0,
                0.5,
                1,
            ],
            "ticktext": [
                "0 %",
                "50 %",
                "100 %",
            ],
            "xanchor": "left",
        },
    }
    layout = {}
    layout.update(theme["layout"])
    layout.update(
        {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": {
                "t": 50,
                "b": 50,
                "l": 50,
            },
            "xaxis": {
                "ticks": "",
                "title": "Realizations",
                "showgrid": False,
                "side": "top",
            },
            "yaxis": {
                "ticks": "",
                "showticklabels": True,
                "tickmode": "array",
                "tickvals": list(status_df["JOB_ID"]),
                "ticktext": list(status_df["JOB"]),
                "showgrid": False,
                "automargin": True,
                "autorange": "reversed",
                "type": "category",
            },
            "height": max(350, len(status_df["JOB_ID"].unique()) * 15),
            "width": max(400, len(status_df["REAL"].unique()) * 12 + 250),
        }
    )

    return {"data": [data], "layout": layout}


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_parcoord(
    plot_df: pd.DataFrame,
    params: List[str],
    theme: dict,
    colormap: Union[List[str], List[list]],
    color_col: str,
    colormap_labels: Union[List[str], None] = None,
) -> dict:
    """Renders parallel coordinates plot"""
    # Create parcoords dimensions (one per parameter)
    dimensions = [
        {"label": param, "values": plot_df[param].values.tolist()} for param in params
    ]

    # Parcoords data dict
    data: dict = {
        "line": {
            "color": plot_df[color_col].values.tolist(),
            "colorscale": colormap,
            "showscale": True,
        },
        "dimensions": dimensions,
        "labelangle": -90,
        "labelside": "bottom",
        "type": "parcoords",
    }
    if color_col == "STATUS_BOOL":
        data["line"].update(
            {
                "cmin": -0.5,
                "cmax": 1.5,
                "colorbar": {
                    "tickvals": [0, 1],
                    "ticktext": colormap_labels,
                    "title": "Status",
                    "xanchor": "right",
                    "x": -0.02,
                    "len": 0.3,
                },
            },
        )
    else:
        data["line"].update(
            {
                "colorbar": {
                    "title": "Running time",
                    "xanchor": "right",
                    "x": -0.02,
                },
            },
        )

    layout = {}
    layout.update(theme["layout"])
    # Ensure sufficient spacing between each dimension and margin for labels
    width = len(dimensions) * 100 + 250
    margin_b = max([len(param) for param in params]) * 8
    layout.update({"width": width, "height": 800, "margin": {"b": margin_b, "t": 30}})
    return {"data": [data], "layout": layout}

@CACHE.memoize(timeout=CACHE.TIMEOUT)
def make_colormap(color_array: list, discrete: int = None) -> list:
    """
    Returns a colormap:
    * If the `discrete` variable is set to an integer x, the colormap will be a discrete map of
    size x evenly sampled from the given color_array.
    * If discrete not defined or `None`: assumes continuous colormap and returns the given
    color_array.
    """
    if discrete is None:
        colormap = color_array
    else:
        colormap = []
        for i in range(0, discrete):
            colormap.append([i / discrete, color_array[i]])
            colormap.append([(i + 1) / discrete, color_array[i]])
    return colormap

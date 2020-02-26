import pandas as pd
from dash.dependencies import Input, Output
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizPluginABC
from webviz_config.common_cache import CACHE

from .._datainput.fmu_input import load_parameters


class ParameterParallelCoordinates(WebvizPluginABC):
    """### ParameterParallelCoordinates

This plugin visualizes parameters used for individual realizations in FMU ensembles.
Useful to investigate initial distributions, and convergence of parameters over multiple iterations

Input:
* `ensembles`: Which ensembles in `shared_settings` to visualize.
* 'visual_parameters': List of default visualized parameteres.
If undefined: all parameters visualized.
"""

    def __init__(self, app, ensembles, visual_parameters=None):

        super().__init__()

        self.ens_paths = {
            ens: app.webviz_settings["shared_settings"]["scratch_ensembles"][ens]
            for ens in ensembles
        }

        self.plotly_theme = app.webviz_settings["theme"].plotly_theme
        self.parameterdf = load_parameters(
            ensemble_paths=self.ens_paths, ensemble_set_name="EnsembleSet"
        )
        # Integer value for each ensemble to be used for colormap
        # self.uuid("COLOR") used to mitigate risk of already having a column named "COLOR" in the
        # DataFrame.
        self.parameterdf[self.uuid("COLOR")] = self.parameterdf.apply(
            lambda row: self.ensembles.index(row["ENSEMBLE"]), axis=1
        )
        self.visual_parameters = (
            visual_parameters if visual_parameters else self.parameters
        )

        self.set_callbacks(app)

    @property
    def parameters(self):
        """Returns numerical input parameters"""
        return list(
            self.parameterdf.drop(["ENSEMBLE", "REAL", self.uuid("COLOR")], axis=1)
            .apply(pd.to_numeric, errors="coerce")
            .dropna(how="all", axis="columns")
            .columns
        )

    @property
    def ensembles(self):
        """Returns list of ensembles"""
        return list(self.parameterdf["ENSEMBLE"].unique())

    @property
    def ens_colormap(self):
        """Returns a discrete colormap with one color per ensemble"""
        colors = self.plotly_theme["layout"]["colorway"]
        colormap = []
        for i in range(0, len(self.ensembles)):
            colormap.append([i / len(self.ensembles), colors[i]])
            colormap.append([(i + 1) / len(self.ensembles), colors[i]])

        return colormap

    @property
    def control_layout(self):
        """Layout to select ensembles and parameters"""
        return html.Div(
            children=[
                html.Div(
                    [
                        html.Span("Selected ensembles:", style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id=self.uuid("ensembles"),
                            options=[
                                {"label": ens, "value": ens} for ens in self.ensembles
                            ],
                            clearable=False,
                            multi=True,
                            value=self.ensembles[0],
                        ),
                    ]
                ),
                html.Div(
                    [
                        html.Span(
                            "Selected parameters:", style={"font-weight": "bold"}
                        ),
                        dcc.Dropdown(
                            id=self.uuid("parameters"),
                            options=[
                                {"label": param, "value": param}
                                for param in self.parameters
                            ],
                            clearable=False,
                            multi=True,
                            value=self.visual_parameters,
                        ),
                    ]
                ),
            ],
        )

    @property
    def layout(self):
        """Main layout"""
        return html.Div(
            id=self.uuid("layout"),
            style=self.set_grid_layout("1fr 4fr"),
            children=[
                self.control_layout,
                html.Div(wcc.Graph(id=self.uuid("parcoords"),),),
            ],
        )

    @staticmethod
    def set_grid_layout(columns):
        return {
            "display": "grid",
            "alignContent": "space-around",
            "justifyContent": "space-between",
            "gridTemplateColumns": f"{columns}",
        }

    def set_callbacks(self, app):
        @app.callback(
            Output(self.uuid("parcoords"), "figure"),
            [
                Input(self.uuid("ensembles"), "value"),
                Input(self.uuid("parameters"), "value"),
            ],
        )
        def _update_parcoord(ens, params):
            """Updates parallel coordinates plot
            Filter dataframe for chosen ensembles and parameters
            Call render_parcoord to render new figure
            """
            # Ensure selected ensembles is a list
            ens = ens if isinstance(ens, list) else [ens]
            # Ensure selected parameters is a list
            params = params if isinstance(params, list) else [params]
            # Filter on ensemble (ens) and active parameters (params),
            # adding the COLOR column to the columns to keep
            params.append(self.uuid("COLOR"))
            plot_df = self.parameterdf[self.parameterdf["ENSEMBLE"].isin(ens)][params]

            return render_parcoord(
                plot_df,
                self.plotly_theme,
                self.ens_colormap,
                self.uuid("COLOR"),
                self.ensembles,
            )


@CACHE.memoize(timeout=CACHE.TIMEOUT)
def render_parcoord(plot_df, theme, colormap, color_col, ens):
    """Renders parallel coordinates plot
    """
    data = []
    # Create parcoords dimensions (one per parameter)
    dimensions = [
        {"label": param, "values": plot_df[param].values.tolist()}
        for param in list(plot_df.columns.drop(color_col))
    ]
    # Parcoords data dict
    data.append(
        {
            "line": {
                "color": plot_df[color_col].values.tolist(),
                "colorscale": colormap,
                "cmin": -0.5,
                "cmax": len(ens) - 0.5,
                "showscale": True,
                "colorbar": {
                    "tickvals": list(range(0, len(ens))),
                    "ticktext": ens,
                    "title": "Ensemble",
                    "xanchor": "right",
                    "x": -0.02,
                    "len": 0.2 * len(ens),
                },
            },
            "dimensions": dimensions,
            "labelangle": -90,
            "labelside": "bottom",
            "type": "parcoords",
        }
    )

    layout = {}
    layout.update(theme["layout"])
    # Ensure sufficient spacing between each dimension and margin for labels
    width = len(dimensions) * 100 + 250
    layout.update({"width": width, "height": 1200, "margin": {"b": 740, "t": 30}})

    return {"data": data, "layout": layout}

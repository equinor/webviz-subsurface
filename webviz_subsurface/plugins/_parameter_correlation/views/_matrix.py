from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
from dash import Input, Output, callback
from webviz_config import WebvizSettings
from webviz_config.webviz_plugin_subclasses import ViewABC

from ...._datainput.fmu_input import scratch_ensemble
from .._plugin_ids import PlugInIDs
from ..view_elements import Graph


class MatrixPlot(ViewABC):
    class IDs:
        # pylint: disable=too-few-public-methods
        MATRIXPLOT = "matrixplot"

    def __init__(
        self,
        ensembles: dict,
        p_cols: List,
        webviz_settings: WebvizSettings,
        drop_constants: bool = True,
    ) -> None:
        super().__init__("Matrix plot")

        self.ensembles = ensembles
        self.p_cols = p_cols
        self.plotly_theme = webviz_settings.theme.plotly_theme
        self.drop_constants = drop_constants

        # Creating the column and row for the setup of the view
        column = self.add_column()
        first_row = column.make_row()
        first_row.add_view_element(
            Graph(),
            MatrixPlot.IDs.MATRIXPLOT,
        )

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(MatrixPlot.IDs.MATRIXPLOT)
                .component_unique_id(Graph.IDs.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.BothPlots.ENSEMBLE), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Horizontal.PARAMETER), "data"
            ),
            Input(
                self.get_store_unique_id(PlugInIDs.Stores.Vertical.PARAMETER), "data"
            ),
        )
        def _update_matrix(
            both_ensemble: str,
            horizontal_paramter: str,
            vertical_parameter: str,
        ) -> dict:
            fig = render_matrix(
                both_ensemble,
                theme=self.plotly_theme,
                drop_constants=self.drop_constants,
            )
            vertical_parameter = horizontal_paramter
            # Finds index of the currently selected cell
            x_index = list(fig["data"][0]["x"]).index(horizontal_paramter)
            y_index = list(fig["data"][0]["y"]).index(vertical_parameter)
            # Adds a shape to highlight the selected cell
            shape = [
                {
                    "xref": "x",
                    "yref": "y",
                    "x0": x_index - 0.5,
                    "y0": y_index - 0.5,
                    "x1": x_index + 0.5,
                    "y1": y_index + 0.5,
                    "type": "rect",
                    "line": {"color": "black"},
                }
            ]
            fig["layout"]["shapes"] = shape
            return fig


def render_matrix(ensemble_path: str, theme: dict, drop_constants: bool = True) -> dict:
    corrdf = get_corr_data(ensemble_path, drop_constants)
    corrdf = corrdf.mask(np.tril(np.ones(corrdf.shape)).astype(np.bool_))

    data = {
        "type": "heatmap",
        "x": corrdf.columns,
        "y": corrdf.columns,
        "z": list(corrdf.values),
        "zmin": -1,
        "zmax": 1,
        "colorscale": theme["layout"]["colorscale"]["sequential"],
    }
    layout = theme_layout(
        theme,
        {
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": {"t": 50, "b": 50},
            "xaxis": {
                "ticks": "",
                "showticklabels": False,
                "showgrid": False,
            },
            "yaxis": {
                "ticks": "",
                "showticklabels": False,
                "showgrid": False,
            },
        },
    )

    return {"data": [data], "layout": layout}


def theme_layout(theme: dict, specific_layout: dict) -> dict:
    layout = {}
    layout.update(theme["layout"])
    layout.update(specific_layout)
    return layout


def get_corr_data(ensemble_path: str, drop_constants: bool = True) -> pd.DataFrame:
    """
    if drop_constants:
    .dropna() removes undefined entries in correlation matrix after
    it is calculated. Correlations between constants yield nan values since
    they are undefined.
    Passing tuple or list to drop on multiple axes is deprecated since
    version 0.23.0. Therefor split in 2x .dropnan()
    """
    data = get_parameters(ensemble_path)

    # Necessary to drop constant before correlations due to
    # https://github.com/pandas-dev/pandas/issues/37448
    if drop_constants is True:
        for col in data.columns:
            if len(data[col].unique()) == 1:
                data = data.drop(col, axis=1)

    return (
        data.corr()
        if not drop_constants
        else data.corr()
        .dropna(axis="index", how="all")
        .dropna(axis="columns", how="all")
    )


def get_parameters(ensemble_path: Path) -> pd.DataFrame:
    return (
        scratch_ensemble("", ensemble_path)
        .parameters.apply(pd.to_numeric, errors="coerce")
        .dropna(how="all", axis="columns")
    )

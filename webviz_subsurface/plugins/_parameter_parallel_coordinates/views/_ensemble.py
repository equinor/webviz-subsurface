from typing import List, Union

import pandas as pd
from dash import Input, Output, callback
from webviz_config import WebvizConfigTheme
from webviz_config.webviz_plugin_subclasses import ViewABC

from ...._utils.unique_theming import unique_colors
from .._plugin_ids import PluginIds
from ..view_elements import Graph
from ._view_functions import render_parcoord


class EnsembleView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        ENSEMBLE_CHART = "ensemble-chart"

    def __init__(
        self,
        parallel_df: pd.DataFrame,
        theme: WebvizConfigTheme,
        parameter_columns: List[str],
        ensembles: List[str],
        ens_colormap: List[str],
    ) -> None:
        super().__init__("Ensemble chart")

        self.parallel_df = parallel_df
        self.parameter_columns = parameter_columns
        self.ensembles = ensembles
        self.ens_colormap = ens_colormap

        column = self.add_column()
        column.add_view_element(Graph(), EnsembleView.Ids.ENSEMBLE_CHART)
        self.theme = theme

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(EnsembleView.Ids.ENSEMBLE_CHART)
                .component_unique_id(Graph.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLE), "data"),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_EXCLUDE_INCLUDE),
                "data",
            ),
            Input(
                self.get_store_unique_id(PluginIds.Stores.SELECTED_PARAMETERS),
                "data",
            ),
        )
        def _update_plot(
            ensemble: str,
            exclude_include: str,
            parameters: List[str],
        ) -> dict:
            ensemble = ensemble if isinstance(ensemble, list) else [ensemble]
            parameters = parameters if isinstance(parameters, list) else [parameters]
            special_columns = ["ENSEMBLE", "REAL"]
            if exclude_include == "exc":
                parallel_df = self.parallel_df.drop(parameters, axis=1)
            elif exclude_include == "inc":
                parallel_df = self.parallel_df[special_columns + parameters]
            params = [
                param
                for param in parallel_df.columns
                if param not in special_columns and param in self.parameter_columns
            ]
            # Filter on ensembles (ens) and active parameters (params),
            # adding the COLOR column to the columns to keep
            df = self.parallel_df[self.parallel_df["ENSEMBLE"].isin(ensemble)][
                params + ["ENSEMBLE"]
            ]
            df["COLOR"] = df.apply(
                lambda row: self.ensembles.index(row["ENSEMBLE"]), axis=1
            )
            return render_parcoord(
                df,
                self.theme,
                self.ens_colormap,
                "COLOR",
                self.ensembles,
                "ensemble",
                params,
                "",
            )

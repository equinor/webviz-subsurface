from typing import List, Tuple, Union

import pandas as pd
from dash import Input, Output, callback
from webviz_config import WebvizSettings
from webviz_config.webviz_plugin_subclasses import ViewABC

from ...._utils.unique_theming import unique_colors
from .._plugin_ids import PluginIds
from ..view_elements import Graph
from ._filter import Filter


class ResponseView(ViewABC):
    class Ids:
        # pylint: disable=too-few-public-methods
        CORRELATIONS = "correlations"
        DISTRIBUTIONS = "distributions"
        SETTINGS = "settings"

    def __init__(
        self,
        response_df: pd.DataFrame,
        webviz_settings: WebvizSettings,
        ensembles: List[str],
        response_filters: dict,
        parameter_columns: list,
        response_columns: List[str],
        aggregation: str,
        corr_method: str,
    ) -> None:
        super().__init__("Response chart")

        self.responsedf = response_df
        self.ensembles = ensembles
        self.response_filters = response_filters
        self.parameter_columns = parameter_columns
        self.response_columns = response_columns
        self.aggregation = aggregation
        self.corr_method = corr_method

        self.add_settings_group(
            Filter(
                self.responsedf,
                self.ensembles,
                self.response_filters,
                self.parameter_columns,
                self.response_columns,
                self.aggregation,
                self.corr_method,
            ),
            ResponseView.Ids.SETTINGS,
        )

        column = self.add_column()
        column.add_view_element(Graph(), ResponseView.Ids.CORRELATIONS)
        column.add_view_element(Graph(), ResponseView.Ids.DISTRIBUTIONS)
        self.theme = webviz_settings.theme

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.view_element(ResponseView.Ids.CORRELATIONS)
                .component_unique_id(Graph.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Output(
                self.view_element(ResponseView.Ids.DISTRIBUTIONS)
                .component_unique_id(Graph.Ids.GRAPH)
                .to_string(),
                "figure",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.SELECTED_ENSEMBLE), "data"),
        )
        def _update_plot(
            ensemble: str,
            sort_by: str,
            ascending: bool,
            n_wells: int,
            wells: Union[str, List[str]],
        ) -> Tuple[dict, dict]:
            return {}

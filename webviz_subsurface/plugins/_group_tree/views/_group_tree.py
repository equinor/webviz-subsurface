from typing import Dict

import webviz_subsurface_components
from dash import Input, Output, callback
from webviz_config.webviz_plugin_subclasses import ViewABC

from .._ensemble_group_tree_data import EnsembleGroupTreeData
from .._plugin_ids import PluginIds
from .._types import NodeType, StatOptions, TreeModeOptions


class GroupTreeGraph(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        GRAPH = "graph"
        GROUPTREE = "group-tree"

    def __init__(self, group_tree_data: Dict[str, EnsembleGroupTreeData]) -> None:
        super().__init__("")
        self.add_column(GroupTreeGraph.Ids.GRAPH)
        self.group_tree_data = group_tree_data

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.layout_element(GroupTreeGraph.Ids.GRAPH)
                .get_unique_id()
                .to_string(),
                "children",
            ),
            Input(self.get_store_unique_id(PluginIds.Stores.TREEMODE), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.STATISTICS), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.REALIZATION), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.FILTER), "data"),
            Input(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES), "data"),
        )
        def _render_grouptree(
            tree_mode_state: str,
            stat_option_state: str,
            real: int,
            node_types: list,
            ensemble_name: str,
        ) -> list:
            """This callback updates the input dataset to the Grouptree component."""
            tree_mode = (
                TreeModeOptions(tree_mode_state)
                if tree_mode_state is not None
                else TreeModeOptions.STATISTICS
            )
            stat_option = (
                StatOptions(stat_option_state)
                if stat_option_state is not None
                else StatOptions.MEAN
            )

            data, edge_options, node_options = self.group_tree_data[
                ensemble_name
            ].create_grouptree_dataset(
                TreeModeOptions(tree_mode),
                StatOptions(stat_option),
                real,
                [NodeType(tpe) for tpe in node_types],
            )

            return [
                webviz_subsurface_components.GroupTree(
                    id="grouptree",
                    data=data,
                    edge_options=edge_options,
                    node_options=node_options,
                ),
            ]

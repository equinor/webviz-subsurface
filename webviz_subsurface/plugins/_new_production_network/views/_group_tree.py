from typing import Dict
from click import style

from dash import callback, Input, Output
from webviz_config.webviz_plugin_subclasses import ViewABC
from webviz_config import WebvizSettings
import webviz_subsurface_components
import webviz_core_components as wcc

from .._plugin_Ids import PluginIds
from .._ensemble_group_tree_data import EnsembleGroupTreeData
from .._types import NodeType, StatOptions, TreeModeOptions

class GroupTreeGraph(ViewABC):

    class Ids:
        GRAPH = "graph"
        GROUPTREE = "group-tree"

    def __init__(self, group_tree_data: Dict[str, EnsembleGroupTreeData], webviz_settings: WebvizSettings) -> None:
        super().__init__("")
        column = self.add_column(GroupTreeGraph.Ids.GRAPH)
        self.group_tree_data = group_tree_data 
    
    def set_callbacks(self) -> None:
        @callback(
            Output(self.layout_element(GroupTreeGraph.Ids.GRAPH).get_unique_id().to_string(), 'children'),
            Input(self.get_store_unique_id(PluginIds.Stores.ENSEMBLES),'data'),
            Input(self.get_store_unique_id(PluginIds.Stores.TREEMODE),'data'),
            Input(self.get_store_unique_id(PluginIds.Stores.STATISTICS),'data'),
            Input(self.get_store_unique_id(PluginIds.Stores.REALIZATION),'data'),
            Input(self.get_store_unique_id(PluginIds.Stores.FILTER),'data'),
        )
        def _update_group_tree (ensemble_name: str, tree_mode: str, stat_option: str, real: int,node_types: list):
            if stat_option is None:
                stat_option = StatOptions.MEAN.value

            data, edge_options, node_options = self.group_tree_data[ensemble_name
                ].create_grouptree_dataset(
                    TreeModeOptions(tree_mode),
                    StatOptions(stat_option),
                    real,
                    [NodeType(tpe) for tpe in node_types],
                )
                
            current_tree = wcc.WebvizViewElement(
                id = self.unique_id(GroupTreeGraph.Ids.GROUPTREE),
                children= webviz_subsurface_components.GroupTree(
                    id="grouptree",
                    data=data,
                    edge_options=edge_options,
                    node_options=node_options,)
            )

            return current_tree
            
           





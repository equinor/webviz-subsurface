from typing import Any, Dict, List, Optional, Tuple

import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import Input, Output, State, callback, html
from dash.development.base_component import Component
from webviz_config.utils import StrEnum, callback_typecheck
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from ..._types import NodeType, StatOptions, TreeModeOptions
from ..._utils import EnsembleGroupTreeData
from ._view_element import GroupTreeViewElement


class ViewControls(SettingsGroupABC):
    class Ids(StrEnum):
        ENSEMBLE = "ensemble"
        TREEMODE = "tree-mode"

    def __init__(self, ensembles: List[str]) -> None:
        super().__init__("Controls")
        self._ensembles = ensembles

    def layout(self) -> List[Component]:
        return [
            wcc.Dropdown(
                id=self.register_component_unique_id(self.Ids.ENSEMBLE),
                label="Ensemble",
                clearable=False,
                options=[{"label": ens, "value": ens} for ens in self._ensembles],
                value=self._ensembles[0],
            ),
            wcc.RadioItems(
                id=self.register_component_unique_id(self.Ids.TREEMODE),
                label="Statistics or realization",
            ),
        ]


class ViewOptions(SettingsGroupABC):
    class Ids(StrEnum):
        STATISTICAL_OPTIONS = "statistical-options"
        STATISTICS = "statistics"
        SINGLE_REAL_OPTIONS = "single-real-options"
        REALIZATION = "realization"

    def __init__(self, group_tree_data: Dict[str, EnsembleGroupTreeData]) -> None:
        super().__init__("Options")
        self.group_tree_data = group_tree_data

    def layout(self) -> List[Component]:
        return [
            html.Div(
                id=self.register_component_unique_id(
                    ViewOptions.Ids.STATISTICAL_OPTIONS
                ),
                children=[
                    wcc.RadioItems(
                        id=self.register_component_unique_id(
                            ViewOptions.Ids.STATISTICS
                        ),
                        options=[
                            {"label": "Mean", "value": StatOptions.MEAN},
                            {"label": "P10 (high)", "value": StatOptions.P10},
                            {
                                "label": "P50 (median)",
                                "value": StatOptions.P50,
                            },
                            {"label": "P90 (low)", "value": StatOptions.P90},
                            {"label": "Maximum", "value": StatOptions.MAX},
                            {"label": "Minimum", "value": StatOptions.MIN},
                        ],
                    )
                ],
            ),
            html.Div(
                id=self.register_component_unique_id(
                    ViewOptions.Ids.SINGLE_REAL_OPTIONS
                ),
                children=[
                    wcc.Dropdown(
                        label="Realization",
                        id=self.register_component_unique_id(
                            ViewOptions.Ids.REALIZATION
                        ),
                        options=[],
                        value=None,
                        multi=False,
                    )
                ],
            ),
        ]


class ViewFilters(SettingsGroupABC):
    class Ids(StrEnum):
        TOUR_STEP = "tour-step"
        PROD_INJ_OTHER = "prod-inj-other"

    def __init__(self) -> None:
        super().__init__("Filters")

    def layout(self) -> html.Div:
        return html.Div(
            id=self.register_component_unique_id(self.Ids.TOUR_STEP),
            children=[
                wcc.SelectWithLabel(
                    id=self.register_component_unique_id(self.Ids.PROD_INJ_OTHER),
                    label="Prod/Inj/Other",
                    options=[
                        {"label": "Production", "value": NodeType.PROD},
                        {"label": "Injection", "value": NodeType.INJ},
                        {"label": "Other", "value": NodeType.OTHER},
                    ],
                    value=[
                        NodeType.PROD,
                        NodeType.INJ,
                        NodeType.OTHER,
                    ],
                    multi=True,
                    size=3,
                )
            ],
        )


class GroupTreeView(ViewABC):
    class Ids(StrEnum):
        VIEW_ELEMENT = "view-element"
        CONTROLS = "controls"
        OPTIONS = "options"
        FILTERS = "filters"
        GROUPTREE_COMPONENT = "grouptree-component"

    def __init__(self, group_tree_data: Dict[str, EnsembleGroupTreeData]) -> None:
        super().__init__("Group Tree")
        self._group_tree_data = group_tree_data

        self.add_settings_group(
            ViewControls(list(self._group_tree_data.keys())), GroupTreeView.Ids.CONTROLS
        )
        self.add_settings_group(
            ViewOptions(self._group_tree_data), GroupTreeView.Ids.OPTIONS
        )
        self.add_settings_group(ViewFilters(), GroupTreeView.Ids.FILTERS)

        main_column = self.add_column()
        main_column.add_view_element(
            GroupTreeViewElement(), GroupTreeView.Ids.VIEW_ELEMENT
        )
        self._group_tree_component_id = self.view_element(
            GroupTreeView.Ids.VIEW_ELEMENT
        ).register_component_unique_id(GroupTreeView.Ids.GROUPTREE_COMPONENT)

    def set_callbacks(self) -> None:
        @callback(
            Output(
                self.settings_group(GroupTreeView.Ids.CONTROLS)
                .component_unique_id(ViewControls.Ids.TREEMODE)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(GroupTreeView.Ids.CONTROLS)
                .component_unique_id(ViewControls.Ids.TREEMODE)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.STATISTICS)
                .to_string(),
                "value",
            ),
            Output(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.REALIZATION)
                .to_string(),
                "options",
            ),
            Output(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(GroupTreeView.Ids.CONTROLS)
                .component_unique_id(ViewControls.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
            State(
                self.settings_group(GroupTreeView.Ids.CONTROLS)
                .component_unique_id(ViewControls.Ids.TREEMODE)
                .to_string(),
                "value",
            ),
            State(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.STATISTICS)
                .to_string(),
                "value",
            ),
            State(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _update_ensemble_options(
            ensemble_name: str,
            tree_mode_state: Optional[TreeModeOptions],
            stat_option_state: Optional[StatOptions],
            real_state: Optional[int],
        ) -> Tuple[List[Dict[str, Any]], str, str, List[Dict[str, Any]], Optional[int]]:
            """Updates the selection options when the ensemble value changes"""
            tree_mode_options: List[Dict[str, Any]] = [
                {
                    "label": "Statistics",
                    "value": TreeModeOptions.STATISTICS,
                },
                {
                    "label": "Single realization",
                    "value": TreeModeOptions.SINGLE_REAL,
                },
            ]
            tree_mode = (
                tree_mode_state
                if tree_mode_state is not None
                else TreeModeOptions.STATISTICS
            )
            stat_option = (
                stat_option_state if stat_option_state is not None else StatOptions.MEAN
            )

            ensemble = self._group_tree_data[ensemble_name]
            if not ensemble.tree_is_equivalent_in_all_real():
                tree_mode_options[0]["label"] = "Ensemble mean (disabled)"
                tree_mode_options[0]["disabled"] = True
                tree_mode = TreeModeOptions.SINGLE_REAL

            unique_real = ensemble.get_unique_real()

            return (
                tree_mode_options,
                tree_mode,
                stat_option,
                [{"label": real, "value": real} for real in unique_real],
                real_state if real_state in unique_real else min(unique_real),
            )

        @callback(
            Output(
                self.view_element(GroupTreeView.Ids.VIEW_ELEMENT)
                .component_unique_id(GroupTreeViewElement.Ids.COMPONENT)
                .to_string(),
                "children",
            ),
            Input(
                self.settings_group(GroupTreeView.Ids.CONTROLS)
                .component_unique_id(ViewControls.Ids.TREEMODE)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.STATISTICS)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.REALIZATION)
                .to_string(),
                "value",
            ),
            Input(
                self.settings_group(GroupTreeView.Ids.FILTERS)
                .component_unique_id(ViewFilters.Ids.PROD_INJ_OTHER)
                .to_string(),
                "value",
            ),
            State(
                self.settings_group(GroupTreeView.Ids.CONTROLS)
                .component_unique_id(ViewControls.Ids.ENSEMBLE)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _render_grouptree(
            tree_mode: TreeModeOptions,
            stat_option: StatOptions,
            real: int,
            node_types: List[NodeType],
            ensemble_name: str,
        ) -> list:
            """This callback updates the input dataset to the Grouptree component."""
            data, edge_options, node_options = self._group_tree_data[
                ensemble_name
            ].create_grouptree_dataset(
                tree_mode,
                stat_option,
                real,
                node_types,
            )

            return [
                wsc.GroupTree(
                    id=self._group_tree_component_id,
                    data=data,
                    edge_options=edge_options,
                    node_options=node_options,
                ),
            ]

        @callback(
            Output(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.STATISTICAL_OPTIONS)
                .to_string(),
                "style",
            ),
            Output(
                self.settings_group(GroupTreeView.Ids.OPTIONS)
                .component_unique_id(ViewOptions.Ids.SINGLE_REAL_OPTIONS)
                .to_string(),
                "style",
            ),
            Input(
                self.settings_group(GroupTreeView.Ids.CONTROLS)
                .component_unique_id(ViewControls.Ids.TREEMODE)
                .to_string(),
                "value",
            ),
        )
        @callback_typecheck
        def _show_hide_single_real_options(
            tree_mode: TreeModeOptions,
        ) -> Tuple[Dict[str, str], Dict[str, str]]:
            if tree_mode is TreeModeOptions.STATISTICS:
                return {"display": "block"}, {"display": "none"}
            return {"display": "none"}, {"display": "block"}

from typing import Any, Dict, List, Optional, Tuple

import webviz_core_components as wcc
import webviz_subsurface_components
from dash import Input, Output, State, callback, html
from webviz_config.webviz_plugin_subclasses import SettingsGroupABC, ViewABC

from .._ensemble_group_tree_data import EnsembleGroupTreeData
from .._types import NodeType, StatOptions, TreeModeOptions
from ..view_elements import GroupTreeViewElement


class ViewControls(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        TOUR_STEP = "tour-step"
        ENSEMBLE = "ensemble"
        TREEMODE = "tree-mode"

    def __init__(self, ensembles: List[str]) -> None:
        super().__init__("Controls")
        self._ensembles = ensembles

    def layout(self) -> html.Div:
        return html.Div(
            id=self.register_component_unique_id(self.Ids.TOUR_STEP),
            children=[
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
            ],
        )


class ViewOptions(SettingsGroupABC):

    # pylint: disable=too-few-public-methods
    class Ids:
        TOUR_STEP = "tour-step"
        STATISTICAL_OPTIONS = "statistical-options"
        STATISTICS = "statistics"
        SINGLE_REAL_OPTIONS = "single-real-options"
        REALIZATION = "realization"

    def __init__(self, group_tree_data: Dict[str, EnsembleGroupTreeData]) -> None:
        super().__init__("Options")
        self.group_tree_data = group_tree_data

    def layout(self) -> html.Div:
        return html.Div(
            id=self.register_component_unique_id(ViewOptions.Ids.TOUR_STEP),
            children=[
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
                                {"label": "Mean", "value": StatOptions.MEAN.value},
                                {"label": "P10 (high)", "value": StatOptions.P10.value},
                                {
                                    "label": "P50 (median)",
                                    "value": StatOptions.P50.value,
                                },
                                {"label": "P90 (low)", "value": StatOptions.P90.value},
                                {"label": "Maximum", "value": StatOptions.MAX.value},
                                {"label": "Minimum", "value": StatOptions.MIN.value},
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
            ],
        )


class ViewFilters(SettingsGroupABC):
    # pylint: disable=too-few-public-methods
    class Ids:
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
                        {"label": "Production", "value": NodeType.PROD.value},
                        {"label": "Injection", "value": NodeType.INJ.value},
                        {"label": "Other", "value": NodeType.OTHER.value},
                    ],
                    value=[
                        NodeType.PROD.value,
                        NodeType.INJ.value,
                        NodeType.OTHER.value,
                    ],
                    multi=True,
                    size=3,
                )
            ],
        )


class GroupTreeView(ViewABC):
    # pylint: disable=too-few-public-methods
    class Ids:
        VIEW_ELEMENT = "view-element"
        CONTROLS = "controls"
        OPTIONS = "options"
        FILTERS = "filters"

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
        def _update_ensemble_options(
            ensemble_name: str,
            tree_mode_state: str,
            stat_option_state: str,
            real_state: int,
        ) -> Tuple[List[Dict[str, Any]], str, str, List[Dict[str, Any]], Optional[int]]:
            """Updates the selection options when the ensemble value changes"""
            tree_mode_options: List[Dict[str, Any]] = [
                {
                    "label": "Statistics",
                    "value": TreeModeOptions.STATISTICS.value,
                },
                {
                    "label": "Single realization",
                    "value": TreeModeOptions.SINGLE_REAL.value,
                },
            ]
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

            ensemble = self._group_tree_data[ensemble_name]
            if not ensemble.tree_is_equivalent_in_all_real():
                tree_mode_options[0]["label"] = "Ensemble mean (disabled)"
                tree_mode_options[0]["disabled"] = True
                tree_mode = TreeModeOptions.SINGLE_REAL

            unique_real = ensemble.get_unique_real()

            return (
                tree_mode_options,
                tree_mode.value,
                stat_option.value,
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
        def _render_grouptree(
            tree_mode: str,
            stat_option: str,
            real: int,
            node_types: list,
            ensemble_name: str,
        ) -> list:
            """This callback updates the input dataset to the Grouptree component."""
            data, edge_options, node_options = self._group_tree_data[
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
        def _show_hide_single_real_options(
            tree_mode: str,
        ) -> Tuple[Dict[str, str], Dict[str, str]]:
            if TreeModeOptions(tree_mode) is TreeModeOptions.STATISTICS:
                return {"display": "block"}, {"display": "none"}
            return {"display": "none"}, {"display": "block"}

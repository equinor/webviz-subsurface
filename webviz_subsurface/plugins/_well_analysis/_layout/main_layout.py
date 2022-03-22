from typing import Callable, Dict

import webviz_core_components as wcc

from .._ensemble_well_analysis_data import EnsembleWellAnalysisData
from .well_control_layout import well_control_tab
from .well_overview_layout import well_overview_tab


def main_layout(
    get_uuid: Callable, data_models: Dict[str, EnsembleWellAnalysisData]
) -> wcc.Tabs:
    """Main layout"""
    tabs = [
        wcc.Tab(
            label="Well Overview", children=well_overview_tab(get_uuid, data_models)
        ),
        wcc.Tab(label="Well Control", children=well_control_tab(get_uuid, data_models)),
    ]
    return wcc.Tabs(children=tabs)

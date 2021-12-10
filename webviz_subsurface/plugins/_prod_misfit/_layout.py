from typing import Callable, Dict, List, Optional

import dash_bootstrap_components as dbc
import dash_html_components as html
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from dash import dash_table, dcc
from webviz_subsurface_components import ExpressionInfo

from ..._providers import Frequency
from ..._utils.vector_calculator import get_custom_vector_definitions_from_expressions

# from .types import (
#     FanchartOptions,
#     StatisticsOptions,
#     TraceOptions,
#     VisualizationOptions,
# )


# pylint: disable=too-few-public-methods
class LayoutElements:
    """
    Definition of names of HTML-elements in layout.
    """

    PROD_MISFIT_LAYOUT = "prod_misfit_layout"
    PROD_MISFIT_ENSEMBLE_NAMES = "prod_misfit_ensemble_names"
    PROD_MISFIT_DATES = "prod_misfit_dates"
    PROD_MISFIT_PHASES = "prod_misfit_phases"
    PROD_MISFIT_WELL_NAMES = "prod_misfit_well_names"
    PROD_MISFIT_WELL_COLLECTIONS = "prod_misfit_well_collections"
    PROD_MISFIT_COMBINE = "prod_misfit_combine"
    PROD_MISFIT_REALIZATIONS = "prod_misfit_realizations"
    PROD_MISFIT_COLORBY = "prod_misfit_colorby"
    PROD_MISFIT_SORTING = "prod_misfit_sorting"
    PROD_MISFIT_FIGHEIGHT = "prod_misfit_figheight"
    PROD_MISFIT_OBS_ERROR_WEIGHT = "prod_misfit_obs_error_weight"
    PROD_MISFIT_EXPONENT = "prod_misfit_exponent"
    # PROD_MISFIT_NORMALIZATION = "prod_misfit_normalization"
    PROD_MISFIT_GRAPH = "prod_misfit_graph"

    WELL_COVERAGE_LAYOUT = "well_coverage_layout"
    WELL_COVERAGE_ENSEMBLE_NAMES = "well_coverage_ensemble_names"
    WELL_COVERAGE_DATES = "well_coverage_dates"
    WELL_COVERAGE_PHASES = "well_coverage_phases"
    WELL_COVERAGE_WELL_NAMES = "well_coverage_well_names"
    WELL_COVERAGE_WELL_COLLECTIONS = "well_coverage_well_collections"
    WELL_COVERAGE_COMBINE = "well_coverage_combine"
    WELL_COVERAGE_REALIZATIONS = "well_coverage_realizations"
    WELL_COVERAGE_COLORBY = "well_coverage_colorby"
    WELL_COVERAGE_SORTING = "well_coverage_sorting"
    WELL_COVERAGE_FIGHEIGHT = "well_coverage_figheight"
    WELL_COVERAGE_PLOT_TYPE = "well_coverage_plot_type"
    WELL_COVERAGE_GRAPH = "well_coverage_graph"


# --- layout ---
def main_layout(
    get_uuid: Callable,
    ensemble_names: List[str],
    dates: Dict[str, List[str]],
    phases: Dict[str, List[str]],
    wells: Dict[str, List[str]],
    realizations: Dict[str, List[int]],
    well_collections: Dict[str, List[str]],
) -> wcc.Tabs:

    all_dates = []
    all_phases = []
    all_wells = []
    all_realizations = []
    for ens_name in ensemble_names:
        all_dates.extend(dates[ens_name])
        all_phases.extend(phases[ens_name])
        all_wells.extend(wells[ens_name])
        all_realizations.extend(realizations[ens_name])
    all_dates = list(sorted(set(all_dates)))
    all_phases = list(sorted(set(all_phases)))
    all_wells = list(sorted(set(all_wells)))
    all_realizations = list(sorted(set(all_realizations)))
    all_well_collection_names = []
    for collection_name in well_collections.keys():
        all_well_collection_names.append(collection_name)

    tabs_styles = {"height": "60px", "width": "100%"}

    tab_style = {
        "borderBottom": "1px solid #d6d6d6",
        "padding": "6px",
        "fontWeight": "bold",
    }

    tab_selected_style = {
        "borderTop": "1px solid #d6d6d6",
        "borderBottom": "1px solid #d6d6d6",
        "backgroundColor": "#007079",
        "color": "white",
        "padding": "6px",
    }

    return wcc.Tabs(
        style=tabs_styles,
        children=[
            wcc.Tab(
                label="Production misfit per real",
                style=tab_style,
                selected_style=tab_selected_style,
                children=_misfit_per_real_layout(
                    get_uuid,
                    ensemble_names,
                    all_dates,
                    all_phases,
                    all_wells,
                    all_well_collection_names,
                    all_realizations,
                ),
            ),
            wcc.Tab(
                label="Well production coverage",
                style=tab_style,
                selected_style=tab_selected_style,
                children=_well_prod_coverage(
                    get_uuid,
                    ensemble_names,
                    all_dates,
                    all_phases,
                    all_wells,
                    all_well_collection_names,
                    all_realizations,
                ),
            ),
            # wcc.Tab(
            #     label="Group production coverage",
            #     style=tab_style,
            #     selected_style=tab_selected_style,
            #     children=_group_prod_coverage(),
            # ),
            # wcc.Tab(
            #     label="Well production heatmap",
            #     style=tab_style,
            #     selected_style=tab_selected_style,
            #     children=_heatmap(),
            # ),
        ],
    )


# --- layout functions ---
def _misfit_per_real_layout(
    get_uuid: Callable,
    ensemble_names: List[str],
    dates: List[str],
    phases: List[str],
    wells: List[str],
    all_well_collection_names: List[str],
    realizations: List[int],
) -> list:
    children = [
        wcc.FlexBox(
            id=get_uuid(LayoutElements.PROD_MISFIT_LAYOUT),
            children=[
                wcc.Frame(
                    style={
                        "flex": 1,
                        "height": "85vh",
                        "maxWidth": "200px",
                    },
                    children=[
                        wcc.Selectors(
                            label="Case settings",
                            children=[
                                wcc.Dropdown(
                                    label="Ensemble selector",
                                    id=get_uuid(
                                        LayoutElements.PROD_MISFIT_ENSEMBLE_NAMES
                                    ),
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in ensemble_names
                                    ],
                                    value=ensemble_names[:2],
                                    multi=True,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Filter settings",
                            children=[
                                wcc.SelectWithLabel(
                                    label="Date selector",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_DATES),
                                    options=[
                                        {
                                            "label": _date.strftime("%Y-%m-%d"),
                                            "value": str(_date),
                                        }
                                        for _date in dates
                                    ],
                                    value=[str(dates[-1])],
                                    size=min([len(dates), 5]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Phase selector",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_PHASES),
                                    options=[
                                        {"label": phase, "value": phase}
                                        for phase in phases
                                    ],
                                    value=phases,
                                    size=min([len(phases), 3]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Well selector",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_WELL_NAMES),
                                    options=[
                                        {"label": well, "value": well} for well in wells
                                    ],
                                    value=wells,
                                    size=min([len(wells), 9]),
                                ),
                                wcc.RadioItems(
                                    label="Combine wells and collections as",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_COMBINE),
                                    options=[
                                        {
                                            "label": "Intersection",
                                            "value": "intersection",
                                        },
                                        {"label": "Union", "value": "union"},
                                    ],
                                    value="intersection",
                                ),
                                wcc.SelectWithLabel(
                                    label="Well collection selector",
                                    id=get_uuid(
                                        LayoutElements.PROD_MISFIT_WELL_COLLECTIONS
                                    ),
                                    options=[
                                        {"label": collection, "value": collection}
                                        for collection in all_well_collection_names
                                    ],
                                    value=all_well_collection_names,
                                    size=min([len(wells), 5]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Realization selector",
                                    id=get_uuid(
                                        LayoutElements.PROD_MISFIT_REALIZATIONS
                                    ),
                                    options=[
                                        {"label": real, "value": real}
                                        for real in realizations
                                    ],
                                    value=realizations,
                                    size=min([len(wells), 5]),
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Plot settings and layout",
                            open_details=True,
                            children=[
                                wcc.Dropdown(
                                    label="Colorby",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_COLORBY),
                                    options=[
                                        {
                                            "label": "Total misfit",
                                            "value": "misfit",
                                        },
                                        {"label": "Phases", "value": "Phases"},
                                        {"label": "Date", "value": "Date"},
                                        {"label": "None", "value": None},
                                    ],
                                    value="misfit",
                                    multi=False,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                wcc.Dropdown(
                                    label="Sorting/ranking",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_SORTING),
                                    options=[
                                        {
                                            "label": "None",
                                            "value": None,
                                        },
                                        {
                                            "label": "Ascending",
                                            "value": "total ascending",
                                        },
                                        {
                                            "label": "Descending",
                                            "value": "total descending",
                                        },
                                    ],
                                    value="total ascending",
                                    multi=False,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                wcc.Dropdown(
                                    label="Fig layout - height",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_FIGHEIGHT),
                                    options=[
                                        {
                                            "label": "Very small",
                                            "value": 250,
                                        },
                                        {
                                            "label": "Small",
                                            "value": 350,
                                        },
                                        {
                                            "label": "Medium",
                                            "value": 450,
                                        },
                                        {
                                            "label": "Large",
                                            "value": 700,
                                        },
                                        {
                                            "label": "Very large",
                                            "value": 1000,
                                        },
                                    ],
                                    value=450,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Misfit options",
                            open_details=True,  # False,
                            children=[
                                wcc.Dropdown(
                                    label="Misfit weight",
                                    id=get_uuid(
                                        LayoutElements.PROD_MISFIT_OBS_ERROR_WEIGHT
                                    ),
                                    options=[
                                        {
                                            "label": "Config weight reduction factors",
                                            "value": -1.0,
                                        },
                                        {"label": "None", "value": 0.0},
                                        {
                                            "label": "10% obs error (min=1000)",
                                            "value": 0.10,
                                        },
                                        {
                                            "label": "20% obs error (min=1000)",
                                            "value": 0.20,
                                        },
                                    ],
                                    value=-1.0,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                wcc.Dropdown(
                                    label="Misfit exponent",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_EXPONENT),
                                    options=[
                                        {
                                            "label": "Linear sum",
                                            "value": 1.0,
                                        },
                                        {
                                            "label": "Squared sum",
                                            "value": 2.0,
                                        },
                                    ],
                                    value=1.0,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                # wcc.Dropdown(
                                #     label="Misfit normalization",
                                #     id=get_uuid(
                                #         LayoutElements.PROD_MISFIT_NORMALIZATION
                                #     ),
                                #     options=[
                                #         {
                                #             "label": "Yes",
                                #             "value": True,
                                #         },
                                #         {
                                #             "label": "No",
                                #             "value": False,
                                #         },
                                #     ],
                                #     value=False,
                                #     clearable=False,
                                #     persistence=True,
                                #     persistence_type="memory",
                                # ),
                            ],
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 4, "minWidth": "500px"},
                    children=[html.Div(id=get_uuid(LayoutElements.PROD_MISFIT_GRAPH))],
                ),
            ],
        ),
    ]
    return children


def _well_prod_coverage(
    get_uuid: Callable,
    ensemble_names: List[str],
    dates: List[str],
    phases: List[str],
    wells: List[str],
    all_well_collection_names: List[str],
    realizations: List[int],
) -> list:
    children = [
        wcc.FlexBox(
            id=get_uuid(LayoutElements.WELL_COVERAGE_LAYOUT),
            children=[
                wcc.Frame(
                    style={
                        "flex": 1,
                        "height": "85vh",
                        "maxWidth": "200px",
                    },
                    children=[
                        wcc.Selectors(
                            label="Case settings",
                            children=[
                                wcc.Dropdown(
                                    label="Ensemble selector",
                                    id=get_uuid(
                                        LayoutElements.WELL_COVERAGE_ENSEMBLE_NAMES
                                    ),
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in ensemble_names
                                    ],
                                    value=ensemble_names[0:1],
                                    multi=True,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Filter settings",
                            children=[
                                wcc.SelectWithLabel(
                                    label="Date selector",
                                    id=get_uuid(LayoutElements.WELL_COVERAGE_DATES),
                                    options=[
                                        {
                                            "label": _date.strftime("%Y-%m-%d"),
                                            "value": str(_date),
                                        }
                                        for _date in dates
                                    ],
                                    value=[str(dates[-1])],
                                    size=min([len(dates), 5]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Phase selector",
                                    id=get_uuid(LayoutElements.WELL_COVERAGE_PHASES),
                                    options=[
                                        {"label": phase, "value": phase}
                                        for phase in phases
                                    ],
                                    value=phases,
                                    size=min([len(phases), 3]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Well selector",
                                    id=get_uuid(
                                        LayoutElements.WELL_COVERAGE_WELL_NAMES
                                    ),
                                    options=[
                                        {"label": well, "value": well} for well in wells
                                    ],
                                    value=wells,
                                    size=min([len(wells), 9]),
                                ),
                                wcc.RadioItems(
                                    label="Combine wells and collections as",
                                    id=get_uuid(LayoutElements.WELL_COVERAGE_COMBINE),
                                    options=[
                                        {
                                            "label": "Intersection",
                                            "value": "intersection",
                                        },
                                        {"label": "Union", "value": "union"},
                                    ],
                                    value="intersection",
                                ),
                                wcc.SelectWithLabel(
                                    label="Well collection selector",
                                    id=get_uuid(
                                        LayoutElements.WELL_COVERAGE_WELL_COLLECTIONS
                                    ),
                                    options=[
                                        {"label": collection, "value": collection}
                                        for collection in all_well_collection_names
                                    ],
                                    value=all_well_collection_names,
                                    size=min([len(wells), 5]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Realization selector",
                                    id=get_uuid(
                                        LayoutElements.WELL_COVERAGE_REALIZATIONS
                                    ),
                                    options=[
                                        {"label": real, "value": real}
                                        for real in realizations
                                    ],
                                    value=realizations,
                                    size=min([len(wells), 5]),
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Plot settings and layout",
                            open_details=True,
                            children=[
                                wcc.Dropdown(
                                    label="Colorby",
                                    id=get_uuid(LayoutElements.WELL_COVERAGE_COLORBY),
                                    options=[
                                        {
                                            "label": "Ensemble",
                                            "value": "ENSEMBLE",
                                        },
                                        {"label": "Well", "value": "WELL"},
                                        {"label": "Date", "value": "DATE"},
                                    ],
                                    value="ENSEMBLE",
                                    multi=False,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                wcc.Dropdown(
                                    label="Plot type",
                                    id=get_uuid(LayoutElements.WELL_COVERAGE_PLOT_TYPE),
                                    options=[
                                        {"label": "Diff plot", "value": "diffplot"},
                                        {"label": "Cross plot", "value": "crossplot"},
                                        {"label": "Box plot", "value": "boxplot"},
                                    ],
                                    value="crossplot",
                                    multi=False,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                            ],
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 4, "minWidth": "500px"},
                    children=[
                        html.Div(id=get_uuid(LayoutElements.WELL_COVERAGE_GRAPH))
                    ],
                ),
            ],
        ),
    ]
    return children


# def _group_prod_coverage() -> list:
#     children = [
#         wcc.FlexBox(
#             id=get_uuid(LayoutElements.group_coverage-layout),
#             children=[
#                 wcc.Frame(
#                     style={
#                         "flex": 1,
#                         "height": "55vh",
#                         "maxWidth": "200px",
#                     },
#                     children=[
#                         wcc.Dropdown(
#                             label="Ensemble selector",
#                             id=get_uuid(LayoutElements.group_coverage-ensemble_names),
#                             options=[{"label": ens, "value": ens} for ens in ensembles],
#                             value=ensembles,
#                             multi=True,
#                             clearable=False,
#                             persistence=True,
#                             persistence_type="memory",
#                         ),
#                         wcc.SelectWithLabel(
#                             label="Date selector",
#                             id=get_uuid(LayoutElements.group_coverage-dates),
#                             options=[
#                                 {"label": _date, "value": _date} for _date in dates
#                             ],
#                             value=[dates[-1]],
#                             size=min([len(dates), 5]),
#                         ),
#                         wcc.SelectWithLabel(
#                             label="Phase selector",
#                             id=get_uuid(LayoutElements.group_coverage-phases),
#                             options=[
#                                 {"label": phase, "value": phase} for phase in phases
#                             ],
#                             value=phases,
#                             size=min([len(phases), 3]),
#                         ),
#                         wcc.SelectWithLabel(
#                             label="Group selector",
#                             id=get_uuid(LayoutElements.group_coverage-group_names),
#                             options=[
#                                 {"label": group, "value": group} for group in groups
#                             ],
#                             value=groups,
#                             size=min([len(groups), 9]),
#                         ),
#                         wcc.Dropdown(
#                             label="Colorby",
#                             id=get_uuid(LayoutElements.group_coverage-colorby),
#                             options=[
#                                 {
#                                     "label": "Ensemble",
#                                     "value": "ENSEMBLE",
#                                 },
#                                 {"label": "Group", "value": "WELL"},
#                                 {"label": "Date", "value": "DATE"},
#                             ],
#                             value="ENSEMBLE",
#                             multi=False,
#                             clearable=False,
#                             persistence=True,
#                             persistence_type="memory",
#                         ),
#                         wcc.Dropdown(
#                             label="Plot type",
#                             id=get_uuid(LayoutElements.group_coverage-plot_type),
#                             options=[
#                                 {"label": "Diff plot", "value": "diffplot"},
#                                 {"label": "Cross plot", "value": "crossplot"},
#                             ],
#                             value="crossplot",
#                             multi=False,
#                             clearable=False,
#                             persistence=True,
#                             persistence_type="memory",
#                         ),
#                     ],
#                 ),
#                 wcc.Frame(
#                     style={"flex": 4, "minWidth": "500px"},
#                     children=[html.Div(id=get_uuid(LayoutElements.group_coverage-graph))],
#                 ),
#             ],
#         ),
#     ]
#     return children


# def _heatmap() -> list:
#     children = [
#         wcc.FlexBox(
#             id=get_uuid(LayoutElements.heatmap-layout),
#             children=[
#                 wcc.Frame(
#                     style={
#                         "flex": 1,
#                         "height": "80vh",
#                         "maxWidth": "200px",
#                     },
#                     children=[
#                         wcc.Selectors(
#                             label="Case settings",
#                             children=[
#                                 wcc.Dropdown(
#                                     label="Ensemble selector",
#                                     id=get_uuid(LayoutElements.heatmap-ensemble_names),
#                                     options=[
#                                         {"label": ens, "value": ens}
#                                         for ens in ensembles
#                                     ],
#                                     value=ensembles,
#                                     multi=True,
#                                     clearable=False,
#                                     persistence=True,
#                                     persistence_type="memory",
#                                 ),
#                             ],
#                         ),
#                         wcc.Selectors(
#                             label="Filter settings",
#                             children=[
#                                 wcc.SelectWithLabel(
#                                     label="Date selector",
#                                     id=get_uuid(LayoutElements.heatmap-dates),
#                                     options=[
#                                         {"label": _date, "value": _date}
#                                         for _date in dates
#                                     ],
#                                     value=dates,
#                                     size=min([len(dates), 5]),
#                                 ),
#                                 wcc.SelectWithLabel(
#                                     label="Phase selector",
#                                     id=get_uuid(LayoutElements.heatmap-phases),
#                                     options=[
#                                         {"label": phase, "value": phase}
#                                         for phase in phases
#                                     ],
#                                     value=phases,
#                                     size=min([len(phases), 3]),
#                                 ),
#                                 wcc.SelectWithLabel(
#                                     label="Well selector",
#                                     id=get_uuid(LayoutElements.heatmap-well_names),
#                                     options=[
#                                         {"label": well, "value": well} for well in wells
#                                     ],
#                                     value=wells,
#                                     size=min([len(wells), 9]),
#                                 ),
#                                 wcc.Dropdown(
#                                     label="Show wells with largest misfit",
#                                     id=get_uuid(LayoutElements.heatmap-filter_largest),
#                                     options=[
#                                         {"label": "Show all", "value": 0},
#                                         {"label": "2", "value": 2},
#                                         {"label": "4", "value": 4},
#                                         {"label": "6", "value": 6},
#                                         {"label": "8", "value": 8},
#                                         {"label": "10", "value": 10},
#                                         {"label": "12", "value": 12},
#                                         {"label": "15", "value": 15},
#                                         {"label": "20", "value": 20},
#                                         {"label": "25", "value": 25},
#                                     ],
#                                     value=0,
#                                     multi=False,
#                                     clearable=False,
#                                     persistence=True,
#                                     persistence_type="memory",
#                                 ),
#                             ],
#                         ),
#                         wcc.Selectors(
#                             label="Plot settings and layout",
#                             open_details=True,
#                             children=[
#                                 wcc.Dropdown(
#                                     label="Fig layout - height",
#                                     id=get_uuid(LayoutElements.heatmap-figheight),
#                                     options=[
#                                         {
#                                             "label": "Very small",
#                                             "value": 250,
#                                         },
#                                         {
#                                             "label": "Small",
#                                             "value": 350,
#                                         },
#                                         {
#                                             "label": "Medium",
#                                             "value": 450,
#                                         },
#                                         {
#                                             "label": "Large",
#                                             "value": 700,
#                                         },
#                                         {
#                                             "label": "Very large",
#                                             "value": 1000,
#                                         },
#                                     ],
#                                     value=450,
#                                     clearable=False,
#                                     persistence=True,
#                                     persistence_type="memory",
#                                 ),
#                                 wcc.Dropdown(
#                                     label="Color range scaling (relative to max)",
#                                     id=get_uuid(LayoutElements.heatmap-scale_col_range),
#                                     options=[
#                                         {"label": f"{x:.0%}", "value": x}
#                                         for x in [
#                                             0.1,
#                                             0.2,
#                                             0.3,
#                                             0.4,
#                                             0.5,
#                                             0.6,
#                                             0.7,
#                                             0.8,
#                                             0.9,
#                                             1.0,
#                                             1.5,
#                                             2.0,
#                                         ]
#                                     ],
#                                     style={"display": "block"},
#                                     value=1.0,
#                                     clearable=False,
#                                     persistence=True,
#                                     persistence_type="memory",
#                                 ),
#                             ],
#                         ),
#                     ],
#                 ),
#                 wcc.Frame(
#                     style={"flex": 4, "minWidth": "500px"},
#                     children=[html.Div(id=get_uuid(LayoutElements.heatmap-graph))],
#                 ),
#             ],
#         ),
#     ]
#     return children

from typing import Callable, List, Optional

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import dash_table
import webviz_core_components as wcc
import webviz_subsurface_components as wsc
from webviz_subsurface_components import ExpressionInfo

from .types import (
    FanchartOptions,
    StatisticsOptions,
    TraceOptions,
    VisualizationOptions,
)

from ..._providers import Frequency
from ..._utils.vector_calculator import get_custom_vector_definitions_from_expressions


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
    PROD_MISFIT_REALIZATIONS = "prod_misfit_realizations"
    PROD_MISFIT_COLORBY = "prod_misfit_colorby"
    PROD_MISFIT_SORTING = "prod_misfit_sorting"
    PROD_MISFIT_FIGHEIGHT = "prod_misfit_figheight"
    PROD_MISFIT_WEIGHT = "prod_misfit_weight"
    PROD_MISFIT_EXPONENT = "prod_misfit_exponent"
    PROD_MISFIT_NORMALIZATION = "prod_misfit_normalization"
    PROD_MISFIT_GRAPH = "prod_misfit_graph"

    VECTOR_SELECTOR = "vector_selector"

    VECTOR_CALCULATOR = "vector_calculator"
    VECTOR_CALCULATOR_MODAL = "vector_calculator_modal"
    VECTOR_CALCULATOR_OPEN_BUTTON = "vector_calculator_open_button"
    VECTOR_CALCULATOR_EXPRESSIONS = "vector_calculator_expressions"
    VECTOR_CALCULATOR_EXPRESSIONS_OPEN_MODAL = (
        "vector_calculator_expressions_open_modal"
    )

    DELTA_ENSEMBLE_A_DROPDOWN = "delta_ensemble_A_dropdown"
    DELTA_ENSEMBLE_B_DROPDOWN = "delta_ensemble_B_dropdown"
    DELTA_ENSEMBLE_CREATE_BUTTON = "delta_ensemble_create_button"
    CREATED_DELTA_ENSEMBLES = "created_delta_ensemble_names"
    CREATED_DELTA_ENSEMBLE_NAMES_TABLE = "created_delta_ensemble_names_table"
    CREATED_DELTA_ENSEMBLE_NAMES_TABLE_COLUMN = (
        "created_delta_ensemble_names_table_column"
    )

    VISUALIZATION_RADIO_ITEMS = "visualization_radio_items"

    PLOT_FANCHART_OPTIONS_CHECKLIST = "plot_fanchart_options_checklist"
    PLOT_STATISTICS_OPTIONS_CHECKLIST = "plot_statistics_options_checklist"
    PLOT_TRACE_OPTIONS_CHECKLIST = "plot_trace_options_checklist"

    RESAMPLING_FREQUENCY_DROPDOWN = "resampling_frequency_dropdown"


# --- layout ---
def main_layout(
    get_uuid: Callable,
    ensemble_names: List[str],
) -> wcc.Tabs:

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
                    get_uuid=get_uuid,
                    ensemble_names=ensemble_names,
                ),
            ),
            # wcc.Tab(
            #     label="Well production coverage",
            #     style=tab_style,
            #     selected_style=tab_selected_style,
            #     children=_well_prod_coverage(),
            # ),
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
def _misfit_per_real_layout(get_uuid: Callable, ensemble_names: List[str]) -> list:
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
                                    value=ensemble_names,
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
                                        {"label": _date, "value": _date}
                                        for _date in self.dates
                                    ],
                                    value=[self.dates[-1]],
                                    size=min([len(self.dates), 5]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Phase selector",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_PHASES),
                                    options=[
                                        {"label": phase, "value": phase}
                                        for phase in self.phases
                                    ],
                                    value=self.phases,
                                    size=min([len(self.phases), 3]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Well selector",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_WELL_NAMES),
                                    options=[
                                        {"label": well, "value": well}
                                        for well in self.wells
                                    ],
                                    value=self.wells,
                                    size=min([len(self.wells), 9]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Realization selector",
                                    id=get_uuid(
                                        LayoutElements.PROD_MISFIT_REALIZATIONS
                                    ),
                                    options=[
                                        {"label": real, "value": real}
                                        for real in self.realizations
                                    ],
                                    value=self.realizations,
                                    size=min([len(self.wells), 5]),
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
                            open_details=False,
                            children=[
                                wcc.Dropdown(
                                    label="Misfit weight",
                                    id=get_uuid(LayoutElements.PROD_MISFIT_WEIGHT),
                                    options=[
                                        {
                                            "label": "none",
                                            "value": None,
                                        },
                                        {
                                            "label": "Obs error",
                                            "value": "obs_error",
                                        },
                                    ],
                                    value="obs_error",
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
                                    value=2.0,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                                wcc.Dropdown(
                                    label="Misfit normalization",
                                    id=get_uuid(
                                        LayoutElements.PROD_MISFIT_NORMALIZATION
                                    ),
                                    options=[
                                        {
                                            "label": "Yes",
                                            "value": True,
                                        },
                                        {
                                            "label": "No",
                                            "value": False,
                                        },
                                    ],
                                    value=False,
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
                    children=[html.Div(id=get_uuid(LayoutElements.PROD_MISFIT_GRAPH))],
                ),
            ],
        ),
    ]
    return children


def _well_prod_coverage() -> list:
    children = [
        wcc.FlexBox(
            id=self.uuid("well_coverage-layout"),
            children=[
                wcc.Frame(
                    style={
                        "flex": 1,
                        "height": "55vh",
                        "maxWidth": "200px",
                    },
                    children=[
                        wcc.Dropdown(
                            label="Ensemble selector",
                            id=self.uuid("well_coverage-ensemble_names"),
                            options=[
                                {"label": ens, "value": ens} for ens in self.ensembles
                            ],
                            value=self.ensembles,
                            multi=True,
                            clearable=False,
                            persistence=True,
                            persistence_type="memory",
                        ),
                        wcc.SelectWithLabel(
                            label="Date selector",
                            id=self.uuid("well_coverage-dates"),
                            options=[
                                {"label": _date, "value": _date} for _date in self.dates
                            ],
                            value=[self.dates[-1]],
                            size=min([len(self.dates), 5]),
                        ),
                        wcc.SelectWithLabel(
                            label="Phase selector",
                            id=self.uuid("well_coverage-phases"),
                            options=[
                                {"label": phase, "value": phase}
                                for phase in self.phases
                            ],
                            value=self.phases,
                            size=min([len(self.phases), 3]),
                        ),
                        wcc.SelectWithLabel(
                            label="Well selector",
                            id=self.uuid("well_coverage-well_names"),
                            options=[
                                {"label": well, "value": well} for well in self.wells
                            ],
                            value=self.wells,
                            size=min([len(self.wells), 9]),
                        ),
                        wcc.Dropdown(
                            label="Colorby",
                            id=self.uuid("well_coverage-colorby"),
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
                            id=self.uuid("well_coverage-plot_type"),
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
                wcc.Frame(
                    style={"flex": 4, "minWidth": "500px"},
                    children=[html.Div(id=self.uuid("well_coverage-graph"))],
                ),
            ],
        ),
    ]
    return children


def _group_prod_coverage() -> list:
    children = [
        wcc.FlexBox(
            id=self.uuid("group_coverage-layout"),
            children=[
                wcc.Frame(
                    style={
                        "flex": 1,
                        "height": "55vh",
                        "maxWidth": "200px",
                    },
                    children=[
                        wcc.Dropdown(
                            label="Ensemble selector",
                            id=self.uuid("group_coverage-ensemble_names"),
                            options=[
                                {"label": ens, "value": ens} for ens in self.ensembles
                            ],
                            value=self.ensembles,
                            multi=True,
                            clearable=False,
                            persistence=True,
                            persistence_type="memory",
                        ),
                        wcc.SelectWithLabel(
                            label="Date selector",
                            id=self.uuid("group_coverage-dates"),
                            options=[
                                {"label": _date, "value": _date} for _date in self.dates
                            ],
                            value=[self.dates[-1]],
                            size=min([len(self.dates), 5]),
                        ),
                        wcc.SelectWithLabel(
                            label="Phase selector",
                            id=self.uuid("group_coverage-phases"),
                            options=[
                                {"label": phase, "value": phase}
                                for phase in self.phases
                            ],
                            value=self.phases,
                            size=min([len(self.phases), 3]),
                        ),
                        wcc.SelectWithLabel(
                            label="Group selector",
                            id=self.uuid("group_coverage-group_names"),
                            options=[
                                {"label": group, "value": group}
                                for group in self.groups
                            ],
                            value=self.groups,
                            size=min([len(self.groups), 9]),
                        ),
                        wcc.Dropdown(
                            label="Colorby",
                            id=self.uuid("group_coverage-colorby"),
                            options=[
                                {
                                    "label": "Ensemble",
                                    "value": "ENSEMBLE",
                                },
                                {"label": "Group", "value": "WELL"},
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
                            id=self.uuid("group_coverage-plot_type"),
                            options=[
                                {"label": "Diff plot", "value": "diffplot"},
                                {"label": "Cross plot", "value": "crossplot"},
                            ],
                            value="crossplot",
                            multi=False,
                            clearable=False,
                            persistence=True,
                            persistence_type="memory",
                        ),
                    ],
                ),
                wcc.Frame(
                    style={"flex": 4, "minWidth": "500px"},
                    children=[html.Div(id=self.uuid("group_coverage-graph"))],
                ),
            ],
        ),
    ]
    return children


def _heatmap() -> list:
    children = [
        wcc.FlexBox(
            id=self.uuid("heatmap-layout"),
            children=[
                wcc.Frame(
                    style={
                        "flex": 1,
                        "height": "80vh",
                        "maxWidth": "200px",
                    },
                    children=[
                        wcc.Selectors(
                            label="Case settings",
                            children=[
                                wcc.Dropdown(
                                    label="Ensemble selector",
                                    id=self.uuid("heatmap-ensemble_names"),
                                    options=[
                                        {"label": ens, "value": ens}
                                        for ens in self.ensembles
                                    ],
                                    value=self.ensembles,
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
                                    id=self.uuid("heatmap-dates"),
                                    options=[
                                        {"label": _date, "value": _date}
                                        for _date in self.dates
                                    ],
                                    value=self.dates,
                                    size=min([len(self.dates), 5]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Phase selector",
                                    id=self.uuid("heatmap-phases"),
                                    options=[
                                        {"label": phase, "value": phase}
                                        for phase in self.phases
                                    ],
                                    value=self.phases,
                                    size=min([len(self.phases), 3]),
                                ),
                                wcc.SelectWithLabel(
                                    label="Well selector",
                                    id=self.uuid("heatmap-well_names"),
                                    options=[
                                        {"label": well, "value": well}
                                        for well in self.wells
                                    ],
                                    value=self.wells,
                                    size=min([len(self.wells), 9]),
                                ),
                                wcc.Dropdown(
                                    label="Show wells with largest misfit",
                                    id=self.uuid("heatmap-filter_largest"),
                                    options=[
                                        {"label": "Show all", "value": 0},
                                        {"label": "2", "value": 2},
                                        {"label": "4", "value": 4},
                                        {"label": "6", "value": 6},
                                        {"label": "8", "value": 8},
                                        {"label": "10", "value": 10},
                                        {"label": "12", "value": 12},
                                        {"label": "15", "value": 15},
                                        {"label": "20", "value": 20},
                                        {"label": "25", "value": 25},
                                    ],
                                    value=0,
                                    multi=False,
                                    clearable=False,
                                    persistence=True,
                                    persistence_type="memory",
                                ),
                            ],
                        ),
                        wcc.Selectors(
                            label="Plot settings and layout",
                            open_details=True,
                            children=[
                                wcc.Dropdown(
                                    label="Fig layout - height",
                                    id=self.uuid("heatmap-figheight"),
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
                                wcc.Dropdown(
                                    label="Color range scaling (relative to max)",
                                    id=self.uuid("heatmap-scale_col_range"),
                                    options=[
                                        {"label": f"{x:.0%}", "value": x}
                                        for x in [
                                            0.1,
                                            0.2,
                                            0.3,
                                            0.4,
                                            0.5,
                                            0.6,
                                            0.7,
                                            0.8,
                                            0.9,
                                            1.0,
                                            1.5,
                                            2.0,
                                        ]
                                    ],
                                    style={"display": "block"},
                                    value=1.0,
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
                    children=[html.Div(id=self.uuid("heatmap-graph"))],
                ),
            ],
        ),
    ]
    return children

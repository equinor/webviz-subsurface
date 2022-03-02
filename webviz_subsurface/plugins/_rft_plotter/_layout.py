from typing import Callable, List

import webviz_core_components as wcc
from dash import html

from ..._components.parameter_filter import ParameterFilter
from ._business_logic import RftPlotterDataModel


# pylint: disable = too-few-public-methods
class LayoutElements:
    MAP = "map-wrapper"
    MAP_GRAPH = "map-graph"
    FORMATIONS_GRAPH = "formations-graph-wrapper"
    MISFITPLOT_GRAPH = "misfit-graph-wrapper"
    CROSSPLOT_GRAPH = "crossplot-graph-wrapper"
    ERRORPLOT_GRAPH = "errorplot-graph-wrapper"
    FORMATIONS_ENSEMBLE = "formations-ensemble"
    FORMATIONS_WELL = "formations-well"
    FORMATIONS_DATE = "formations-date"
    FORMATIONS_LINETYPE = "formations-linetype"
    FORMATIONS_DEPTHOPTION = "formations-depthoption"
    MAP_ENSEMBLE = "map-ensemble"
    MAP_SIZE_BY = "map-size-by"
    MAP_COLOR_BY = "map-color-by"
    MAP_DATE_RANGE = "map-date-range"
    MAP_ZONES = "map-zones"
    FILTER_ENSEMBLES = {
        "misfitplot": "ensembles-misfit",
        "crossplot": "ensembles-crossplot",
        "errorplot": "ensembles-errorplot",
    }
    FILTER_WELLS = {
        "misfitplot": "well-misfit",
        "crossplot": "well-crossplot",
        "errorplot": "well-errorplot",
    }
    FILTER_ZONES = {
        "misfitplot": "zones-misfit",
        "crossplot": "zones-crossplot",
        "errorplot": "zones-errorplot",
    }
    FILTER_DATES = {
        "misfitplot": "dates-misfit",
        "crossplot": "dates-crossplot",
        "errorplot": "dates-errorplot",
    }
    CROSSPLOT_COLOR_BY = "crossplot-color-by"
    CROSSPLOT_SIZE_BY = "crossplot-size-by"
    PARAMRESP_ENSEMBLE = "param-response-ensemble"
    PARAMRESP_WELL = "param-response-well"
    PARAMRESP_DATE = "param-response-date"
    PARAMRESP_ZONE = "param-response-zone"
    PARAMRESP_PARAM = "param-response-param"
    PARAMRESP_CORRTYPE = "param-response-corrtype"
    PARAMRESP_CORR_BARCHART = "paramresp-corr-barchart"
    PARAMRESP_CORR_BARCHART_FIGURE = "paramresp-corr-barchart-figure"
    PARAMRESP_SCATTERPLOT = "paramresp-scatterplot"
    PARAMRESP_FORMATIONS = "paramresp-formations"
    PARAMRESP_DATE_DROPDOWN = "paramresp-well-dropdown"
    PARAMRESP_ZONE_DROPDOWN = "paramresp-zone-dropdown"
    PARAMRESP_DEPTHOPTION = "paramresp-depthoption"
    PARAM_FILTER = "param-filter"
    PARAM_FILTER_WRAPPER = "param-filter-wrapper"
    DISPLAY_PARAM_FILTER = "display-param-filter"


def main_layout(get_uuid: Callable, datamodel: RftPlotterDataModel) -> wcc.Tabs:

    tabs = [
        wcc.Tab(
            label="RFT Map",
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style={"flex": 1, "height": "87vh"},
                            children=[
                                map_plot_selectors(get_uuid, datamodel),
                                formation_plot_selectors(get_uuid, datamodel),
                            ],
                        ),
                        wcc.Frame(
                            style={"flex": 3, "height": "87vh"},
                            color="white",
                            highlight=False,
                            id=get_uuid(LayoutElements.MAP),
                            children=[],
                        ),
                        wcc.Frame(
                            style={"flex": 3, "height": "87vh"},
                            color="white",
                            highlight=False,
                            id=get_uuid(LayoutElements.FORMATIONS_GRAPH),
                            children=[],
                        ),
                    ]
                )
            ],
        ),
        wcc.Tab(
            label="RFT misfit per real",
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style={"flex": 1, "height": "87vh"},
                            children=filter_layout(get_uuid, datamodel, "misfitplot"),
                        ),
                        wcc.Frame(
                            style={"flex": 6, "height": "87vh"},
                            color="white",
                            highlight=False,
                            id=get_uuid(LayoutElements.MISFITPLOT_GRAPH),
                            children=[],
                        ),
                    ]
                )
            ],
        ),
        wcc.Tab(
            label="RFT crossplot - sim vs obs",
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style={"flex": 1, "height": "87vh"},
                            children=[
                                filter_layout(get_uuid, datamodel, "crossplot"),
                                size_color_layout(get_uuid),
                            ],
                        ),
                        wcc.Frame(
                            style={"flex": 6, "height": "87vh"},
                            color="white",
                            highlight=False,
                            children=[
                                html.Div(id=get_uuid(LayoutElements.CROSSPLOT_GRAPH)),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        wcc.Tab(
            label="RFT misfit per observation",
            children=[
                wcc.FlexBox(
                    children=[
                        wcc.Frame(
                            style={"flex": 1, "height": "87vh"},
                            children=filter_layout(get_uuid, datamodel, "errorplot"),
                        ),
                        wcc.Frame(
                            color="white",
                            highlight=False,
                            style={"flex": 6, "height": "87vh"},
                            id=get_uuid(LayoutElements.ERRORPLOT_GRAPH),
                            children=[],
                        ),
                    ],
                ),
            ],
        ),
    ]

    # It this is not a sensitivity run, add the parameter response tab
    if not datamodel.param_model.sensrun:
        tabs.append(
            wcc.Tab(
                label="RFT parameter response",
                children=parameter_response_layout(
                    get_uuid=get_uuid, datamodel=datamodel
                ),
            )
        )

    return wcc.Tabs(children=tabs)


def parameter_response_selector_layout(
    get_uuid: Callable, datamodel: RftPlotterDataModel
) -> wcc.Frame:
    ensembles = datamodel.ensembles
    well_names = datamodel.well_names
    params = datamodel.parameters if not datamodel.parameters is None else []
    return wcc.Frame(
        style={
            "height": "87vh",
            "overflowY": "auto",
            "font-size": "15px",
        },
        children=[
            wcc.Selectors(
                label="Selections",
                children=[
                    wcc.Dropdown(
                        label="Ensemble",
                        id=get_uuid(LayoutElements.PARAMRESP_ENSEMBLE),
                        options=[{"label": ens, "value": ens} for ens in ensembles],
                        value=ensembles[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Well",
                        id=get_uuid(LayoutElements.PARAMRESP_WELL),
                        options=[{"label": well, "value": well} for well in well_names],
                        value=well_names[0] if well_names else "",
                        clearable=False,
                    ),
                    html.Div(
                        id=get_uuid(LayoutElements.PARAMRESP_DATE_DROPDOWN),
                        children=wcc.Dropdown(
                            label="Date",
                            id=get_uuid(LayoutElements.PARAMRESP_DATE),
                            options=None,
                            value=None,
                            clearable=False,
                        ),
                    ),
                    html.Div(
                        id=get_uuid(LayoutElements.PARAMRESP_ZONE_DROPDOWN),
                        children=wcc.Dropdown(
                            label="Zone",
                            id=get_uuid(LayoutElements.PARAMRESP_ZONE),
                            options=None,
                            clearable=False,
                            value=None,
                        ),
                    ),
                    wcc.Dropdown(
                        label="Parameter",
                        id=get_uuid(LayoutElements.PARAMRESP_PARAM),
                        options=[{"label": param, "value": param} for param in params],
                        clearable=False,
                        value=None,
                    ),
                ],
            ),
            wcc.Selectors(
                label="Options",
                children=[
                    wcc.Checklist(
                        id=get_uuid(LayoutElements.DISPLAY_PARAM_FILTER),
                        options=[{"label": "Show parameter filter", "value": "Show"}],
                        value=[],
                    ),
                    wcc.RadioItems(
                        label="Correlation options",
                        id=get_uuid(LayoutElements.PARAMRESP_CORRTYPE),
                        options=[
                            {
                                "label": "Simulated vs parameters",
                                "value": "sim_vs_param",
                            },
                            {
                                "label": "Parameter vs simulated",
                                "value": "param_vs_sim",
                            },
                        ],
                        value="sim_vs_param",
                    ),
                    wcc.RadioItems(
                        label="Depth option",
                        id=get_uuid(LayoutElements.PARAMRESP_DEPTHOPTION),
                        options=[
                            {
                                "label": "TVD",
                                "value": "TVD",
                            },
                            {
                                "label": "MD",
                                "value": "MD",
                            },
                        ],
                        value="TVD",
                    ),
                ],
            ),
        ],
    )


def parameter_response_layout(
    get_uuid: Callable, datamodel: RftPlotterDataModel
) -> wcc.FlexBox:
    df = datamodel.param_model.dataframe
    parameter_filter = ParameterFilter(
        uuid=get_uuid(LayoutElements.PARAM_FILTER),
        dframe=df[df["ENSEMBLE"].isin(datamodel.param_model.mc_ensembles)].copy(),
        reset_on_ensemble_update=True,
    )
    return wcc.FlexBox(
        children=[
            wcc.FlexColumn(
                flex=1, children=parameter_response_selector_layout(get_uuid, datamodel)
            ),
            wcc.FlexColumn(
                flex=4,
                children=wcc.FlexBox(
                    children=[
                        wcc.FlexColumn(
                            flex=2,
                            children=[
                                wcc.Frame(
                                    style={"height": "41.5vh"},
                                    id=get_uuid(LayoutElements.PARAMRESP_CORR_BARCHART),
                                    color="white",
                                    highlight=False,
                                    children=[],
                                ),
                                wcc.Frame(
                                    style={"height": "41.5vh"},
                                    id=get_uuid(LayoutElements.PARAMRESP_SCATTERPLOT),
                                    color="white",
                                    highlight=False,
                                    children=[],
                                ),
                            ],
                        ),
                        wcc.FlexColumn(
                            flex=2,
                            children=[
                                wcc.Frame(
                                    id=get_uuid(LayoutElements.PARAMRESP_FORMATIONS),
                                    color="white",
                                    highlight=False,
                                    style={"height": "87vh"},
                                    children=[],
                                )
                            ],
                        ),
                    ],
                ),
            ),
            wcc.FlexColumn(
                id=get_uuid(LayoutElements.PARAM_FILTER_WRAPPER),
                style={"display": "none"},
                flex=1,
                children=wcc.Frame(
                    style={"height": "87vh"},
                    children=parameter_filter.layout,
                ),
            ),
        ]
    )


def formation_plot_selectors(
    get_uuid: Callable, datamodel: RftPlotterDataModel
) -> List[html.Div]:
    ensembles = datamodel.ensembles
    well_names = datamodel.well_names
    date_in_well = datamodel.date_in_well
    return wcc.Selectors(
        label="Formation plot settings",
        children=[
            wcc.Dropdown(
                label="Ensemble",
                id=get_uuid(LayoutElements.FORMATIONS_ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in ensembles],
                value=ensembles[0],
                multi=True,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Well",
                id=get_uuid(LayoutElements.FORMATIONS_WELL),
                options=[{"label": well, "value": well} for well in well_names],
                value=well_names[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Date",
                id=get_uuid(LayoutElements.FORMATIONS_DATE),
                options=[
                    {"label": date, "value": date}
                    for date in date_in_well(well_names[0])
                ],
                clearable=False,
                value=date_in_well(well_names[0])[0],
            ),
            wcc.RadioItems(
                label="Plot simulations as",
                id=get_uuid(LayoutElements.FORMATIONS_LINETYPE),
                options=[
                    {
                        "label": "Realization lines",
                        "value": "realization",
                    },
                    {
                        "label": "Statistical fanchart",
                        "value": "fanchart",
                    },
                ],
                value="realization",
            ),
            wcc.RadioItems(
                label="Depth option",
                id=get_uuid(LayoutElements.FORMATIONS_DEPTHOPTION),
                options=[
                    {
                        "label": "TVD",
                        "value": "TVD",
                    },
                    {
                        "label": "MD",
                        "value": "MD",
                    },
                ],
                value="TVD",
            ),
        ],
    )


def map_plot_selectors(
    get_uuid: Callable, datamodel: RftPlotterDataModel
) -> List[html.Div]:
    ensembles = datamodel.ensembles
    zone_names = datamodel.zone_names
    return wcc.Selectors(
        label="Map plot settings",
        children=[
            wcc.Dropdown(
                label="Ensemble",
                id=get_uuid(LayoutElements.MAP_ENSEMBLE),
                options=[{"label": ens, "value": ens} for ens in ensembles],
                value=ensembles[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Size points by",
                id=get_uuid(LayoutElements.MAP_SIZE_BY),
                options=[
                    {
                        "label": "Standard Deviation",
                        "value": "STDDEV",
                    },
                    {
                        "label": "Misfit",
                        "value": "ABSDIFF",
                    },
                ],
                value="ABSDIFF",
                clearable=False,
            ),
            wcc.Dropdown(
                label="Color points by",
                id=get_uuid(LayoutElements.MAP_COLOR_BY),
                options=[
                    {
                        "label": "Misfit",
                        "value": "ABSDIFF",
                    },
                    {
                        "label": "Standard Deviation",
                        "value": "STDDEV",
                    },
                    {
                        "label": "Year",
                        "value": "YEAR",
                    },
                ],
                value="STDDEV",
                clearable=False,
            ),
            wcc.RangeSlider(
                label="Filter date range",
                id=get_uuid(LayoutElements.MAP_DATE_RANGE),
                min=datamodel.ertdatadf["DATE_IDX"].min(),
                max=datamodel.ertdatadf["DATE_IDX"].max(),
                value=[
                    datamodel.ertdatadf["DATE_IDX"].min(),
                    datamodel.ertdatadf["DATE_IDX"].max(),
                ],
                marks=datamodel.date_marks,
            ),
            wcc.Selectors(
                label="Zone filter",
                open_details=False,
                children=[
                    wcc.SelectWithLabel(
                        size=min(10, len(zone_names)),
                        id=get_uuid(LayoutElements.MAP_ZONES),
                        options=[{"label": name, "value": name} for name in zone_names],
                        value=zone_names,
                        multi=True,
                    ),
                ],
            ),
        ],
    )


def filter_layout(
    get_uuid: Callable, datamodel: RftPlotterDataModel, tab: str
) -> List[wcc.Selectors]:
    """Layout for shared filters"""
    ensembles = datamodel.ensembles
    well_names = datamodel.well_names
    zone_names = datamodel.zone_names
    dates = datamodel.dates
    return wcc.Selectors(
        label="Selectors",
        children=[
            wcc.SelectWithLabel(
                label="Ensembles",
                size=min(4, len(ensembles)),
                id=get_uuid(LayoutElements.FILTER_ENSEMBLES[tab]),
                options=[{"label": name, "value": name} for name in ensembles],
                value=ensembles,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Wells",
                size=min(20, len(well_names)),
                id=get_uuid(LayoutElements.FILTER_WELLS[tab]),
                options=[{"label": name, "value": name} for name in well_names],
                value=well_names,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Zones",
                size=min(10, len(zone_names)),
                id=get_uuid(LayoutElements.FILTER_ZONES[tab]),
                options=[{"label": name, "value": name} for name in zone_names],
                value=zone_names,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Dates",
                size=min(10, len(dates)),
                id=get_uuid(LayoutElements.FILTER_DATES[tab]),
                options=[{"label": name, "value": name} for name in dates],
                value=dates,
                multi=True,
            ),
        ],
    )


def size_color_layout(get_uuid: Callable) -> List[html.Div]:
    return wcc.Selectors(
        label="Plot settings",
        children=[
            wcc.Dropdown(
                label="Color by",
                id=get_uuid(LayoutElements.CROSSPLOT_COLOR_BY),
                options=[
                    {
                        "label": "Misfit",
                        "value": "ABSDIFF",
                    },
                    {
                        "label": "Standard Deviation",
                        "value": "STDDEV",
                    },
                ],
                value="STDDEV",
                clearable=False,
            ),
            wcc.Dropdown(
                label="Size by",
                id=get_uuid(LayoutElements.CROSSPLOT_SIZE_BY),
                options=[
                    {
                        "label": "Standard Deviation",
                        "value": "STDDEV",
                    },
                    {
                        "label": "Misfit",
                        "value": "ABSDIFF",
                    },
                ],
                value="ABSDIFF",
                clearable=False,
            ),
        ],
    )

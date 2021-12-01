from typing import Callable, List

import webviz_core_components as wcc
from dash import html

from ._business_logic import RftPlotterDataModel


# pylint: disable = too-few-public-methods
class LayoutElements:
    MAP = "map-wrapper"
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
    CORRELATIONS_ENSEMBLE = "correlations-ensemble"
    CORRELATIONS_WELL = "correlations-well"
    CORRELATIONS_DATE = "correlations-date"
    CORRELATIONS_ZONE = "correlations-zone"
    CORRELATIONS_PARAM = "correlations-param"


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

    #
    if datamodel.param_model is not None:
        tabs.append(
            wcc.Tab(
                label="RFT correlations",
                children=correlations_layout(get_uuid=get_uuid, datamodel=datamodel),
            )
        )

    return wcc.Tabs(children=tabs)


def correlations_selector_layout(
    get_uuid: Callable, datamodel: RftPlotterDataModel
) -> wcc.Frame:
    ensembles = datamodel.ensembles
    well_names = datamodel.well_names
    zone_names = datamodel.zone_names
    dates_in_well = datamodel.date_in_well(well_names[0])
    params = datamodel.parameters
    # what if the lists are empty
    # what if there are no parameters
    return wcc.Frame(
        style={
            "height": "80vh",
            "overflowY": "auto",
            "font-size": "15px",
        },
        children=[
            wcc.Selectors(
                label="Selections",
                children=[
                    wcc.Dropdown(
                        label="Ensemble",
                        id=get_uuid(LayoutElements.CORRELATIONS_ENSEMBLE),
                        options=[{"label": ens, "value": ens} for ens in ensembles],
                        value=ensembles[0],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Well",
                        id=get_uuid(LayoutElements.CORRELATIONS_WELL),
                        options=[{"label": well, "value": well} for well in well_names],
                        value=well_names[0] if well_names else "",
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        label="Date",
                        id=get_uuid(LayoutElements.CORRELATIONS_DATE),
                        options=[
                            {"label": date, "value": date} for date in dates_in_well
                        ],
                        clearable=False,
                        value=dates_in_well[0] if dates_in_well else "",
                    ),
                    wcc.Dropdown(
                        label="Zone",
                        id=get_uuid(LayoutElements.CORRELATIONS_ZONE),
                        options=[{"label": zone, "value": zone} for zone in zone_names],
                        clearable=False,
                        value=zone_names[0] if zone_names else "",
                    ),
                    wcc.Dropdown(
                        label="Parameter",
                        id=get_uuid(LayoutElements.CORRELATIONS_PARAM),
                        options=[{"label": param, "value": param} for param in params],
                        clearable=False,
                        value=params[0] if params else "",
                    ),
                ],
            ),
        ],
    )


def correlations_layout(
    get_uuid: Callable, datamodel: RftPlotterDataModel
) -> wcc.FlexBox:
    return wcc.FlexBox(
        children=[
            wcc.FlexColumn(
                flex=1, children=correlations_selector_layout(get_uuid, datamodel)
            ),
            wcc.FlexColumn(
                flex=4,
                children=wcc.FlexBox(
                    children=[
                        wcc.FlexColumn(
                            flex=2,
                            children=[
                                wcc.Frame(
                                    style={"height": "38.5vh"},
                                    color="white",
                                    highlight=False,
                                    children=[],  # timeseries_view(get_uuid=get_uuid),
                                ),
                                wcc.Frame(
                                    style={"height": "38.5vh"},
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
                                    color="white",
                                    highlight=False,
                                    style={"height": "38.5vh"},
                                    children=[],
                                ),
                                wcc.Frame(
                                    color="white",
                                    highlight=False,
                                    style={"height": "38.5vh"},
                                    children=[],
                                ),
                            ],
                        ),
                    ],
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

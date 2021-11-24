from typing import Callable, List

import webviz_core_components as wcc
from dash import html

from ._business_logic import RftPlotterDataModel


def main_layout(get_uuid: Callable, datamodel: RftPlotterDataModel) -> wcc.Tabs:
    return wcc.Tabs(
        children=[
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
                                id=get_uuid("map"),
                                children=[]
                                # children=wcc.Graph(
                                #     id=get_uuid("map"),
                                # ),
                            ),
                            wcc.Frame(
                                style={"flex": 3, "height": "87vh"},
                                color="white",
                                highlight=False,
                                id=get_uuid("formations-graph-wrapper"),
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
                                children=filter_layout(
                                    get_uuid, datamodel, "misfitplot"
                                ),
                            ),
                            wcc.Frame(
                                style={"flex": 6, "height": "87vh"},
                                color="white",
                                highlight=False,
                                id=get_uuid("misfit-graph-wrapper"),
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
                                    html.Div(id=get_uuid("crossplot-graph-wrapper")),
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
                                children=filter_layout(
                                    get_uuid, datamodel, "errorplot"
                                ),
                            ),
                            wcc.Frame(
                                color="white",
                                highlight=False,
                                style={"flex": 6, "height": "87vh"},
                                id=get_uuid("errorplot-graph-wrapper"),
                                children=[],
                            ),
                        ],
                    ),
                ],
            ),
        ],
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
                id=get_uuid("ensemble"),
                options=[{"label": ens, "value": ens} for ens in ensembles],
                value=ensembles[0],
                multi=True,
                clearable=False,
            ),
            wcc.Dropdown(
                label="Well",
                id=get_uuid("well"),
                options=[{"label": well, "value": well} for well in well_names],
                value=well_names[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Date",
                id=get_uuid("date"),
                options=[
                    {"label": date, "value": date}
                    for date in date_in_well(well_names[0])
                ],
                clearable=False,
                value=date_in_well(well_names[0])[0],
            ),
            wcc.RadioItems(
                label="Plot simulations as",
                id=get_uuid("linetype"),
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
                id=get_uuid("depth_option"),
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
                id=get_uuid("map_ensemble"),
                options=[{"label": ens, "value": ens} for ens in ensembles],
                value=ensembles[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Size points by",
                id=get_uuid("map_size"),
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
                id=get_uuid("map_color"),
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
                id=get_uuid("map_date"),
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
                id=get_uuid(f"ensemble-{tab}"),
                options=[{"label": name, "value": name} for name in ensembles],
                value=ensembles,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Wells",
                size=min(20, len(well_names)),
                id=get_uuid(f"well-{tab}"),
                options=[{"label": name, "value": name} for name in well_names],
                value=well_names,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Zones",
                size=min(10, len(zone_names)),
                id=get_uuid(f"zone-{tab}"),
                options=[{"label": name, "value": name} for name in zone_names],
                value=zone_names,
                multi=True,
            ),
            wcc.SelectWithLabel(
                label="Dates",
                size=min(10, len(dates)),
                id=get_uuid(f"date-{tab}"),
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
                id=get_uuid("crossplot_color"),
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
                id=get_uuid("crossplot_size"),
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

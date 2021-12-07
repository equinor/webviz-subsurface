from typing import List, Optional

import webviz_core_components as wcc
from dash import html

from webviz_subsurface._models import InplaceVolumesModel


def filter_layout(
    uuid: str,
    tab: str,
    volumemodel: InplaceVolumesModel,
    open_details: bool = True,
    hide_selectors: Optional[list] = None,
) -> wcc.Selectors:
    """Layout for selecting intersection data"""
    return wcc.Selectors(
        label="FILTERS",
        open_details=open_details,
        children=[
            filter_dropdowns(
                uuid=uuid,
                tab=tab,
                volumemodel=volumemodel,
                hide_selectors=hide_selectors,
            ),
            realization_filters(uuid=uuid, tab=tab, volumemodel=volumemodel),
        ],
    )


def filter_dropdowns(
    uuid: str,
    volumemodel: InplaceVolumesModel,
    tab: str,
    hide_selectors: Optional[list] = None,
) -> html.Div:
    """Makes dropdowns for each selector"""
    dropdowns_layout: List[html.Div] = []
    hide_selectors = ["SENSNAME", "SENSTYPE", "SENSCASE"] + (
        hide_selectors if hide_selectors is not None else []
    )
    selectors = [
        x
        for x in volumemodel.selectors
        if x not in volumemodel.region_selectors + ["REAL"]
    ]
    for selector in selectors:
        dropdowns_layout.append(
            create_filter_select(
                selector,
                elements=list(volumemodel.dataframe[selector].unique()),
                filter_type="undef",
                uuid=uuid,
                tab=tab,
                hide=selector in hide_selectors,
            )
        )
    # Make region filters
    dropdowns_layout.append(
        html.Span("Region filters: ", style={"font-weight": "bold"})
    )
    if all(x in volumemodel.region_selectors for x in ["FIPNUM", "ZONE", "REGION"]):
        dropdowns_layout.append(fipnum_vs_zone_region_switch(uuid, tab))

    for selector in volumemodel.region_selectors:
        dropdowns_layout.append(
            create_filter_select(
                selector,
                elements=list(volumemodel.dataframe[selector].unique()),
                filter_type="region",
                uuid=uuid,
                tab=tab,
                hide=selector == "FIPNUM" and len(volumemodel.region_selectors) > 1,
            )
        )
    return html.Div(dropdowns_layout)


def create_filter_select(
    selector: str, elements: list, uuid: str, tab: str, filter_type: str, hide: bool
) -> html.Div:
    return html.Div(
        id={"id": uuid, "tab": tab, "wrapper": selector, "type": filter_type},
        style={"display": "inline" if len(elements) > 1 and not hide else "none"},
        children=wcc.SelectWithLabel(
            label=selector.lower().capitalize(),
            id={"id": uuid, "tab": tab, "selector": selector, "type": filter_type},
            options=[{"label": i, "value": i} for i in elements],
            value=elements,
            multi=True,
            size=min(15, len(elements)),
        ),
    )


def fipnum_vs_zone_region_switch(uuid: str, tab: str) -> wcc.RadioItems:
    return wcc.RadioItems(
        id={"id": uuid, "tab": tab, "element": "region-selector"},
        options=[
            {"label": "Region∕Zone", "value": "regzone"},
            {"label": "Fipnum", "value": "fipnum"},
        ],
        value="regzone",
        vertical=False,
    )


def realization_filters(
    uuid: str, tab: str, volumemodel: InplaceVolumesModel
) -> html.Div:
    reals = volumemodel.realizations
    return html.Div(
        style={"margin-top": "15px"},
        children=[
            html.Div(
                style={"display": "inline-flex"},
                children=[
                    html.Span(
                        "Realizations: ",
                        style={"font-weight": "bold"},
                    ),
                    html.Span(
                        id={"id": uuid, "tab": tab, "element": "real_text"},
                        style={"margin-left": "10px"},
                        children=f"{min(reals)}-{max(reals)}",
                    ),
                ],
            ),
            wcc.RadioItems(
                id={"id": uuid, "tab": tab, "element": "real-selector-option"},
                options=[
                    {"label": "Range", "value": "range"},
                    {"label": "Select", "value": "select"},
                ],
                value="range",
                vertical=False,
            ),
            wcc.RangeSlider(
                wrapper_id={"id": uuid, "tab": tab, "element": "real-slider-wrapper"},
                id={
                    "id": uuid,
                    "tab": tab,
                    "component_type": "range",
                },
                value=[min(reals), max(reals)],
                min=min(reals),
                max=max(reals),
                marks={str(i): {"label": str(i)} for i in [min(reals), max(reals)]},
            ),
            html.Div(
                style={"display": "none"},
                children=wcc.Select(
                    id={"id": uuid, "tab": tab, "selector": "REAL", "type": "REAL"},
                    options=[{"label": i, "value": i} for i in reals],
                    value=reals,
                ),
            ),
        ],
    )

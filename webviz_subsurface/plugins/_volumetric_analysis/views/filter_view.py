from typing import List, Optional

import dash_html_components as html
import webviz_core_components as wcc
from webviz_subsurface._models import InplaceVolumesModel


def filter_layout(
    uuid: str,
    tab: str,
    volumemodel: InplaceVolumesModel,
    open_details: bool = True,
    filters: Optional[list] = None,
) -> wcc.Selectors:
    """Layout for selecting intersection data"""
    return wcc.Selectors(
        label="FILTERS",
        open_details=open_details,
        children=[
            filter_dropdowns(
                uuid=uuid, tab=tab, volumemodel=volumemodel, filters=filters
            ),
            realization_filters(uuid=uuid, tab=tab, volumemodel=volumemodel),
        ],
    )


def filter_dropdowns(
    uuid: str,
    volumemodel: InplaceVolumesModel,
    tab: str,
    filters: Optional[list] = None,
) -> html.Div:
    """Makes dropdowns for each selector"""
    dropdowns: List[html.Div] = []
    filters = filters if filters is not None else volumemodel.selectors
    for selector in filters:
        if selector == "REAL":
            continue
        elements = list(volumemodel.dataframe[selector].unique())

        dropdowns.append(
            html.Div(
                style={"display": "inline" if len(elements) > 1 else "none"},
                children=wcc.SelectWithLabel(
                    label=selector.lower().capitalize(),
                    id={"id": uuid, "tab": tab, "selector": selector},
                    options=[{"label": i, "value": i} for i in elements],
                    value=elements,
                    multi=True,
                    size=min(15, len(elements)),
                ),
            )
        )
    return html.Div(dropdowns)


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
                    id={"id": uuid, "tab": tab, "selector": "REAL"},
                    options=[{"label": i, "value": i} for i in reals],
                    value=reals,
                ),
            ),
        ],
    )

from typing import List, Optional
from dataclasses import dataclass
from dash import html, dcc
import webviz_core_components as wcc
import webviz_subsurface_components as wsc


@dataclass
class EnsembleSurfaceProviderContent:
    ensembles: List[str] = None
    selected_ensemble: str = None
    attributes: List[str] = None
    selected_attribute: Optional[str] = None
    names: List[str] = None
    selected_name: str = None
    dates: Optional[List[str]] = None
    selected_date: str = None
    stypes: List[str] = None
    selected_type: str = None


def main_layout(get_uuid):
    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style={"flex": 1},
                children=[
                    # dcc.Loading(
                    html.Div(
                        id=get_uuid("surface-selectors"),
                        children=surface_selectors(
                            get_uuid, EnsembleSurfaceProviderContent()
                        ),
                    ),
                    html.Progress(id=get_uuid("value-range-progress")),
                    html.Pre(id=get_uuid("value-range")),
                ],
            ),
            wcc.Frame(style={"flex": 5}, children=map_view(get_uuid)),
            dcc.Store(id=get_uuid("stored-selections")),
            dcc.Store(id=get_uuid("stored-surface-address")),
            dcc.Store(id=get_uuid("stored-surface-meta")),
            dcc.Store(id=get_uuid("stored-qualified-address")),
        ]
    )


def surface_selectors(get_uuid, provider_content: EnsembleSurfaceProviderContent):
    return [
        wcc.SelectWithLabel(
            id={"id": get_uuid("selector"), "component": "ensemble"},
            label="Ensemble",
            options=[{"label": val, "value": val} for val in provider_content.ensembles]
            if provider_content.ensembles is not None
            else [],
            value=provider_content.selected_ensemble,
            multi=False,
        ),
        wcc.SelectWithLabel(
            id={"id": get_uuid("selector"), "component": "attribute"},
            label="Attribute",
            options=[
                {"label": val, "value": val} for val in provider_content.attributes
            ]
            if provider_content.attributes is not None
            else [],
            value=provider_content.selected_attribute,
            multi=False,
        ),
        wcc.SelectWithLabel(
            id={"id": get_uuid("selector"), "component": "name"},
            label="Name",
            options=[{"label": val, "value": val} for val in provider_content.names]
            if provider_content.names is not None
            else [],
            value=provider_content.selected_name,
            multi=False,
        ),
        wcc.SelectWithLabel(
            id={"id": get_uuid("selector"), "component": "date"},
            label="Date",
            options=[{"label": val, "value": val} for val in provider_content.dates]
            if provider_content.dates is not None
            else [],
            value=provider_content.selected_date,
            multi=False,
        ),
        wcc.SelectWithLabel(
            id={"id": get_uuid("selector"), "component": "stype"},
            label="Surface Type",
            multi=False,
            options=[{"label": val, "value": val} for val in provider_content.stypes]
            if provider_content.stypes is not None
            else [],
            value=provider_content.selected_type,
        ),
    ]


def map_view(get_uuid):
    return wsc.DeckGLMap(id=get_uuid("deckgl"), layers=[], bounds=[0, 0, 10, 10])

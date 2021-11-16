from typing import List
from enum import Enum
from dash import html, dcc
import webviz_core_components as wcc

from webviz_subsurface._models import WellSetModel
from webviz_subsurface._private_plugins.surface_selector import format_date

from ..utils.formatting import format_date
from ..models.surface_set_model import SurfaceMode, SurfaceSetModel


class SurfaceSelectorLabel(Enum):
    WRAPPER = "Surface data"
    ATTRIBUTE = "Surface attribute"
    NAME = "Surface name / zone"
    DATE = "Surface time interval"
    ENSEMBLE = "Ensemble"
    MODE = "Mode"
    REALIZATIONS = "#Reals"


class SurfaceSelectorID(Enum):
    SELECTED_DATA = "surface-selected-data"
    ATTRIBUTE = "surface-attribute"
    NAME = "surface-name"
    DATE = "surface-date"
    ENSEMBLE = "surface-ensemble"
    MODE = "surface-mode"
    REALIZATIONS = "surface-realizations"


class WellSelectorLabel(str, Enum):
    WRAPPER = "Well data"
    WELLS = "Wells"
    LOG = "Log"


class WellSelectorID(str, Enum):
    WELLS = "wells"
    LOG = "log"


def surface_selector_view(
    get_uuid, surface_set_models: List[SurfaceSetModel]
) -> wcc.Selectors:
    ensembles = list(surface_set_models.keys())
    realizations = surface_set_models[ensembles[0]].realizations
    attributes = surface_set_models[ensembles[0]].attributes
    names = surface_set_models[ensembles[0]].names_in_attribute(attributes[0])
    dates = surface_set_models[ensembles[0]].dates_in_attribute(attributes[0])
    return wcc.Selectors(
        label=SurfaceSelectorLabel.WRAPPER,
        children=[
            dcc.Store(id=get_uuid(SurfaceSelectorID.SELECTED_DATA.value)),
            wcc.SelectWithLabel(
                label=SurfaceSelectorLabel.ATTRIBUTE,
                id=get_uuid(SurfaceSelectorID.ATTRIBUTE.value),
                options=[{"label": attr, "value": attr} for attr in attributes],
                value=[attributes[0]],
                multi=False,
            ),
            wcc.SelectWithLabel(
                label=SurfaceSelectorLabel.NAME,
                id=get_uuid(SurfaceSelectorID.NAME.value),
                options=[{"label": name, "value": name} for name in names],
                value=[names[0]],
                multi=False,
            ),
            wcc.SelectWithLabel(
                label=SurfaceSelectorLabel.DATE,
                id=get_uuid(SurfaceSelectorID.DATE.value),
                options=[{"label": format_date(date), "value": date} for date in dates]
                if dates
                else None,
                value=[dates[0]] if dates else None,
                multi=False,
            ),
            wcc.SelectWithLabel(
                label=SurfaceSelectorLabel.ENSEMBLE,
                id=get_uuid(SurfaceSelectorID.ENSEMBLE.value),
                options=[
                    {"label": ensemble, "value": ensemble} for ensemble in ensembles
                ],
                value=ensembles[0],
                multi=False,
            ),
            html.Div(
                style={"display": "grid", "gridTemplateColumns": "3fr 1fr"},
                children=[
                    wcc.RadioItems(
                        id=get_uuid(SurfaceSelectorID.MODE.value),
                        label=SurfaceSelectorLabel.MODE,
                        options=[
                            {"label": mode, "value": mode} for mode in SurfaceMode
                        ],
                        value=SurfaceMode.REALIZATION,
                    ),
                    wcc.SelectWithLabel(
                        label=SurfaceSelectorLabel.REALIZATIONS,
                        id=get_uuid(SurfaceSelectorID.REALIZATIONS.value),
                        options=[
                            {"label": real, "value": real} for real in realizations
                        ],
                        value=[realizations[0]],
                    ),
                ],
            ),
        ],
    )


def well_selector_view(get_uuid, well_set_model: WellSetModel) -> wcc.Selectors:
    return wcc.Selectors(
        label=WellSelectorLabel.WRAPPER,
        children=[
            wcc.SelectWithLabel(
                label=WellSelectorLabel.WELLS,
                id=get_uuid(WellSelectorID.WELLS),
                options=[
                    {"label": name, "value": name} for name in well_set_model.well_names
                ],
                value=well_set_model.well_names,
                size=min(len(well_set_model.well_names), 10),
            )
        ],
    )

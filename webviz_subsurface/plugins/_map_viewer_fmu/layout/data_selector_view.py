from typing import Callable, List
from enum import Enum
from dash import html, dcc
import webviz_core_components as wcc

from webviz_subsurface._models import WellSetModel
from webviz_subsurface._private_plugins.surface_selector import format_date

from ..utils.formatting import format_date
from ..models.surface_set_model import SurfaceMode, SurfaceSetModel
from webviz_subsurface.plugins._map_viewer_fmu.models import surface_set_model


class SurfaceSelectorLabel(str, Enum):
    WRAPPER = "Surface data"
    ATTRIBUTE = "Surface attribute"
    NAME = "Surface name / zone"
    DATE = "Surface time interval"
    ENSEMBLE = "Ensemble"
    MODE = "Mode"
    REALIZATIONS = "#Reals"


class SurfaceSelectorID(str, Enum):
    SELECTED_DATA = "surface-selected-data"
    ATTRIBUTE = "surface-attribute"
    NAME = "surface-name"
    DATE = "surface-date"
    ENSEMBLE = "surface-ensemble"
    MODE = "surface-mode"
    REALIZATIONS = "surface-realizations"


class SurfaceLinkID(str, Enum):
    ATTRIBUTE = "attribute"
    NAME = "name"
    DATE = "date"
    ENSEMBLE = "ensemble"
    REALIZATIONS = "realizations"
    MODE = "mode"


class WellSelectorLabel(str, Enum):
    WRAPPER = "Well data"
    WELLS = "Wells"
    LOG = "Log"


class WellSelectorID(str, Enum):
    WELLS = "wells"
    LOG = "log"


def selector_view(get_uuid, surface_set_models: List[SurfaceSetModel]) -> html.Div:
    ensembles = list(surface_set_models.keys())
    realizations = surface_set_models[ensembles[0]].realizations
    attributes = surface_set_models[ensembles[0]].attributes
    names = surface_set_models[ensembles[0]].names_in_attribute(attributes[0])
    dates = surface_set_models[ensembles[0]].dates_in_attribute(attributes[0])

    return html.Div(
        [
            dcc.Store(
                id={"view": "view1", "id": get_uuid(SurfaceSelectorID.SELECTED_DATA)}
            ),
            dcc.Store(
                id={"view": "view2", "id": get_uuid(SurfaceSelectorID.SELECTED_DATA)}
            ),
            EnsembleSelector(get_uuid=get_uuid, ensembles=ensembles),
            AttributeSelector(get_uuid=get_uuid, attributes=attributes),
            NameSelector(get_uuid=get_uuid, names=names),
            DateSelector(get_uuid=get_uuid, dates=dates),
            ModeSelector(get_uuid=get_uuid),
            RealizationSelector(get_uuid=get_uuid, realizations=realizations),
        ]
    )


class LinkCheckBox(wcc.Checklist):
    def __init__(self, component_id: str):
        self.id = component_id
        self.value = None
        # self.style = ({"position": "absolute", "top": 10},)
        self.options = [
            {
                "label": "🔗 Link",
                "value": component_id,
            }
        ]
        super().__init__(id=component_id, options=self.options)


class SideBySideSelector(html.Div):
    def __init__(self, style=None, *args, **kwargs):
        self.style = {} if style is None else style
        self.style.update(
            {
                "display": "grid",
                "grid-template-columns": " 1fr 1fr",
                "position": "relative",
            }
        )
        super().__init__(*args, **kwargs)


class EnsembleSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, ensembles: List[str]):
        return super().__init__(
            label="Ensemble",
            children=[
                LinkCheckBox(get_uuid(SurfaceLinkID.ENSEMBLE)),
                SideBySideSelector(
                    children=[
                        wcc.Dropdown(
                            id={
                                "view": "view1",
                                "id": get_uuid(SurfaceSelectorID.ENSEMBLE),
                            },
                            options=[
                                {"label": ensemble, "value": ensemble}
                                for ensemble in ensembles
                            ],
                            value=ensembles[0],
                            clearable=False,
                        ),
                        wcc.Dropdown(
                            id={
                                "view": "view2",
                                "id": get_uuid(SurfaceSelectorID.ENSEMBLE),
                            },
                            options=[
                                {"label": ensemble, "value": ensemble}
                                for ensemble in ensembles
                            ],
                            value=ensembles[0],
                            clearable=False,
                        ),
                    ]
                ),
            ],
        )


class AttributeSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, attributes: List[str]):
        return super().__init__(
            label=SurfaceSelectorLabel.ATTRIBUTE,
            children=[
                LinkCheckBox(get_uuid(SurfaceLinkID.ATTRIBUTE)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": "view1",
                                "id": get_uuid(SurfaceSelectorID.ATTRIBUTE),
                            },
                            options=[
                                {"label": ensemble, "value": ensemble}
                                for ensemble in attributes
                            ],
                            value=attributes[0],
                            multi=False,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": "view2",
                                "id": get_uuid(SurfaceSelectorID.ATTRIBUTE),
                            },
                            options=[
                                {"label": ensemble, "value": ensemble}
                                for ensemble in attributes
                            ],
                            value=attributes[0],
                            multi=False,
                        ),
                    ]
                ),
            ],
        )


class NameSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, names: List[str]):
        return super().__init__(
            label=SurfaceSelectorLabel.NAME,
            children=[
                LinkCheckBox(get_uuid(SurfaceLinkID.NAME)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": "view1",
                                "id": get_uuid(SurfaceSelectorID.NAME),
                            },
                            options=[{"label": name, "value": name} for name in names],
                            value=names[0],
                            multi=False,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": "view2",
                                "id": get_uuid(SurfaceSelectorID.NAME),
                            },
                            options=[{"label": name, "value": name} for name in names],
                            value=names[0],
                            multi=False,
                        ),
                    ]
                ),
            ],
        )


class DateSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, dates: List[str]):
        return super().__init__(
            label=SurfaceSelectorLabel.DATE,
            children=[
                LinkCheckBox(get_uuid(SurfaceLinkID.DATE)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": "view1",
                                "id": get_uuid(SurfaceSelectorID.DATE),
                            },
                            options=[
                                {"label": format_date(date), "value": date}
                                for date in dates
                            ],
                            value=dates[0],
                            multi=False,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": "view2",
                                "id": get_uuid(SurfaceSelectorID.DATE),
                            },
                            options=[
                                {"label": format_date(date), "value": date}
                                for date in dates
                            ],
                            value=dates[0],
                            multi=False,
                        ),
                    ]
                ),
            ],
        )


class ModeSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable):
        return super().__init__(
            label=SurfaceSelectorLabel.MODE,
            children=[
                LinkCheckBox(get_uuid(SurfaceLinkID.MODE)),
                SideBySideSelector(
                    children=[
                        wcc.Dropdown(
                            id={
                                "view": "view1",
                                "id": get_uuid(SurfaceSelectorID.MODE),
                            },
                            options=[
                                {"label": mode, "value": mode} for mode in SurfaceMode
                            ],
                            value=SurfaceMode.REALIZATION,
                            clearable=False,
                        ),
                        wcc.Dropdown(
                            id={
                                "view": "view2",
                                "id": get_uuid(SurfaceSelectorID.MODE),
                            },
                            options=[
                                {"label": mode, "value": mode} for mode in SurfaceMode
                            ],
                            value=SurfaceMode.REALIZATION,
                            clearable=False,
                        ),
                    ]
                ),
            ],
        )


class RealizationSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, realizations: List[str]):
        return super().__init__(
            label=SurfaceSelectorLabel.REALIZATIONS,
            children=[
                LinkCheckBox(get_uuid(SurfaceLinkID.REALIZATIONS)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": "view1",
                                "id": get_uuid(SurfaceSelectorID.REALIZATIONS),
                            },
                            options=[
                                {"label": real, "value": real} for real in realizations
                            ],
                            value=realizations[0],
                            multi=False,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": "view2",
                                "id": get_uuid(SurfaceSelectorID.REALIZATIONS),
                            },
                            options=[
                                {"label": real, "value": real} for real in realizations
                            ],
                            value=realizations[0],
                            multi=False,
                        ),
                    ]
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

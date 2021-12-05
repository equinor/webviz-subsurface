from enum import Enum, auto, unique
from typing import Callable, List, Dict, Any, Optional


import webviz_core_components as wcc
from dash import dcc, html

from webviz_subsurface._components.deckgl_map import DeckGLMapAIO  # type: ignore
from webviz_subsurface._components.deckgl_map.types.deckgl_props import (
    ColormapLayer,
    DrawingLayer,
    Hillshading2DLayer,
    WellsLayer,
)
from webviz_subsurface._models import WellSetModel

from .models.surface_set_model import SurfaceMode, SurfaceSetModel
from .utils.formatting import format_date


@unique
class LayoutElements(str, Enum):
    """Contains all ids used in plugin. Note that some id's are
    used as combinations of LEFT/RIGHT_VIEW together with other elements to
    support pattern matching callbacks."""

    SELECTED_DATA = auto()
    ATTRIBUTE = auto()
    NAME = auto()
    DATE = auto()
    ENSEMBLE = auto()
    MODE = auto()
    REALIZATIONS = auto()
    LINK_ATTRIBUTE = auto()
    LINK_NAME = auto()
    LINK_DATE = auto()
    LINK_ENSEMBLE = auto()
    LINK_REALIZATIONS = auto()
    LINK_MODE = auto()
    WELLS = auto()
    LINK_WELLS = auto()
    LOG = auto()
    DECKGLMAP_LEFT = auto()
    DECKGLMAP_LEFT_WRAPPER = auto()
    DECKGLMAP_RIGHT_WRAPPER = auto()
    DECKGLMAP_RIGHT = auto()
    LEFT_VIEW = auto()
    RIGHT_VIEW = auto()
    COLORMAP_RANGE = auto()
    COLORMAP_SELECT = auto()
    COLORMAP_KEEP_RANGE = auto()
    COLORMAP_RESET_RANGE = auto()
    LINK_COLORMAP_RANGE = auto()
    LINK_COLORMAP_SELECT = auto()


class LayoutLabels(str, Enum):
    """Text labels used in layout components"""

    ATTRIBUTE = "Surface attribute"
    NAME = "Surface name / zone"
    DATE = "Surface time interval"
    ENSEMBLE = "Ensemble"
    MODE = "Aggregation"
    REALIZATIONS = "Realization(s)"
    WELLS = "Wells"
    LOG = "Log"
    COLORMAP_WRAPPER = "Surface coloring"
    COLORMAP_SELECT = "Colormap"
    COLORMAP_RANGE = "Value range"
    COLORMAP_RESET_RANGE = "Reset range"
    COLORMAP_KEEP_RANGE_OPTIONS = "Keep range"
    LINK = "🔗 Link"


class LayoutStyle:
    """CSS styling"""

    SIDEBAR = {"flex": 3, "height": "90vh"}
    LEFT_MAP = {"flex": 5, "height": "90vh"}
    RIGHT_MAP = {"flex": 5}
    SIDE_BY_SIDE = {
        "display": "grid",
        "grid-template-columns": " 1fr 1fr",
        "position": "relative",
    }


class FullScreen(wcc.WebvizPluginPlaceholder):
    def __init__(self, id: str, children: List[Any]) -> None:
        super().__init__(id=id, buttons=["expand", "screenshot"], children=children)


def main_layout(
    get_uuid: Callable,
    surface_set_models: Dict[str, SurfaceSetModel],
    well_set_model: Optional[WellSetModel],
) -> None:
    ensembles = list(surface_set_models.keys())
    realizations = surface_set_models[ensembles[0]].realizations
    attributes = surface_set_models[ensembles[0]].attributes
    names = surface_set_models[ensembles[0]].names_in_attribute(attributes[0])
    dates = surface_set_models[ensembles[0]].dates_in_attribute(attributes[0])

    return wcc.FlexBox(
        children=[
            wcc.Frame(
                style=LayoutStyle.SIDEBAR,
                children=list(
                    filter(
                        None,
                        [
                            DataStores(get_uuid=get_uuid),
                            EnsembleSelector(get_uuid=get_uuid, ensembles=ensembles),
                            AttributeSelector(get_uuid=get_uuid, attributes=attributes),
                            NameSelector(get_uuid=get_uuid, names=names),
                            DateSelector(
                                get_uuid=get_uuid,
                                dates=dates if dates is not None else [],
                            ),
                            ModeSelector(get_uuid=get_uuid),
                            RealizationSelector(
                                get_uuid=get_uuid, realizations=realizations
                            ),
                            well_set_model
                            and WellsSelector(
                                get_uuid=get_uuid, wells=well_set_model.well_names
                            ),
                            SurfaceColorSelector(get_uuid=get_uuid),
                        ],
                    )
                ),
            ),
            html.Div(
                style={"flex": 5, "height": "90vh"},
                children=FullScreen(
                    id=get_uuid(LayoutElements.DECKGLMAP_LEFT_WRAPPER),
                    children=[
                        wcc.Frame(
                            color="white",
                            highlight=False,
                            style=LayoutStyle.LEFT_MAP,
                            children=[
                                DeckGLMapAIO(
                                    aio_id=get_uuid(LayoutElements.DECKGLMAP_LEFT),
                                    layers=[
                                        ColormapLayer(),
                                        Hillshading2DLayer(),
                                        WellsLayer(),
                                        DrawingLayer(),
                                    ],
                                ),
                            ],
                        )
                    ],
                ),
            ),
            wcc.Frame(
                style=LayoutStyle.RIGHT_MAP,
                children=[
                    DeckGLMapAIO(
                        aio_id=get_uuid(LayoutElements.DECKGLMAP_RIGHT),
                        layers=[
                            ColormapLayer(),
                            Hillshading2DLayer(),
                            WellsLayer(),
                            DrawingLayer(),
                        ],
                    ),
                ],
            ),
        ],
    )


class DataStores(html.Div):
    def __init__(self, get_uuid: Callable) -> None:
        super().__init__(
            children=[
                dcc.Store(
                    id={
                        "view": LayoutElements.LEFT_VIEW,
                        "id": get_uuid(LayoutElements.SELECTED_DATA),
                    }
                ),
                dcc.Store(
                    id={
                        "view": LayoutElements.RIGHT_VIEW,
                        "id": get_uuid(LayoutElements.SELECTED_DATA),
                    }
                ),
            ]
        )


class LinkCheckBox(wcc.Checklist):
    def __init__(self, component_id: str):
        self.id = component_id
        self.value = None
        self.options = [
            {
                "label": LayoutLabels.LINK,
                "value": component_id,
            }
        ]
        super().__init__(id=component_id, options=self.options)


class SideBySideSelector(html.Div):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(style=LayoutStyle.SIDE_BY_SIDE, *args, **kwargs)


class EnsembleSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, ensembles: List[str]):
        return super().__init__(
            label=LayoutLabels.ENSEMBLE,
            children=[
                LinkCheckBox(get_uuid(LayoutElements.LINK_ENSEMBLE)),
                SideBySideSelector(
                    children=[
                        wcc.Dropdown(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.ENSEMBLE),
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
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.ENSEMBLE),
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
            label=LayoutLabels.ATTRIBUTE,
            children=[
                LinkCheckBox(get_uuid(LayoutElements.LINK_ATTRIBUTE)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.ATTRIBUTE),
                            },
                            size=len(attributes),
                            options=[
                                {"label": ensemble, "value": ensemble}
                                for ensemble in attributes
                            ],
                            value=[attributes[0]],
                            multi=False,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.ATTRIBUTE),
                            },
                            options=[
                                {"label": ensemble, "value": ensemble}
                                for ensemble in attributes
                            ],
                            size=len(attributes),
                            value=[attributes[0]],
                            multi=False,
                        ),
                    ]
                ),
            ],
        )


class NameSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, names: List[str]):
        return super().__init__(
            label=LayoutLabels.NAME,
            children=[
                LinkCheckBox(get_uuid(LayoutElements.LINK_NAME)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.NAME),
                            },
                            size=max(5, len(names)),
                            options=[{"label": name, "value": name} for name in names],
                            value=[names[0]],
                            multi=False,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.NAME),
                            },
                            size=max(5, len(names)),
                            options=[{"label": name, "value": name} for name in names],
                            value=[names[0]],
                            multi=False,
                        ),
                    ]
                ),
            ],
        )


class DateSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, dates: List[str]):
        return super().__init__(
            label=LayoutLabels.DATE,
            children=[
                LinkCheckBox(get_uuid(LayoutElements.LINK_DATE)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.DATE),
                            },
                            size=max(5, len(dates)),
                            options=[
                                {"label": format_date(date), "value": date}
                                for date in dates
                            ],
                            value=[dates[0]],
                            multi=False,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.DATE),
                            },
                            options=[
                                {"label": format_date(date), "value": date}
                                for date in dates
                            ],
                            size=max(5, len(dates)),
                            value=[dates[0]],
                            multi=False,
                        ),
                    ]
                ),
            ],
        )


class ModeSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable):
        return super().__init__(
            label=LayoutLabels.MODE,
            children=[
                LinkCheckBox(get_uuid(LayoutElements.LINK_MODE)),
                SideBySideSelector(
                    children=[
                        wcc.Dropdown(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.MODE),
                            },
                            options=[
                                {"label": mode, "value": mode} for mode in SurfaceMode
                            ],
                            value=SurfaceMode.REALIZATION,
                            clearable=False,
                        ),
                        wcc.Dropdown(
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.MODE),
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
            label=LayoutLabels.REALIZATIONS,
            open_details=False,
            children=[
                wcc.Label(
                    "Single selection or subset "
                    "for statistics dependent on aggregation mode."
                ),
                LinkCheckBox(get_uuid(LayoutElements.LINK_REALIZATIONS)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.REALIZATIONS),
                            },
                            options=[
                                {"label": real, "value": real} for real in realizations
                            ],
                            size=min(len(realizations), 50),
                            value=[realizations[0]],
                            multi=False,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.REALIZATIONS),
                            },
                            options=[
                                {"label": real, "value": real} for real in realizations
                            ],
                            size=min(len(realizations), 50),
                            value=[realizations[0]],
                            multi=False,
                        ),
                    ]
                ),
            ],
        )


class WellsSelector(wcc.Selectors):
    def __init__(self, get_uuid: Callable, wells: List[str]):
        return super().__init__(
            label=LayoutLabels.WELLS,
            open_details=False,
            children=[
                LinkCheckBox(get_uuid(LayoutElements.LINK_WELLS)),
                SideBySideSelector(
                    children=[
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.WELLS),
                            },
                            options=[{"label": well, "value": well} for well in wells],
                            size=min(len(wells), 50),
                            value=wells,
                            multi=True,
                        ),
                        wcc.SelectWithLabel(
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.WELLS),
                            },
                            options=[{"label": well, "value": well} for well in wells],
                            size=min(len(wells), 50),
                            value=wells,
                            multi=True,
                        ),
                    ]
                ),
            ],
        )


class SurfaceColorSelector(wcc.Selectors):
    def __init__(
        self, get_uuid: Callable, colormaps: List[str] = ["viridis_r", "seismic"]
    ):
        return super().__init__(
            label=LayoutLabels.COLORMAP_WRAPPER,
            open_details=False,
            children=[
                LinkCheckBox(get_uuid(LayoutElements.LINK_COLORMAP_SELECT)),
                SideBySideSelector(
                    children=[
                        wcc.Dropdown(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.COLORMAP_SELECT),
                            },
                            options=[
                                {"label": colormap, "value": colormap}
                                for colormap in colormaps
                            ],
                            value=colormaps[0],
                        ),
                        wcc.Dropdown(
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.COLORMAP_SELECT),
                            },
                            options=[
                                {"label": colormap, "value": colormap}
                                for colormap in colormaps
                            ],
                            value=colormaps[0],
                        ),
                    ]
                ),
                LinkCheckBox(get_uuid(LayoutElements.LINK_COLORMAP_RANGE)),
                SideBySideSelector(
                    children=[
                        wcc.RangeSlider(
                            label=LayoutLabels.COLORMAP_RANGE,
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.COLORMAP_RANGE),
                            },
                            updatemode="drag",
                            tooltip={
                                "always_visible": True,
                                "placement": "bottomLeft",
                            },
                        ),
                        wcc.RangeSlider(
                            label=LayoutLabels.COLORMAP_RANGE,
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.COLORMAP_RANGE),
                            },
                            updatemode="drag",
                            tooltip={
                                "always_visible": True,
                                "placement": "bottomLeft",
                            },
                        ),
                    ]
                ),
                SideBySideSelector(
                    children=[
                        wcc.Checklist(
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.COLORMAP_KEEP_RANGE),
                            },
                            options=[
                                {
                                    "label": LayoutLabels.COLORMAP_KEEP_RANGE_OPTIONS,
                                    "value": LayoutLabels.COLORMAP_KEEP_RANGE_OPTIONS,
                                }
                            ],
                        ),
                        wcc.Checklist(
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.COLORMAP_KEEP_RANGE),
                            },
                            options=[
                                {
                                    "label": LayoutLabels.COLORMAP_KEEP_RANGE_OPTIONS,
                                    "value": LayoutLabels.COLORMAP_KEEP_RANGE_OPTIONS,
                                }
                            ],
                        ),
                    ]
                ),
                SideBySideSelector(
                    children=[
                        html.Button(
                            children=LayoutLabels.COLORMAP_RESET_RANGE,
                            style={"marginTop": "5px"},
                            id={
                                "view": LayoutElements.LEFT_VIEW,
                                "id": get_uuid(LayoutElements.COLORMAP_RESET_RANGE),
                            },
                        ),
                        html.Button(
                            children=LayoutLabels.COLORMAP_RESET_RANGE,
                            style={"marginTop": "5px"},
                            id={
                                "view": LayoutElements.RIGHT_VIEW,
                                "id": get_uuid(LayoutElements.COLORMAP_RESET_RANGE),
                            },
                        ),
                    ]
                ),
            ],
        )

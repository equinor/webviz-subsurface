from typing import Callable, Dict, List, Optional

import webviz_core_components as wcc
from dash import dcc, html

from .dialog import open_dialog_layout


def intersection_data_layout(
    get_uuid: Callable,
    surface_attributes: List[str],
    surface_names: List[str],
    ensembles: List[str],
    use_wells: bool,
    well_names: List[str],
    surface_geometry: Dict,
    initial_settings: Dict,
) -> html.Div:
    """Layout for selecting intersection data"""
    return html.Div(
        id=get_uuid("intersection-data-wrapper"),
        children=[
            html.Div(
                style={
                    "padding-bottom": "10px",
                    "border-bottom-style": "solid",
                    "border-width": "thin",
                    "border-color": "grey",
                },
                id=get_uuid("intersection-source-wrapper"),
                children=[
                    source_layout(
                        uuid=get_uuid("intersection-data"),
                        use_wells=use_wells,
                    ),
                    well_layout(
                        uuid=get_uuid("intersection-data"),
                        well_names=well_names,
                        value=initial_settings.get(
                            "well",
                            well_names[0] if use_wells else None,
                        ),
                    ),
                    xline_layout(
                        uuid=get_uuid("intersection-data"),
                        surface_geometry=surface_geometry,
                    ),
                    yline_layout(
                        uuid=get_uuid("intersection-data"),
                        surface_geometry=surface_geometry,
                    ),
                ],
            ),
            surface_attribute_layout(
                uuid=get_uuid("intersection-data"),
                surface_attributes=surface_attributes,
                value=initial_settings.get(
                    "surface_attribute",
                    surface_attributes[0],
                ),
            ),
            surface_names_layout(
                uuid=get_uuid("intersection-data"),
                surface_names=surface_names,
                value=initial_settings.get("surface_names", [surface_names[0]]),
            ),
            ensemble_layout(
                uuid=get_uuid("intersection-data"),
                ensemble_names=ensembles,
                value=initial_settings.get("ensembles", [ensembles[0]]),
            ),
            statistical_layout(
                uuid=get_uuid("intersection-data"),
                value=initial_settings.get("calculation", ["Mean", "Min", "Max"]),
            ),
            blue_apply_button(
                uuid=get_uuid("apply-intersection-data-selections"),
                title="Update intersection",
            ),
            open_dialog_layout(
                dialog_id="uncertainty-table",
                uuid=get_uuid("dialog"),
                title="Uncertainty table",
            ),
            settings_layout(get_uuid, initial_settings=initial_settings),
        ],
    )


def source_layout(uuid: str, use_wells: bool = True) -> html.Div:
    options = [
        {"label": "Intersect polyline from Surface A", "value": "polyline"},
        {"label": "Intersect x-line from Surface A", "value": "xline"},
        {"label": "Intersect y-line from Surface A", "value": "yline"},
    ]
    if use_wells:
        options.append({"label": "Intersect well", "value": "well"})
    return wcc.Dropdown(
        label="Intersection source",
        id={"id": uuid, "element": "source"},
        options=options,
        value="well" if use_wells else "polyline",
        clearable=False,
    )


def well_layout(
    uuid: str, well_names: List[str], value: Optional[str] = None
) -> html.Div:
    return html.Div(
        style={
            "display": "none",
        }
        if value is None
        else {},
        id={"id": uuid, "element": "well-wrapper"},
        children=wcc.Dropdown(
            label="Well",
            id={"id": uuid, "element": "well"},
            options=[{"label": well, "value": well} for well in well_names],
            value=value,
            clearable=False,
        ),
    )


def xline_layout(uuid: str, surface_geometry: Dict) -> html.Div:
    return html.Div(
        style={
            "display": "none",
        },
        id={"id": uuid, "element": "xline-wrapper"},
        children=[
            html.Label("X-Line:"),
            wcc.FlexBox(
                style={"fontSize": "0.8em"},
                children=[
                    dcc.Input(
                        id={"id": uuid, "cross-section": "xline", "element": "value"},
                        style={"flex": 3, "minWidth": "100px"},
                        type="number",
                        value=round(surface_geometry["xmin"]),
                        min=round(surface_geometry["xmin"]),
                        max=round(surface_geometry["xmax"]),
                        step=500,
                        persistence=True,
                        persistence_type="session",
                    ),
                    wcc.Label(
                        style={"flex": 1, "marginLeft": "10px", "minWidth": "20px"},
                        children="Step:",
                    ),
                    dcc.Input(
                        id={"id": uuid, "cross-section": "xline", "element": "step"},
                        style={"flex": 2, "minWidth": "20px"},
                        value=500,
                        type="number",
                        min=1,
                        max=round(surface_geometry["xmax"])
                        - round(surface_geometry["xmin"]),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ],
    )


def yline_layout(uuid: str, surface_geometry: Dict) -> html.Div:
    return html.Div(
        style={
            "display": "none",
        },
        id={"id": uuid, "element": "yline-wrapper"},
        children=[
            html.Label("Y-Line:"),
            wcc.FlexBox(
                style={"fontSize": "0.8em"},
                children=[
                    dcc.Input(
                        id={"id": uuid, "cross-section": "yline", "element": "value"},
                        style={"flex": 3, "minWidth": "100px"},
                        type="number",
                        value=round(surface_geometry["ymin"]),
                        min=round(surface_geometry["ymin"]),
                        max=round(surface_geometry["ymax"]),
                        step=50,
                        persistence=True,
                        persistence_type="session",
                    ),
                    wcc.Label(
                        style={"flex": 1, "marginLeft": "10px", "minWidth": "20px"},
                        children="Step:",
                    ),
                    dcc.Input(
                        id={"id": uuid, "cross-section": "yline", "element": "step"},
                        style={"flex": 2, "minWidth": "20px"},
                        value=50,
                        type="number",
                        min=1,
                        max=round(surface_geometry["ymax"])
                        - round(surface_geometry["ymin"]),
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
        ],
    )


def surface_attribute_layout(
    uuid: str, surface_attributes: List[str], value: str
) -> html.Div:
    return wcc.Dropdown(
        label="Surface attribute",
        id={"id": uuid, "element": "surface_attribute"},
        options=[
            {"label": attribute, "value": attribute} for attribute in surface_attributes
        ],
        value=value,
        clearable=False,
        multi=False,
    )


def surface_names_layout(
    uuid: str, surface_names: List[str], value: List[str]
) -> html.Div:
    return wcc.SelectWithLabel(
        label="Surface names",
        id={"id": uuid, "element": "surface_names"},
        options=[
            {"label": attribute, "value": attribute} for attribute in surface_names
        ],
        value=value,
        multi=True,
        size=min(len(surface_names), 5),
    )


def ensemble_layout(uuid: str, ensemble_names: List[str], value: List[str]) -> html.Div:
    return html.Div(
        style={
            "marginTop": "5px",
            "display": ("inline" if len(ensemble_names) > 1 else "none"),
        },
        children=wcc.SelectWithLabel(
            label="Ensembles",
            id={"id": uuid, "element": "ensembles"},
            options=[{"label": ens, "value": ens} for ens in ensemble_names],
            value=value,
            size=min(len(ensemble_names), 3),
        ),
    )


def statistical_layout(uuid: str, value: List[str]) -> html.Div:
    return wcc.Checklist(
        label="Show surfaces",
        id={"id": uuid, "element": "calculation"},
        options=[
            {"label": "Mean", "value": "Mean"},
            {"label": "Min", "value": "Min"},
            {"label": "Max", "value": "Max"},
            {"label": "Realizations", "value": "Realizations"},
            {
                "label": "Uncertainty envelope",
                "value": "Uncertainty envelope",
            },
        ],
        value=value,
    )


def blue_apply_button(uuid: str, title: str) -> html.Div:
    return html.Button(
        title,
        className="webviz-structunc-blue-apply-btn",
        id=uuid,
    )


def options_layout(
    uuid: str,
    depth_truncations: Dict,
    resolution: float,
    extension: int,
    initial_layout: Dict,
) -> html.Div:

    return html.Div(
        children=[
            html.Div(
                children=[
                    wcc.Label(
                        "Resolution (m) ",
                    ),
                    dcc.Input(
                        className="webviz-structunc-range-input",
                        id={"id": uuid, "element": "resolution"},
                        type="number",
                        required=True,
                        value=resolution,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
            html.Div(
                children=[
                    wcc.Label(
                        "Extension (m) ",
                    ),
                    dcc.Input(
                        className="webviz-structunc-range-input",
                        id={"id": uuid, "element": "extension"},
                        type="number",
                        step=25,
                        required=True,
                        value=extension,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
            html.Div(
                style={"margin-top": "10px"},
                children=[
                    wcc.Label("Depth range settings:"),
                    wcc.FlexBox(
                        style={"display": "flex"},
                        children=[
                            dcc.Input(
                                id={
                                    "id": uuid,
                                    "settings": "zrange_min",
                                },
                                style={"flex": 1, "minWidth": "70px"},
                                type="number",
                                value=depth_truncations.get("min", None),
                                debounce=True,
                                placeholder="Min",
                                persistence=True,
                                persistence_type="session",
                            ),
                            dcc.Input(
                                id={
                                    "id": uuid,
                                    "settings": "zrange_max",
                                },
                                style={"flex": 1, "minWidth": "70px"},
                                type="number",
                                value=depth_truncations.get("max", None),
                                debounce=True,
                                placeholder="Max",
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                    wcc.RadioItems(
                        id={
                            "id": uuid,
                            "settings": "zrange_locks",
                        },
                        options=[
                            {
                                "label": "Truncate range",
                                "value": "truncate",
                            },
                            {
                                "label": "Lock range",
                                "value": "lock",
                            },
                        ],
                        value="truncate",
                    ),
                    wcc.Checklist(
                        id={
                            "id": uuid,
                            "settings": "ui_options",
                        },
                        options=[
                            {"label": "Keep zoom state", "value": "uirevision"},
                        ],
                        value=["uirevision"] if "uirevision" in initial_layout else [],
                    ),
                ],
            ),
        ],
    )


def settings_layout(get_uuid: Callable, initial_settings: Dict) -> html.Div:
    return wcc.Selectors(
        open_details=False,
        label="⚙️ Settings",
        children=[
            options_layout(
                uuid=get_uuid("intersection-data"),
                depth_truncations=initial_settings.get("depth_truncations", {}),
                resolution=initial_settings.get("resolution", 10),
                extension=initial_settings.get("extension", 500),
                initial_layout=initial_settings.get("intersection_layout", {}),
            ),
            open_dialog_layout(
                dialog_id="color",
                uuid=get_uuid("dialog"),
                title="Intersection colors",
            ),
        ],
    )

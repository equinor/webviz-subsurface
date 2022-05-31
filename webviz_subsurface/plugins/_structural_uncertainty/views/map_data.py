from typing import List

import webviz_core_components as wcc
from dash import dcc, html


def map_data_layout(
    uuid: str,
    surface_attributes: List[str],
    surface_names: List[str],
    ensembles: List[str],
    realizations: List[int],
    use_wells: bool,
) -> html.Div:
    """Layout for the map data dialog"""
    return html.Div(
        children=[
            wcc.Selectors(
                label="Surface A",
                children=make_map_selectors(
                    uuid=uuid,
                    surface_attributes=surface_attributes,
                    surface_names=surface_names,
                    ensembles=ensembles,
                    realizations=realizations,
                    use_wells=use_wells,
                    map_id="map1",
                ),
            ),
            wcc.Selectors(
                label="Surface B",
                children=make_map_selectors(
                    uuid=uuid,
                    surface_attributes=surface_attributes,
                    surface_names=surface_names,
                    ensembles=ensembles,
                    realizations=realizations,
                    use_wells=use_wells,
                    map_id="map2",
                ),
            ),
            settings_layout(uuid=uuid),
        ]
    )


def make_map_selectors(
    uuid: str,
    map_id: str,
    surface_attributes: List[str],
    surface_names: List[str],
    ensembles: List[str],
    realizations: List[int],
    use_wells: bool,
) -> html.Div:
    return html.Div(
        children=[
            wcc.Dropdown(
                label="Surface attribute",
                id={"id": uuid, "map_id": map_id, "element": "surfaceattribute"},
                options=[{"label": val, "value": val} for val in surface_attributes],
                value=surface_attributes[0],
                clearable=False,
            ),
            wcc.Dropdown(
                label="Surface name",
                id={"id": uuid, "map_id": map_id, "element": "surfacename"},
                options=[{"label": val, "value": val} for val in surface_names],
                value=surface_names[0],
                clearable=False,
            ),
            html.Div(
                style={"display": ("inline" if len(ensembles) > 1 else "none")},
                children=[
                    wcc.Dropdown(
                        label="Ensemble",
                        id={"id": uuid, "map_id": map_id, "element": "ensemble"},
                        options=[{"label": val, "value": val} for val in ensembles],
                        value=ensembles[0],
                        clearable=False,
                    ),
                ],
            ),
            wcc.Dropdown(
                label="Calculation/Realization",
                id={"id": uuid, "map_id": map_id, "element": "calculation"},
                options=[
                    {"label": val, "value": val}
                    for val in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]
                    + [str(real) for real in realizations]
                ],
                value=str(realizations[0]),
                clearable=False,
            ),
            wcc.Checklist(
                id={"id": uuid, "map_id": map_id, "element": "options"},
                options=[
                    {"label": "Calculate well intersections", "value": "intersect_well"}
                ]
                if use_wells
                else [],
                value=[],
            ),
        ]
    )


def settings_layout(uuid: str) -> html.Details:
    return wcc.Selectors(
        open_details=False,
        label="⚙️ Settings",
        children=[
            wcc.Checklist(
                id={"id": uuid, "settings": "compute_diff"},
                options=[
                    {
                        "label": "Auto compute difference map",
                        "value": "compute_diffmap",
                    }
                ],
                value=["compute_diffmap"],
            ),
            html.Div(
                children=[
                    wcc.Label(
                        "Color ranges:",
                        style={"font-weight": "bold"},
                    ),
                    color_range_layout(uuid=uuid, map_id="map1"),
                    color_range_layout(uuid=uuid, map_id="map2"),
                    wcc.Checklist(
                        id={"id": uuid, "colors": "sync_range"},
                        options=[
                            {
                                "label": "Sync range on maps",
                                "value": "sync_range",
                            }
                        ],
                        value=[],
                    ),
                ],
            ),
        ],
    )


def color_range_layout(uuid: str, map_id: str) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"display": "flex", "align-items": "center"},
        children=[
            wcc.Label(
                "Surface A" if map_id == "map1" else "Surface B",
                style={"flex": 1, "minWidth": "40px"},
            ),
            dcc.Input(
                id={
                    "id": uuid,
                    "colors": f"{map_id}_clip_min",
                },
                style={"flex": 1, "minWidth": "40px"},
                type="number",
                value=None,
                debounce=True,
                placeholder="Min",
                persistence=True,
                persistence_type="session",
            ),
            dcc.Input(
                id={
                    "id": uuid,
                    "colors": f"{map_id}_clip_max",
                },
                style={"flex": 1, "minWidth": "40px"},
                type="number",
                value=None,
                debounce=True,
                placeholder="Max",
                persistence=True,
                persistence_type="session",
            ),
        ],
    )

from typing import List

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import webviz_core_components as wcc


def map_data_layout(
    uuid: str,
    surface_attributes: List[str],
    surface_names: List[str],
    ensembles: List[str],
    realizations: List[int],
    use_wells: bool,
) -> html.Div:
    """Layout for the map data modal"""
    return html.Div(
        children=[
            html.Details(
                open=True,
                children=[
                    html.Summary(
                        style={
                            "font-size": "15px",
                            "font-weight": "bold",
                        },
                        children="Surface A",
                    ),
                    html.Div(
                        make_map_selectors(
                            uuid=uuid,
                            surface_attributes=surface_attributes,
                            surface_names=surface_names,
                            ensembles=ensembles,
                            realizations=realizations,
                            use_wells=use_wells,
                            map_id="map1",
                        ),
                    ),
                ],
            ),
            html.Details(
                style={
                    "marginTop": "15px",
                    "marginBottom": "10px",
                },
                open=False,
                children=[
                    html.Summary(
                        style={
                            "font-size": "15px",
                            "font-weight": "bold",
                        },
                        children="Surface B",
                    ),
                    html.Div(
                        make_map_selectors(
                            uuid=uuid,
                            surface_attributes=surface_attributes,
                            surface_names=surface_names,
                            ensembles=ensembles,
                            realizations=realizations,
                            use_wells=use_wells,
                            map_id="map2",
                        ),
                    ),
                ],
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
            html.Label(
                "Surface attribute", style={"fontSize": "0.8em", "fontWeight": "bold"}
            ),
            dcc.Dropdown(
                id={"id": uuid, "map_id": map_id, "element": "surfaceattribute"},
                options=[{"label": val, "value": val} for val in surface_attributes],
                value=surface_attributes[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
            html.Label(
                "Surface name", style={"fontSize": "0.8em", "fontWeight": "bold"}
            ),
            dcc.Dropdown(
                id={"id": uuid, "map_id": map_id, "element": "surfacename"},
                options=[{"label": val, "value": val} for val in surface_names],
                value=surface_names[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
            html.Div(
                style={"display": ("inline" if len(ensembles) > 1 else "none")},
                children=[
                    html.Label(
                        "Ensemble", style={"fontSize": "0.8em", "fontWeight": "bold"}
                    ),
                    dcc.Dropdown(
                        id={"id": uuid, "map_id": map_id, "element": "ensemble"},
                        options=[{"label": val, "value": val} for val in ensembles],
                        value=ensembles[0],
                        clearable=False,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
            html.Label(
                "Calculation/Realization",
                style={"fontSize": "0.8em", "fontWeight": "bold"},
            ),
            dcc.Dropdown(
                id={"id": uuid, "map_id": map_id, "element": "calculation"},
                options=[
                    {"label": val, "value": val}
                    for val in ["Mean", "StdDev", "Max", "Min", "P90", "P10"]
                    + [str(real) for real in realizations]
                ],
                value=realizations[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
            dcc.Checklist(
                style={"marginTop": "10px"},
                id={"id": uuid, "map_id": map_id, "element": "options"},
                options=[
                    {"label": "Calculate well intersections", "value": "intersect_well"}
                ]
                if use_wells
                else [],
                value=[],
                persistence=True,
                persistence_type="session",
            ),
        ]
    )


def settings_layout(uuid: str) -> html.Details:
    return html.Details(
        className="webviz-structunc-settings",
        open=False,
        children=[
            html.Summary(
                style={
                    "font-size": "15px",
                    "font-weight": "bold",
                },
                children="⚙️ Settings",
            ),
            html.Div(
                style={"padding": "10px"},
                children=[
                    dcc.Checklist(
                        id={"id": uuid, "settings": "compute_diff"},
                        options=[
                            {
                                "label": "Auto compute difference map",
                                "value": "compute_diffmap",
                            }
                        ],
                        value=["compute_diffmap"],
                        persistence=True,
                        persistence_type="session",
                    ),
                    html.Div(
                        style={"margin-top": "10px"},
                        children=[
                            html.Label(
                                "Color ranges:",
                                style={"font-weight": "bold"},
                            ),
                            color_range_layout(uuid=uuid, map_id="map1"),
                            color_range_layout(uuid=uuid, map_id="map2"),
                            dcc.Checklist(
                                id={"id": uuid, "colors": "sync_range"},
                                options=[
                                    {
                                        "label": "Sync range on maps",
                                        "value": "sync_range",
                                    }
                                ],
                                value=[],
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def color_range_layout(uuid: str, map_id: str) -> wcc.FlexBox:
    return wcc.FlexBox(
        style={"display": "flex", "align-items": "center"},
        children=[
            html.Div(
                "Surface A" if map_id == "map1" else "Surface B",
                style={"flex": 1, "minWidth": "70px"},
            ),
            dbc.Input(
                id={
                    "id": uuid,
                    "colors": f"{map_id}_clip_min",
                },
                style={"flex": 1, "minWidth": "70px"},
                type="number",
                value=None,
                debounce=True,
                placeholder="Min",
                persistence=True,
                persistence_type="session",
            ),
            dbc.Input(
                id={
                    "id": uuid,
                    "colors": f"{map_id}_clip_max",
                },
                style={"flex": 1, "minWidth": "70px"},
                type="number",
                value=None,
                debounce=True,
                placeholder="Max",
                persistence=True,
                persistence_type="session",
            ),
        ],
    )

from typing import List, Optional
import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc
from webviz_config import WebvizConfigTheme
from webviz_subsurface._models import InplaceVolumesModel


def selections_layout(
    uuid: str,
    volumemodel: InplaceVolumesModel,
    theme: WebvizConfigTheme,
) -> html.Div:
    """Layout for selecting intersection data"""
    selectors = "/".join(
        [x.lower() for x in ["ZONE", "REGION", "FACIES"] if x in volumemodel.selectors]
    )
    return html.Div(
        children=[
            button(uuid=uuid, title="1 plot / 1 table", page_id="1p1t"),
            button(uuid=uuid, title=f"Plots per {selectors}", page_id="per_zr"),
            button(uuid=uuid, title="Convergence plot mean/p10/p90", page_id="conv"),
            button(uuid=uuid, title="Custom plotting", page_id="custom"),
            plot_selections_layout(uuid, volumemodel),
            table_selections_layout(uuid, volumemodel),
            settings_layout(uuid, theme),
        ]
    )


def button(uuid: str, title: str, page_id: str) -> html.Button:
    return html.Button(
        title,
        className="webviz-inplace-vol-btn",
        id={"id": uuid, "button": page_id},
    )


def source_selector(uuid: str, volumemodel: InplaceVolumesModel) -> html.Div:
    return html.Div(
        style={"marginTop": "5px"},
        children=html.Label(
            children=[
                html.Span("Source", style={"font-weight": "bold"}),
                dcc.Dropdown(
                    id={"id": uuid, "element": "ensembles"},
                    options=[
                        {"label": src, "value": src} for src in volumemodel.sources
                    ],
                    value=volumemodel.sources[0],
                    clearable=False,
                    persistence=True,
                    persistence_type="session",
                ),
            ]
        ),
    )


def plot_selections_layout(uuid: str, volumemodel: InplaceVolumesModel) -> html.Details:
    return html.Details(
        className="webviz-inplace-vol-plotselect",
        style={"margin-top": "20px"},
        open=True,
        children=[
            html.Summary(
                style={"font-size": "15px", "font-weight": "bold"},
                children="PLOT CONTROLS",
            ),
            html.Div(
                style={"padding": "10px"},
                children=plot_selector_dropdowns(
                    uuid=uuid,
                    volumemodel=volumemodel,
                ),
            ),
        ],
    )


def table_selections_layout(
    uuid: str, volumemodel: InplaceVolumesModel
) -> html.Details:
    responses = volumemodel.volume_columns + volumemodel.property_columns
    return html.Details(
        className="webviz-inplace-vol-plotselect",
        open=True,
        children=[
            html.Summary(
                style={
                    "font-size": "15px",
                    "font-weight": "bold",
                },
                children="TABLE CONTROLS",
            ),
            html.Div(
                style={"padding": "10px"},
                children=[
                    table_sync_option(uuid),
                    html.Div(
                        children=[
                            html.Span("Table type", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id={"id": uuid, "selector": "Table type"},
                                options=[
                                    {"label": elm, "value": elm}
                                    for elm in ["Statistics table", "Mean table"]
                                ],
                                value="Statistics table",
                                clearable=False,
                                persistence=True,
                                persistence_type="session",
                            ),
                        ]
                    ),
                    html.Div(
                        id={
                            "id": uuid,
                            "element": "table_response_group_wrapper",
                        },
                        style={"display": "None"},
                        children=[
                            html.Span("Group by", style={"font-weight": "bold"}),
                            dcc.Dropdown(
                                id={"id": uuid, "selector": "Group by"},
                                options=[
                                    {"label": elm, "value": elm}
                                    for elm in volumemodel.selectors
                                ],
                                value=None,
                                multi=True,
                                clearable=False,
                                persistence=True,
                                persistence_type="session",
                            ),
                            html.Span("Responses", style={"font-weight": "bold"}),
                            wcc.Select(
                                id={"id": uuid, "selector": "table_responses"},
                                options=[{"label": i, "value": i} for i in responses],
                                value=responses,
                                size=min(
                                    20,
                                    len(responses),
                                ),
                                persistence=True,
                                persistence_type="session",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


def plot_selector_dropdowns(
    uuid: str, volumemodel: InplaceVolumesModel
) -> List[html.Div]:
    """Makes dropdowns for each selector"""

    dropdowns: List[html.Div] = []
    value: Optional[str] = None

    for selector in [
        "Plot type",
        "X Response",
        "Y Response",
        "Subplots",
        "Color by",
    ]:
        if selector == "Plot type":
            elements = ["histogram", "scatter", "distribution", "box"]
            value = elements[0]
        if selector == "X Response":
            elements = volumemodel.responses
            value = "STOIIP" if "STOIIP" in elements else elements[0]
        if selector == "Y Response":
            elements = volumemodel.responses
            value = None
        if selector == "Subplots":
            elements = [x for x in volumemodel.selectors if x != "REAL"]
            value = None
        if selector == "Color by":
            elements = volumemodel.selectors
            value = "ENSEMBLE"

        dropdowns.append(
            html.Div(
                html.Label(
                    children=[
                        html.Span(selector, style={"font-weight": "bold"}),
                        dcc.Dropdown(
                            id={"id": uuid, "selector": selector},
                            options=[{"label": elm, "value": elm} for elm in elements],
                            value=value,
                            clearable=selector
                            in ["Subplots", "Color by", "Y Response"],
                            disabled=selector in ["Subplots", "Y Response"],
                            persistence=True,
                            persistence_type="session",
                        ),
                    ],
                )
            )
        )
    return dropdowns


def settings_layout(uuid: str, theme: WebvizConfigTheme) -> html.Details:

    theme_colors = theme.plotly_theme.get("layout", {}).get("colorway", [])
    return html.Details(
        className="webviz-inplace-vol-plotselect",
        open=False,
        children=[
            html.Summary(
                style={"font-size": "15px", "font-weight": "bold"},
                children="⚙️ SETTINGS",
            ),
            html.Div(
                style={"padding": "10px"},
                children=[
                    remove_fluid_annotation(uuid=uuid),
                    subplot_xaxis_range(uuid=uuid),
                    histogram_options(uuid=uuid),
                    html.Span("Colors", style={"font-weight": "bold"}),
                    wcc.ColorScales(
                        id={"id": uuid, "settings": "Colorscale"},
                        colorscale=theme_colors,
                        fixSwatches=True,
                        nSwatches=12,
                    ),
                ],
            ),
        ],
    )


def subplot_xaxis_range(
    uuid: str,
) -> html.Div:
    axis_matches_layout = []
    for axis in ["X axis", "Y axis"]:
        axis_matches_layout.append(
            html.Div(
                children=dcc.Checklist(
                    id={"id": uuid, "selector": f"{axis} matches"},
                    options=[{"label": f"Equal {axis} range", "value": "Equal"}],
                    value=["Equal"],
                )
            )
        )
    return html.Div(
        children=[
            html.Span("Subplot options:", style={"font-weight": "bold"}),
            html.Div(style={"margin-bottom": "10px"}, children=axis_matches_layout),
        ]
    )


def table_sync_option(
    uuid: str,
) -> html.Div:
    return html.Div(
        style={"margin-bottom": "10px"},
        children=dcc.Checklist(
            id={"id": uuid, "selector": "sync_table"},
            options=[{"label": "Sync table with plot", "value": "Sync"}],
            value=["Sync"],
        ),
    )


def remove_fluid_annotation(
    uuid: str,
) -> html.Div:
    return html.Div(
        style={"margin-bottom": "10px"},
        children=dcc.Checklist(
            id={"id": uuid, "selector": "Fluid annotation"},
            options=[{"label": "Show fluid annotation", "value": "Show"}],
            value=["Show"],
        ),
    )


def histogram_options(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Span("Histogram options:", style={"font-weight": "bold"}),
            html.Div(
                children=[
                    dcc.RadioItems(
                        id={"id": uuid, "selector": "barmode"},
                        options=[
                            {"label": "overlay", "value": "overlay"},
                            {"label": "group", "value": "group"},
                            {"label": "stack", "value": "stack"},
                        ],
                        labelStyle={"display": "inline-flex", "margin-right": "5px"},
                        value="overlay",
                    ),
                    wcc.FlexBox(
                        children=[
                            html.Span(
                                "Bins:",
                                style={
                                    "flex": 1,
                                    "minWidth": "10px",
                                    "maxWidth": "30px",
                                },
                            ),
                            html.Div(
                                style={"flex": 2, "minWidth": "250px"},
                                children=dcc.Slider(
                                    id={"id": uuid, "selector": "hist_bins"},
                                    value=15,
                                    min=5,
                                    max=30,
                                ),
                            ),
                        ]
                    ),
                ]
            ),
        ],
    )

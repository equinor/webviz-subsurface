from dash import html
import webviz_core_components as wcc
from webviz_subsurface._models import InplaceVolumesModel


def tornado_selections_layout(
    uuid: str, volumemodel: InplaceVolumesModel, tab: str
) -> html.Div:
    """Layout for selecting tornado data"""
    return html.Div(
        children=[
            tornado_controls_layout(uuid, tab, volumemodel),
            settings_layout(uuid, tab, volumemodel),
        ]
    )


def tornado_controls_layout(
    uuid: str, tab: str, volumemodel: InplaceVolumesModel
) -> wcc.Selectors:
    mode_options = [{"label": "Custom", "value": "custom"}]
    if "BULK" in volumemodel.responses:
        mode_options.append({"label": "Bulk vs STOIIP/GIIP", "value": "locked"})
    return wcc.Selectors(
        label="TORNADO CONTROLS",
        children=[
            wcc.RadioItems(
                label="Mode:",
                id={"id": uuid, "tab": tab, "selector": "mode"},
                options=mode_options,
                value="custom",
            ),
            tornado_selection(
                position="left", uuid=uuid, tab=tab, volumemodel=volumemodel
            ),
            tornado_selection(
                position="right", uuid=uuid, tab=tab, volumemodel=volumemodel
            ),
        ],
    )


def tornado_selection(
    position: str, uuid: str, tab: str, volumemodel: InplaceVolumesModel
) -> html.Div:
    return html.Div(
        style={"margin-top": "10px"},
        children=[
            html.Label(
                children=f"Tornado ({position})",
                style={"display": "block"},
                className="webviz-underlined-label",
            ),
            wcc.Dropdown(
                id={"id": uuid, "tab": tab, "selector": f"Response {position}"},
                clearable=False,
                value=volumemodel.responses[0],
            ),
            html.Details(
                open=False,
                children=[
                    html.Summary("Sensitivity filter"),
                    wcc.Select(
                        id={
                            "id": uuid,
                            "tab": tab,
                            "selector": f"Sensitivities {position}",
                        },
                        options=[
                            {"label": i, "value": i} for i in volumemodel.sensitivities
                        ],
                        value=volumemodel.sensitivities,
                        size=min(15, len(volumemodel.sensitivities)),
                    ),
                ],
            ),
        ],
    )


def settings_layout(
    uuid: str, tab: str, volumemodel: InplaceVolumesModel
) -> wcc.Selectors:
    return wcc.Selectors(
        label="⚙️ SETTINGS",
        open_details=True,
        children=[
            wcc.Dropdown(
                label="Scale:",
                id={"id": uuid, "tab": tab, "selector": "Scale"},
                options=[
                    {"label": "Relative value (%)", "value": "Percentage"},
                    {"label": "Relative value", "value": "Absolute"},
                    {"label": "True value", "value": "True"},
                ],
                value="Percentage",
                clearable=False,
            ),
            html.Div(
                style={"margin-top": "10px"},
                children=wcc.Checklist(
                    id={"id": uuid, "tab": tab, "selector": "real_scatter"},
                    options=[{"label": "Show realization points", "value": "Show"}],
                    value=[],
                ),
            ),
            cut_by_ref(uuid, tab),
            labels_display(uuid, tab),
            wcc.Dropdown(
                label="Reference:",
                id={"id": uuid, "tab": tab, "selector": "Reference"},
                options=[
                    {"label": elm, "value": elm} for elm in volumemodel.sensitivities
                ],
                value="rms_seed"
                if "rms_seed" in volumemodel.sensitivities
                else volumemodel.sensitivities[0],
                clearable=False,
            ),
        ],
    )


def cut_by_ref(uuid: str, tab: str) -> html.Div:
    return html.Div(
        style={"margin-bottom": "10px"},
        children=wcc.Checklist(
            id={"id": uuid, "tab": tab, "selector": "Remove no impact"},
            options=[
                {"label": "Remove sensitivities with no impact", "value": "Remove"}
            ],
            value=["Remove"],
        ),
    )


def labels_display(uuid: str, tab: str) -> html.Div:
    return html.Div(
        style={"margin-bottom": "10px"},
        children=[
            wcc.RadioItems(
                label="Label options:",
                id={"id": uuid, "tab": tab, "selector": "labeloptions"},
                options=[
                    {"label": "detailed", "value": "detailed"},
                    {"label": "simple", "value": "simple"},
                    {"label": "hide", "value": "hide"},
                ],
                vertical=False,
                value="detailed",
            ),
        ],
    )

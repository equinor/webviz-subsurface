from typing import Optional, Union
import dash_html_components as html
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

    return wcc.Selectors(
        label="TORNADO CONTROLS",
        open_details=True,
        children=[
            create_dropdown(
                selector="Volume response",
                options=[x for x in ["STOIIP", "GIIP"] if x in volumemodel.responses],
                uuid=uuid,
                tab=tab,
            ),
            create_dropdown(
                selector="Scale",
                options=[
                    {"label": "Relative value (%)", "value": "Percentage"},
                    {"label": "Relative value", "value": "Absolute"},
                    {"label": "True value", "value": "True"},
                ],
                uuid=uuid,
                tab=tab,
            ),
            html.Div(
                style={"margin-top": "10px"},
                children=create_select(
                    selector="Bulk sensitivities",
                    options=volumemodel.sensitivities,
                    uuid=uuid,
                    tab=tab,
                ),
            ),
            html.Div(
                style={"margin-top": "10px"},
                children=create_select(
                    selector="Volume sensitivities",
                    options=volumemodel.sensitivities,
                    uuid=uuid,
                    tab=tab,
                ),
            ),
            html.Div(
                style={"margin-top": "10px"},
                children=wcc.Checklist(
                    id={"id": uuid, "tab": tab, "selector": "real_scatter"},
                    options=[{"label": "Show realization points", "value": "Show"}],
                    value=[],
                ),
            ),
        ],
    )


def settings_layout(
    uuid: str, tab: str, volumemodel: InplaceVolumesModel
) -> wcc.Selectors:
    return wcc.Selectors(
        label="⚙️ SETTINGS",
        open_details=False,
        children=[
            cut_by_ref(uuid, tab),
            labels_display(uuid, tab),
            create_dropdown(
                selector="Reference",
                options=volumemodel.sensitivities,
                value="rms_seed" if "rms_seed" in volumemodel.sensitivities else None,
                uuid=uuid,
                tab=tab,
            ),
        ],
    )


def create_dropdown(
    selector: str,
    options: Union[list, dict],
    uuid: str,
    tab: str,
    value: Optional[str] = None,
) -> wcc.Dropdown:
    options = (
        options
        if isinstance(options[0], dict)
        else [{"label": elm, "value": elm} for elm in options]
    )
    return wcc.Dropdown(
        label=selector,
        id={"id": uuid, "tab": tab, "selector": selector},
        options=options,
        value=value if value is not None else options[0]["value"],
        clearable=False,
    )


def create_select(
    selector: str, options: list, uuid: str, tab: str, value: Optional[list] = None
) -> html.Details:
    return html.Details(
        open=False,
        children=[
            html.Summary(
                selector,
                style={"font-weight": "bold"},
            ),
            wcc.Select(
                id={
                    "id": uuid,
                    "tab": tab,
                    "selector": selector,
                },
                options=[{"label": i, "value": i} for i in options],
                value=value if value is not None else options,
                size=min(
                    10,
                    len(options),
                ),
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

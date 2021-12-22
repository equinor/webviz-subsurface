import webviz_core_components as wcc
from dash import html

from webviz_subsurface._models import InplaceVolumesModel

from ..utils.table_and_figure_utils import create_figure_matrix


def tornado_main_layout(uuid: str) -> html.Div:
    return html.Div(
        children=[
            html.Div(id={"id": uuid, "page": "torn_multi"}, style={"display": "block"}),
            html.Div(
                id={"id": uuid, "page": "torn_bulk_inplace"}, style={"display": "none"}
            ),
        ]
    )


def tornado_plots_layout(figures: list, bottom_display: list) -> html.Div:
    matrix = create_figure_matrix(figures)
    max_height = 45 if bottom_display else 86

    return html.Div(
        children=[
            html.Div(
                children=[
                    wcc.FlexBox(
                        children=[
                            html.Div(
                                style={"flex": 1},
                                children=wcc.Graph(
                                    config={"displayModeBar": False},
                                    style={"height": f"{max_height/len(matrix)}vh"},
                                    figure=fig,
                                )
                                if fig is not None
                                else [],
                            )
                            for fig in row
                        ]
                    )
                    for row in matrix
                ],
            ),
            html.Div(
                bottom_display,
                style={
                    "height": "40vh",
                    "display": "block" if bottom_display else "none",
                    "margin-top": "20px",
                },
            ),
        ]
    )


def tornado_error_layout(message: str) -> wcc.Frame:
    return html.Div(message, style={"margin-top": "40px"})


def tornado_selections_layout(
    uuid: str, volumemodel: InplaceVolumesModel, tab: str
) -> html.Div:
    """Layout for selecting tornado data"""
    return html.Div(
        children=[
            page_buttons(uuid, volumemodel),
            wcc.Selectors(
                label="TORNADO CONTROLS",
                children=tornado_controls_layout(uuid, tab, volumemodel),
            ),
            wcc.Selectors(
                label="⚙️ SETTINGS",
                open_details=True,
                children=[
                    scale_selector(uuid, tab),
                    checkboxes_settings(uuid, tab),
                    labels_display(uuid, tab),
                    reference_selector(uuid, tab, volumemodel),
                ],
            ),
        ]
    )


def page_buttons(uuid: str, volumemodel: InplaceVolumesModel) -> html.Div:
    no_bulk = "BULK" not in volumemodel.responses
    return html.Div(
        style={"margin-bottom": "20px", "display": "none" if no_bulk else "block"},
        children=[
            button(uuid=uuid, title="Custom", page_id="torn_multi"),
            button(
                uuid=uuid,
                title="Bulk vs STOIIP/GIIP",
                page_id="torn_bulk_inplace",
            ),
        ],
    )


def button(uuid: str, title: str, page_id: str) -> html.Button:
    return html.Button(
        title,
        className="webviz-inplace-vol-btn",
        id={"id": uuid, "button": page_id},
    )


def tornado_controls_layout(
    uuid: str, tab: str, volumemodel: InplaceVolumesModel
) -> wcc.Selectors:
    sens_columns = ["REAL", "SENSNAME", "SENSCASE", "SENSTYPE", "SENSNAME_CASE"]
    return [
        wcc.Dropdown(
            label="Response",
            id={"id": uuid, "tab": tab, "selector": "Response"},
            clearable=False,
            options=[{"label": i, "value": i} for i in volumemodel.responses],
            value=volumemodel.responses[0],
        ),
        wcc.SelectWithLabel(
            label="Sensitivity filter",
            collapsible=True,
            open_details=False,
            id={"id": uuid, "tab": tab, "selector": "Sensitivities"},
            options=[{"label": i, "value": i} for i in volumemodel.sensitivities],
            value=volumemodel.sensitivities,
            size=min(15, len(volumemodel.sensitivities)),
        ),
        wcc.Dropdown(
            label="Subplots",
            id={"id": uuid, "tab": tab, "selector": "Subplots"},
            clearable=True,
            options=[
                {"label": i, "value": i}
                for i in [
                    x
                    for x in volumemodel.selectors
                    if x not in sens_columns and volumemodel.dataframe[x].nunique() > 1
                ]
            ],
        ),
        html.Div(
            style={"margin-top": "10px"},
            children=wcc.RadioItems(
                label="Visualization below tornado:",
                id={"id": uuid, "tab": tab, "selector": "bottom_viz"},
                options=[
                    {"label": "Table", "value": "table"},
                    {"label": "Realization plot", "value": "realplot"},
                    {"label": "None", "value": "none"},
                ],
                vertical=False,
                value="table",
            ),
        ),
    ]


def checkboxes_settings(uuid: str, tab: str) -> html.Div:
    return html.Div(
        style={"margin-top": "10px", "margin-bottom": "10px"},
        children=[
            wcc.Checklist(
                id={"id": uuid, "tab": tab, "selector": selector},
                options=[{"label": label, "value": "selected"}],
                value=["selected"] if selected else [],
            )
            for label, selector, selected in [
                ("Color by sensitivity", "color_by_sens", True),
                ("Shared subplot X axis", "Shared axis", False),
                ("Show realization points", "real_scatter", False),
                ("Show reference on tornado", "torn_ref", True),
                ("Remove sensitivities with no impact", "Remove no impact", True),
            ]
        ],
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
                value="simple",
            ),
        ],
    )


def reference_selector(
    uuid: str, tab: str, volumemodel: InplaceVolumesModel
) -> wcc.Dropdown:
    return wcc.Dropdown(
        label="Reference:",
        id={"id": uuid, "tab": tab, "selector": "Reference"},
        options=[{"label": elm, "value": elm} for elm in volumemodel.sensitivities],
        value="rms_seed"
        if "rms_seed" in volumemodel.sensitivities
        else volumemodel.sensitivities[0],
        clearable=False,
    )


def scale_selector(uuid: str, tab: str) -> wcc.Dropdown:
    return wcc.Dropdown(
        label="Scale:",
        id={"id": uuid, "tab": tab, "selector": "Scale"},
        options=[
            {"label": "Relative value (%)", "value": "Percentage"},
            {"label": "Relative value", "value": "Absolute"},
            {"label": "True value", "value": "True"},
        ],
        value="Percentage",
        clearable=False,
    )

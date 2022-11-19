from typing import Optional

import plotly.graph_objects as go
import webviz_core_components as wcc
from dash import dash_table, dcc, html

from webviz_subsurface._models import InplaceVolumesModel


def comparison_main_layout(uuid: str) -> html.Div:
    return [
        html.Div(
            style={"margin-bottom": "20px"},
            children=wcc.RadioItems(
                vertical=False,
                id={"id": uuid, "element": "display-option"},
                options=[
                    {
                        "label": "QC plots",
                        "value": "plots",
                    },
                    {
                        "label": "Difference table for selected response",
                        "value": "single-response table",
                    },
                    {
                        "label": "Difference table for multiple responses",
                        "value": "multi-response table",
                    },
                ],
                value="plots",
            ),
        ),
        html.Div(id={"id": uuid, "wrapper": "table"}),
    ]


def comparison_qc_plots_layout(
    fig_diff_vs_real: Optional[go.Figure],
    fig_corr: go.Figure,
    fig_diff_vs_response: go.Figure,
    barfig: go.Figure,
) -> html.Div:
    real_plot = fig_diff_vs_real is not None
    return html.Div(
        children=[
            html.Div(
                children=wcc.Graph(
                    config={"displayModeBar": False},
                    style={"height": "21vh"},
                    figure=fig_diff_vs_real,
                )
                if real_plot
                else [],
            ),
            wcc.FlexBox(
                style={"height": "31vh" if real_plot else "52vh"},
                children=[
                    wcc.FlexColumn(
                        children=wcc.Graph(
                            config={"displayModeBar": False},
                            style={"height": "30vh" if real_plot else "51vh"},
                            figure=fig_diff_vs_response,
                        )
                    ),
                    wcc.FlexColumn(
                        children=wcc.Graph(
                            config={"displayModeBar": False},
                            style={"height": "30vh" if real_plot else "51vh"},
                            figure=fig_corr,
                        )
                    ),
                ],
            ),
            wcc.Frame(
                style={"height": "29vh"},
                children=[
                    wcc.Header("Highlighted data"),
                    wcc.Graph(
                        config={"displayModeBar": False},
                        style={"height": "25vh"},
                        figure=barfig,
                    )
                    if barfig is not None
                    else html.Div("No data within highlight criteria"),
                ],
            ),
        ]
    )


def comparison_table_layout(
    table: dash_table, table_type: str, selections: dict, filter_info: str
) -> html.Div:
    if table_type == "single-response table":
        header = f"Table showing differences for {selections['Response']}"
    else:
        diff_mode = "percent" if selections["Diff mode"] == "diff (%)" else "true value"
        header = f"Table showing differences in {diff_mode} for multiple responses"

    return html.Div(
        children=[
            wcc.Header(header),
            html.Div(
                style={"margin-bottom": "30px", "font-weight": "bold"},
                children=[
                    html.Div(
                        f"From {selections['value1'].replace('|', ':  ')} "
                        f"to {selections['value2'].replace('|', ':  ')}"
                    ),
                    html.Div(
                        f"{filter_info.capitalize()} {selections['filters'][filter_info][0]}"
                    ),
                ],
            ),
            table,
        ]
    )


def comparison_options(compare_on: str, volumemodel: InplaceVolumesModel) -> list:
    if compare_on == "Ensemble" and "SENSNAME_CASE" in volumemodel.selectors:
        elements = []
        for ens in volumemodel.ensembles:
            for sens in volumemodel.ensemble_sensitivities[ens]:
                elements.append("|".join([ens, sens]))
        return [{"label": i.replace("|", ":  "), "value": i} for i in elements]

    if compare_on == "Source":
        elements = volumemodel.sources
    elif compare_on == "Ensemble":
        elements = volumemodel.ensembles
    elif compare_on == "Sensitivity":
        elements = list(volumemodel.ensemble_sensitivities.values())[0]
    return [{"label": i, "value": i} for i in elements]


def comparison_selections(
    uuid: str, volumemodel: InplaceVolumesModel, tab: str, compare_on: str
) -> html.Div:
    options = comparison_options(compare_on, volumemodel)
    return html.Div(
        children=[
            wcc.Selectors(
                label="CONTROLS",
                open_details=True,
                children=[
                    wcc.Dropdown(
                        id={"id": uuid, "tab": tab, "selector": "value1"},
                        label=f"{compare_on} A",
                        optionHeight=50,
                        options=options,
                        value=options[0]["value"],
                        clearable=False,
                    ),
                    wcc.Dropdown(
                        id={"id": uuid, "tab": tab, "selector": "value2"},
                        optionHeight=50,
                        label=f"{compare_on} B",
                        options=options,
                        value=options[-1]["value"],
                        clearable=False,
                    ),
                    dcc.Input(
                        style={"display": "none"},
                        id={"id": uuid, "tab": tab, "selector": "compare_on"},
                        value=compare_on,
                    ),
                    html.Div(
                        f"Difference = {compare_on} B - {compare_on} A",
                        style={
                            "font-size": "15px",
                            "margin-top": "5px",
                            "color": "#007079",
                        },
                    ),
                    response_selector(volumemodel, uuid, tab),
                    group_by_selector(volumemodel, uuid, tab),
                    diff_mode_selector(uuid, tab),
                    highlight_controls(uuid, tab),
                ],
            ),
            wcc.Selectors(
                label="⚙️ SETTINGS",
                open_details=False,
                children=[
                    colorby_selector(uuid, tab),
                    axis_focus_selector(uuid, tab),
                    remove_zero_responses(uuid, tab),
                    remove_non_highlighted_data(uuid, tab),
                ],
            ),
        ]
    )


def axis_focus_selector(uuid: str, tab: str) -> html.Div:
    return wcc.Checklist(
        id={"id": uuid, "tab": tab, "selector": "Axis focus"},
        options=[{"label": "Focus diff plots on highlighted", "value": "focus"}],
        value=["focus"],
    )


def remove_zero_responses(uuid: str, tab: str) -> html.Div:
    return wcc.Checklist(
        id={"id": uuid, "tab": tab, "selector": "Remove zeros"},
        options=[{"label": "Remove data with no volume", "value": "remove"}],
        value=["remove"],
    )


def remove_non_highlighted_data(uuid: str, tab: str) -> html.Div:
    return wcc.Checklist(
        id={"id": uuid, "tab": tab, "selector": "Remove non-highlighted"},
        options=[
            {"label": "Display only highlighted data in table", "value": "remove"}
        ],
        value=[],
    )


def diff_mode_selector(uuid: str, tab: str) -> html.Div:
    return html.Div(
        style={"margin-top": "10px"},
        children=wcc.RadioItems(
            label="Difference mode",
            id={"id": uuid, "tab": tab, "selector": "Diff mode"},
            options=[
                {"label": "Percent", "value": "diff (%)"},
                {"label": "True value", "value": "diff"},
            ],
            labelStyle={"display": "inline-flex", "margin-right": "5px"},
            value="diff (%)",
        ),
    )


def highlight_controls(uuid: str, tab: str) -> html.Div:
    return html.Div(
        style={"margin-top": "10px"},
        children=[
            html.Label("Data highlight criterias", className="webviz-underlined-label"),
            html.Div(
                children=[
                    wcc.Label("Absolute diff (%) above:"),
                    dcc.Input(
                        id={"id": uuid, "tab": tab, "selector": "Accept value"},
                        type="number",
                        required=True,
                        value=5,
                        persistence=True,
                        persistence_type="session",
                    ),
                ],
            ),
            html.Div(
                children=[
                    wcc.Label("Ignore response values below:"),
                    dcc.Input(
                        id={"id": uuid, "tab": tab, "selector": "Ignore <"},
                        type="number",
                        required=True,
                        value=0,
                        persistence=True,
                        persistence_type="session",
                        debounce=True,
                    ),
                ]
            ),
        ],
    )


def response_selector(
    volumemodel: InplaceVolumesModel,
    uuid: str,
    tab: str,
) -> html.Div:
    return html.Div(
        style={"margin-top": "10px"},
        children=wcc.Dropdown(
            id={
                "id": uuid,
                "tab": tab,
                "selector": "Response",
            },
            label="Response",
            options=[{"label": i, "value": i} for i in volumemodel.responses],
            value=volumemodel.volume_columns[0],
            clearable=False,
        ),
    )


def colorby_selector(
    uuid: str,
    tab: str,
) -> html.Div:
    return html.Div(
        style={"margin": "10px 0px"},
        children=wcc.RadioItems(
            label="Color plots on",
            id={"id": uuid, "tab": tab, "selector": "Color by"},
            options=[
                {"label": "Highlighted", "value": "highlighted"},
                {"label": "1st level of investigation", "value": "groups"},
            ],
            labelStyle={"display": "inline-flex", "margin-right": "5px"},
            value="highlighted",
        ),
    )


def group_by_selector(
    volumemodel: InplaceVolumesModel, uuid: str, tab: str
) -> html.Div:
    available_selectors = [
        x
        for x in volumemodel.region_selectors + ["FACIES", "REAL", "FLUID_ZONE"]
        if x in volumemodel.selectors and volumemodel.dataframe[x].nunique() > 1
    ]
    return html.Div(
        style={"margin-top": "10px"},
        children=wcc.Dropdown(
            label="Investigate differences on level",
            id={"id": uuid, "tab": tab, "selector": "Group by"},
            options=[{"label": elm, "value": elm} for elm in available_selectors],
            value=[],
            placeholder="Total",
            multi=True,
            clearable=False,
        ),
    )

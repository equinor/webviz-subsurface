from typing import Union

import dash_html_components as html
import dash_core_components as dcc
import webviz_core_components as wcc


def ensemble_selector(
    parent, tab: str, multi: bool = False, value: str = None
) -> html.Div:
    return html.Div(
        style={"width": "75%"},
        children=[
            html.H5("Ensemble"),
            dcc.Dropdown(
                id={"id": parent.uuid("ensemble-selector"), "tab": tab},
                options=[
                    {"label": ens, "value": ens} for ens in parent.pmodel.ensembles
                ],
                multi=multi,
                value=value if value is not None else parent.pmodel.ensembles[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def delta_ensemble_selector(parent, tab: str, multi: bool = False) -> html.Div:
    return html.Div(
        style={"width": "75%"},
        children=[
            html.H5("Delta Ensemble"),
            dcc.Dropdown(
                id={"id": parent.uuid("delta-ensemble-selector"), "tab": tab},
                options=[
                    {"label": ens, "value": ens} for ens in parent.pmodel.ensembles
                ],
                multi=multi,
                value=parent.pmodel.ensembles[-1],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def property_selector(
    parent, tab: str, multi: bool = False, value: str = None
) -> html.Div:
    display = "none" if len(parent.pmodel.properties) < 2 else "inline"
    return html.Div(
        style={"width": "75%", "display": display},
        children=[
            html.H5("Property"),
            dcc.Dropdown(
                id={"id": parent.uuid("property-selector"), "tab": tab},
                options=[
                    {"label": prop, "value": prop} for prop in parent.pmodel.properties
                ],
                multi=multi,
                value=value if value is not None else parent.pmodel.properties[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def source_selector(
    parent, tab: str, multi: bool = False, value: str = None
) -> html.Div:
    display = "none" if len(parent.pmodel.sources) < 2 else "inline"
    return html.Div(
        style={"width": "75%", "display": display},
        children=[
            html.H5("Source"),
            dcc.Dropdown(
                id={"id": parent.uuid("source-selector"), "tab": tab},
                options=[
                    {"label": source, "value": source}
                    for source in parent.pmodel.sources
                ],
                multi=multi,
                value=value if value is not None else parent.pmodel.sources[0],
                clearable=False,
                persistence=True,
                persistence_type="session",
            ),
        ],
    )


def make_filter(
    parent,
    tab: str,
    df_column: str,
    column_values: list,
    multi: bool = True,
    value: Union[str, float] = None,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        children=html.Details(
            open=open_details,
            children=[
                html.Summary(df_column.lower().capitalize()),
                wcc.Select(
                    id={
                        "id": parent.uuid("filter-selector"),
                        "tab": tab,
                        "selector": df_column,
                    },
                    options=[{"label": i, "value": i} for i in column_values],
                    value=[value] if value is not None else column_values,
                    multi=multi,
                    size=min(20, len(column_values)),
                    persistence=True,
                    persistence_type="session",
                ),
            ],
        ),
    )


def filter_selector(
    parent,
    tab: str,
    multi: bool = True,
    value: Union[str, float] = None,
    open_details: bool = False,
) -> html.Div:
    return html.Div(
        children=[
            html.H5("Selections"),
            html.Div(
                children=[
                    make_filter(
                        parent=parent,
                        tab=tab,
                        df_column=sel,
                        column_values=parent.pmodel.selector_values(sel),
                        multi=multi,
                        value=value,
                        open_details=open_details,
                    )
                    for sel in parent.pmodel.selectors
                ]
            ),
        ]
    )
